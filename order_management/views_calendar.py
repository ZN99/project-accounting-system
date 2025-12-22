from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from .models import Project
from subcontract_management.models import Contractor, Subcontract, InternalWorker
from django.db.models import Q, Count


class ConstructionCalendarView(LoginRequiredMixin, TemplateView):
    """建設カレンダー - FullCalendar使用"""
    template_name = 'order_management/construction_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PerformanceMonthlyView(LoginRequiredMixin, TemplateView):
    """月別業績表示"""
    template_name = 'order_management/performance_monthly.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class GanttChartView(LoginRequiredMixin, TemplateView):
    """ガントチャート表示"""
    template_name = 'order_management/gantt_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class WorkerResourceCalendarView(LoginRequiredMixin, TemplateView):
    """職人リソース管理カレンダー"""
    template_name = 'order_management/worker_resource_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 開始日と終了日（デフォルトは今月の1日から30日後まで）
        today = datetime.now()
        start_date = today.replace(day=1).date()  # date型に変換
        end_date = (today.replace(day=1) + timedelta(days=30)).date()  # date型に変換

        # 全職人データを統合（社内職人・個人職人・協力会社）
        all_workers = []

        # 1. 社内職人を取得
        internal_workers = InternalWorker.objects.all().order_by('name')

        for worker in internal_workers:
            # この職人が担当している案件数（期間内）
            # アクティブな案件に関連する下請けを取得
            subcontracts = Subcontract.objects.filter(
                worker_type='internal',
                internal_worker=worker,
                project__project_status='受注確定'
            ).select_related('project')

            # 期間内の案件をPythonでフィルタ
            active_projects = 0
            for sc in subcontracts:
                period = sc.project.get_construction_period()
                if period.get('start_date') and period.get('end_date'):
                    if period['start_date'] <= end_date and period['end_date'] >= start_date:
                        active_projects += 1

            # 稼働率を簡易的に計算（より詳細な計算が必要な場合は調整）
            utilization_rate = min(active_projects * 25, 100)  # 1案件=25%として計算

            all_workers.append({
                'id': f'internal-{worker.id}',
                'name': f"{worker.name}（社内）",
                'specialty': worker.get_department_display(),
                'phone': worker.phone or '-',
                'email': worker.email or '-',
                'utilization': utilization_rate,
                'active_projects': active_projects,
                'worker_type': 'internal'  # フィルター用
            })

        # 2. 個人職人を取得
        individual_contractors = Contractor.objects.filter(
            contractor_type='individual'
        ).order_by('name')

        for contractor in individual_contractors:
            # この職人が担当している案件数（期間内）
            subcontracts = Subcontract.objects.filter(
                worker_type='external',
                contractor=contractor,
                project__project_status='受注確定'
            ).select_related('project')

            active_projects = 0
            for sc in subcontracts:
                period = sc.project.get_construction_period()
                if period.get('start_date') and period.get('end_date'):
                    if period['start_date'] <= end_date and period['end_date'] >= start_date:
                        active_projects += 1

            # 稼働率を簡易的に計算
            utilization_rate = min(active_projects * 25, 100)

            all_workers.append({
                'id': f'individual-{contractor.id}',
                'name': f"{contractor.name}（個人職人）",
                'specialty': contractor.specialties or '指定なし',
                'phone': contractor.phone or '-',
                'email': contractor.email or '-',
                'utilization': utilization_rate,
                'active_projects': active_projects,
                'worker_type': 'individual'  # フィルター用
            })

        # 3. 協力会社を取得
        company_contractors = Contractor.objects.filter(
            contractor_type='company'
        ).order_by('name')

        for contractor in company_contractors:
            # この職人が担当している案件数（期間内）
            subcontracts = Subcontract.objects.filter(
                worker_type='external',
                contractor=contractor,
                project__project_status='受注確定'
            ).select_related('project')

            active_projects = 0
            for sc in subcontracts:
                period = sc.project.get_construction_period()
                if period.get('start_date') and period.get('end_date'):
                    if period['start_date'] <= end_date and period['end_date'] >= start_date:
                        active_projects += 1

            # 稼働率を簡易的に計算
            utilization_rate = min(active_projects * 25, 100)

            all_workers.append({
                'id': f'company-{contractor.id}',
                'name': f"{contractor.name}（協力会社）",
                'specialty': contractor.specialties or '指定なし',
                'phone': contractor.phone or '-',
                'email': contractor.email or '-',
                'utilization': utilization_rate,
                'active_projects': active_projects,
                'worker_type': 'company'  # フィルター用
            })

        context['contractors'] = all_workers
        context['start_date'] = start_date
        context['end_date'] = end_date

        # カレンダーの日数リストを生成（1から31まで）
        context['calendar_days'] = list(range(1, 32))

        return context


@login_required
def calendar_events_api(request):
    """カレンダーイベントをJSON形式で返す - 主要マイルストーン対応"""
    from datetime import timedelta

    # 日付範囲を取得
    start = request.GET.get('start')
    end = request.GET.get('end')

    # 全案件を取得（Subcontractも一緒に取得）
    projects = Project.objects.prefetch_related('subcontract_set__contractor', 'subcontract_set__internal_worker').all()

    # イベントデータを生成
    events = []

    # マイルストーンの定義（表示名、フィールド名、色）- 各マイルストーンに固有の色を割り当て
    milestone_types = {
        'estimate': {'label': '見積発行', 'field': 'estimate_issued_date', 'color': '#17a2b8', 'icon': '📄'},  # teal
        'contract': {'label': '契約', 'field': 'contract_date', 'color': '#ffc107', 'icon': '📝'},  # yellow
        'work_start': {'label': '着工', 'field': 'work_start_date', 'color': '#007bff', 'icon': '🚧'},  # blue
        'work_end': {'label': '完工', 'field': 'work_end_date', 'color': '#28a745', 'icon': '✓'},  # green
    }

    # 動的ステップ用の色定義
    dynamic_step_colors = {
        'survey': '#6f42c1',  # purple - 現調
        'attendance': '#fd7e14',  # orange - 立ち会い
        'inspection': '#e83e8c',  # pink - 検査
        'site_survey': '#6f42c1',  # purple - 現場調査
    }

    for project in projects:
        # NGステータスの案件はスキップ
        if project.project_status == 'NG':
            continue

        # 下請業者情報を取得
        subcontractors = []
        for sc in project.subcontract_set.all():
            if sc.worker_type == 'external' and sc.contractor:
                subcontractors.append(sc.contractor.name)
            elif sc.worker_type == 'internal' and sc.internal_worker:
                subcontractors.append(f"{sc.internal_worker.name}(社内)")
            elif sc.worker_type == 'internal' and sc.internal_worker_name:
                subcontractors.append(f"{sc.internal_worker_name}(社内)")

        subcontractor_text = ', '.join(subcontractors) if subcontractors else '未割当'

        # 元請情報を取得（client_companyを優先、なければclient_name）
        client_display = '-'
        if project.client_company:
            client_display = project.client_company.company_name
        elif project.client_name:
            client_display = project.client_name

        # 見積と契約のマイルストーンを追加（単日イベント）
        for milestone_key in ['estimate', 'contract']:
            milestone_info = milestone_types[milestone_key]
            date_value = getattr(project, milestone_info['field'], None)
            if date_value:
                event = {
                    'id': f'{project.id}-{milestone_key}',
                    'project_id': project.id,
                    'title': f"{milestone_info['icon']} {project.site_name}",
                    'start': date_value.isoformat(),
                    'allDay': True,
                    'url': f'/orders/{project.id}/',
                    'backgroundColor': milestone_info['color'],
                    'borderColor': milestone_info['color'],
                    'classNames': ['milestone-event'],  # リスト表示で非表示にするためのクラス
                    'extendedProps': {
                        'milestone_type': milestone_key,
                        'milestone_label': milestone_info['label'],
                        'project_name': project.site_name,
                        'status': project.get_project_status_display(),
                        'client': client_display,
                        'manager': project.project_manager or '-',
                        'amount': float(project.order_amount or 0),
                        'subcontractors': subcontractor_text
                    }
                }
                events.append(event)

        # 工期（着工〜完工）を期間イベントとして追加
        # 案件詳細ページと同じwork_start_date/work_end_dateを使用
        if project.work_start_date and project.work_end_date:
            # 完工済みかどうかで色を変更（完工チェックボックスのみで判定）
            is_completed = project.work_end_completed
            work_period_color = '#28a745' if is_completed else '#007bff'  # 完工済み=緑、進行中=青
            work_period_icon = '✓' if is_completed else '🚧'

            # 完工チェックで表示を変更
            period_label = '工期（完工）' if is_completed else '工期（予定・進行中）'

            # 両方ある場合は期間イベント
            event = {
                'id': f'{project.id}-work_period',
                'project_id': project.id,
                'title': f"{work_period_icon} {project.site_name}",
                'start': project.work_start_date.isoformat(),
                'end': (project.work_end_date + timedelta(days=1)).isoformat(),  # FullCalendarは終了日を含まないので+1
                'allDay': True,
                'url': f'/orders/{project.id}/',
                'backgroundColor': work_period_color,
                'borderColor': work_period_color,
                'classNames': ['work-period-event'],  # 工期イベント（リスト表示で表示）
                'extendedProps': {
                    'milestone_type': 'work_period',
                    'milestone_label': period_label,
                    'project_name': project.site_name,
                    'status': project.get_project_status_display(),
                    'client': client_display,
                    'manager': project.project_manager or '-',
                    'amount': float(project.order_amount or 0),
                    'work_start': project.work_start_date.isoformat(),
                    'work_end': project.work_end_date.isoformat(),
                    'is_completed': is_completed,
                    'subcontractors': subcontractor_text
                }
            }
            events.append(event)
        else:
            # 着工日のみまたは完工日のみの場合は単日イベント
            for milestone_key in ['work_start', 'work_end']:
                milestone_info = milestone_types[milestone_key]
                date_value = getattr(project, milestone_info['field'], None)
                if date_value:
                    event = {
                        'id': f'{project.id}-{milestone_key}',
                        'project_id': project.id,
                        'title': f"{milestone_info['icon']} {project.site_name}",
                        'start': date_value.isoformat(),
                        'allDay': True,
                        'url': f'/orders/{project.id}/',
                        'backgroundColor': milestone_info['color'],
                        'borderColor': milestone_info['color'],
                        'classNames': ['work-period-event'],  # 工期がない場合の着工/完工もリスト表示
                        'extendedProps': {
                            'milestone_type': milestone_key,
                            'milestone_label': milestone_info['label'],
                            'project_name': project.site_name,
                            'status': project.get_project_status_display(),
                            'client': client_display,
                            'manager': project.project_manager or '-',
                            'amount': float(project.order_amount or 0),
                            'subcontractors': subcontractor_text
                        }
                    }
                    events.append(event)

        # ProjectProgressStepからマイルストーンを追加
        from order_management.models import ProjectProgressStep
        from order_management.services.progress_step_service import STEP_TEMPLATES

        # ステップテンプレートのマッピング（テンプレート名 -> キー）
        template_to_key = {}
        for key, config in STEP_TEMPLATES.items():
            template_to_key[config['name']] = key

        # 主要ステップの名前マッピング
        step_names = {
            'survey': '現調',
            'attendance': '立ち会い',
            'inspection': '検査',
            'estimate': '見積書発行',
            'construction_start': '着工',
            'completion': '完工',
        }

        # 動的ステップのアイコン定義
        step_icons = {
            'survey': '📅',
            'attendance': '👥',
            'inspection': '🔍',
            'estimate': '📋',
            'construction_start': '🏗️',
            'completion': '✅',
        }

        # ProjectProgressStepから読み込み
        progress_steps = ProjectProgressStep.objects.filter(
            project=project,
            is_active=True
        ).select_related('template')

        for progress_step in progress_steps:
            # テンプレート名からキーを取得
            step_key = template_to_key.get(progress_step.template.name)
            if not step_key or step_key not in step_names:
                continue

            # 基本フィールドと重複するステップをスキップ
            # estimate: estimate_issued_date がある場合はスキップ
            # construction_start: work_start_date がある場合はスキップ
            # completion: work_end_date がある場合はスキップ
            if step_key == 'estimate' and project.estimate_issued_date:
                continue
            if step_key == 'construction_start' and project.work_start_date:
                continue
            if step_key == 'completion' and project.work_end_date:
                continue

            # scheduled_dateを取得
            scheduled_date = ''
            if progress_step.value and isinstance(progress_step.value, dict):
                scheduled_date = progress_step.value.get('scheduled_date', '')

            if scheduled_date:
                # ステップに応じた色を取得（デフォルトは青）
                step_color = dynamic_step_colors.get(step_key, '#007bff')
                step_icon = step_icons.get(step_key, '📅')

                event = {
                    'id': f'{project.id}-{step_key}',
                    'project_id': project.id,
                    'title': f"{step_icon} {project.site_name}",
                    'start': scheduled_date,
                    'allDay': True,
                    'url': f'/orders/{project.id}/',
                    'backgroundColor': step_color,
                    'borderColor': step_color,
                    'classNames': ['milestone-event'],  # リスト表示で非表示
                    'extendedProps': {
                        'milestone_type': step_key,
                        'milestone_label': step_names[step_key],
                        'project_name': project.site_name,
                        'status': project.get_project_status_display(),
                        'client': client_display,
                        'manager': project.project_manager or '-',
                        'amount': float(project.order_amount or 0),
                        'is_actual': False,
                        'subcontractors': subcontractor_text
                    }
                }
                events.append(event)

    return JsonResponse(events, safe=False)


@login_required
def performance_monthly_api(request):
    """月別業績データをJSON形式で返す"""
    year = request.GET.get('year', datetime.now().year)
    month = request.GET.get('month', datetime.now().month)

    # 指定月の案件を取得
    start_date = datetime(int(year), int(month), 1)
    if int(month) == 12:
        end_date = datetime(int(year) + 1, 1, 1)
    else:
        end_date = datetime(int(year), int(month) + 1, 1)

    # アクティブな案件を取得
    projects = Project.objects.filter(
        project_status='受注確定',
        created_at__gte=start_date,
        created_at__lt=end_date
    )

    # 統計データを集計
    stats = {
        'total_projects': projects.count(),
        'total_amount': sum(p.order_amount or 0 for p in projects),
        'completed_projects': projects.filter(current_stage='完工').count(),
    }

    return JsonResponse(stats)


@login_required
def gantt_data_api(request):
    """ガントチャートデータをJSON形式で返す"""
    projects = Project.objects.prefetch_related('subcontract_set__contractor', 'subcontract_set__internal_worker').all().order_by('id')

    # Ganttデータを生成
    tasks = []
    for project in projects:
        # NGステータスの案件はスキップ
        if project.project_status == 'NG':
            continue

        # 案件詳細ページと同じwork_start_date/work_end_dateを使用
        if project.work_start_date and project.work_end_date:
            # 下請業者情報を取得
            subcontractors = []
            for sc in project.subcontract_set.all():
                if sc.worker_type == 'external' and sc.contractor:
                    subcontractors.append(sc.contractor.name)
                elif sc.worker_type == 'internal' and sc.internal_worker:
                    subcontractors.append(f"{sc.internal_worker.name}(社内)")
                elif sc.worker_type == 'internal' and sc.internal_worker_name:
                    subcontractors.append(f"{sc.internal_worker_name}(社内)")

            subcontractor_text = ', '.join(subcontractors) if subcontractors else '未割当'

            # 元請情報を取得（client_companyを優先、なければclient_name）
            client_display = '-'
            if project.client_company:
                client_display = project.client_company.company_name
            elif project.client_name:
                client_display = project.client_name

            # 進捗率を取得
            progress_details = project.get_progress_details()
            progress_percentage = 0
            if progress_details['total_steps'] > 0:
                progress_percentage = int((progress_details['completed_steps'] / progress_details['total_steps']) * 100)

            # 工期の日数を計算
            construction_days = (project.work_end_date - project.work_start_date).days

            # 完工済みかどうか
            period_type = 'actual' if project.work_end_completed else 'planned'

            task = {
                'id': f'project-{project.id}',
                'name': project.site_name,
                'start': project.work_start_date.isoformat(),
                'end': project.work_end_date.isoformat(),
                'progress': progress_percentage,
                'dependencies': '',
                'construction_period_type': period_type,
                'construction_period_days': construction_days,
                'project_id': project.id,
                'status': project.get_project_status_display(),
                'client': client_display,
                'manager': project.project_manager or '-',
                'amount': float(project.order_amount or 0),
                'subcontractors': subcontractor_text,
                'is_completed': project.work_end_completed
            }
            tasks.append(task)

    return JsonResponse({'tasks': tasks})


@login_required
def worker_resource_data_api(request):
    """職人のスケジュールデータをJSON形式で返す（社内職人・個人職人・協力会社別）"""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': '開始日と終了日が必要です'}, status=400)

    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    # 職人と案件のマッピングを取得
    # アクティブな案件に関連する下請けを取得し、後でPythonで期間フィルタ
    subcontracts = Subcontract.objects.filter(
        project__project_status='受注確定'
    ).select_related('contractor', 'internal_worker', 'project')

    # 期間内の下請けのみをフィルタ
    filtered_subcontracts = []
    for sc in subcontracts:
        period = sc.project.get_construction_period()
        if period.get('start_date') and period.get('end_date'):
            if period['start_date'] <= end.date() and period['end_date'] >= start.date():
                filtered_subcontracts.append(sc)

    subcontracts = filtered_subcontracts

    # データ構造を構築（社内職人・個人職人・協力会社別）
    worker_schedules = {
        'internal': {},  # 社内職人
        'individual': {},  # 個人職人
        'company': {}  # 協力会社
    }

    for sc in subcontracts:
        # 社内職人の場合
        if sc.worker_type == 'internal' and sc.internal_worker:
            worker_id = f'internal-{sc.internal_worker.id}'
            if worker_id not in worker_schedules['internal']:
                worker_schedules['internal'][worker_id] = {
                    'worker_id': worker_id,
                    'worker_name': f"{sc.internal_worker.name}（社内）",
                    'worker_type': 'internal',
                    'department': sc.internal_worker.get_department_display(),
                    'projects': []
                }

            worker_schedules['internal'][worker_id]['projects'].append({
                'project_id': sc.project.id,
                'project_name': sc.project.site_name,
                'start_date': sc.project.work_start_date.isoformat() if sc.project.work_start_date else None,
                'end_date': sc.project.work_end_date.isoformat() if sc.project.work_end_date else None,
                'type': sc.project.contract_type or 'other'
            })

        # 外部業者の場合
        elif sc.worker_type == 'external' and sc.contractor:
            contractor_type = sc.contractor.contractor_type

            # 個人職人または協力会社
            if contractor_type in ['individual', 'company']:
                category = contractor_type
                worker_id = f'{contractor_type}-{sc.contractor.id}'

                if worker_id not in worker_schedules[category]:
                    type_label = '個人職人' if contractor_type == 'individual' else '協力会社'
                    worker_schedules[category][worker_id] = {
                        'worker_id': worker_id,
                        'worker_name': f"{sc.contractor.name}（{type_label}）",
                        'worker_type': contractor_type,
                        'specialties': sc.contractor.specialties,
                        'projects': []
                    }

                worker_schedules[category][worker_id]['projects'].append({
                    'project_id': sc.project.id,
                    'project_name': sc.project.site_name,
                    'start_date': sc.project.work_start_date.isoformat() if sc.project.work_start_date else None,
                    'end_date': sc.project.work_end_date.isoformat() if sc.project.work_end_date else None,
                    'type': sc.project.contract_type or 'other'
                })

    # 3つのカテゴリーを統合してレスポンスを作成
    result = {
        'internal_workers': list(worker_schedules['internal'].values()),
        'individual_workers': list(worker_schedules['individual'].values()),
        'company_workers': list(worker_schedules['company'].values())
    }

    return JsonResponse(result, safe=False)
