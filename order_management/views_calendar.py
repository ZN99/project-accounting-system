from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from .models import Project, Contractor, SubContract
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
        start_date = today.replace(day=1)
        end_date = start_date + timedelta(days=30)

        # 職人（協力業者）一覧を取得
        contractors = Contractor.objects.all().order_by('name')

        # 各職人の稼働率を計算
        contractor_data = []
        for contractor in contractors:
            # この職人が担当している案件数（期間内）
            active_projects = SubContract.objects.filter(
                contractor=contractor,
                project__work_start_date__lte=end_date,
                project__work_end_date__gte=start_date
            ).count()

            # 稼働率を簡易的に計算（より詳細な計算が必要な場合は調整）
            utilization_rate = min(active_projects * 25, 100)  # 1案件=25%として計算

            contractor_data.append({
                'id': contractor.id,
                'name': contractor.name,
                'specialty': contractor.specialty or '指定なし',
                'phone': contractor.phone or '-',
                'email': contractor.email or '-',
                'utilization': utilization_rate,
                'active_projects': active_projects
            })

        context['contractors'] = contractor_data
        context['start_date'] = start_date
        context['end_date'] = end_date

        return context


@login_required
def calendar_events_api(request):
    """カレンダーイベントをJSON形式で返す"""
    # 日付範囲を取得
    start = request.GET.get('start')
    end = request.GET.get('end')

    # 案件を取得
    projects = Project.objects.filter(
        work_start_date__isnull=False
    )

    if start:
        projects = projects.filter(work_start_date__gte=start)
    if end:
        projects = projects.filter(work_start_date__lte=end)

    # イベントデータを生成
    events = []
    for project in projects:
        event = {
            'id': project.id,
            'title': project.site_name,
            'start': project.work_start_date.isoformat() if project.work_start_date else None,
            'end': project.work_end_date.isoformat() if project.work_end_date else None,
            'url': f'/orders/{project.id}/',
            'backgroundColor': '#3788d8',
            'borderColor': '#2c6aa0'
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

    projects = Project.objects.filter(
        work_start_date__gte=start_date,
        work_start_date__lt=end_date
    )

    # 統計データを集計
    stats = {
        'total_projects': projects.count(),
        'total_amount': sum(p.total_amount or 0 for p in projects),
        'completed_projects': projects.filter(work_end_date__isnull=False).count(),
    }

    return JsonResponse(stats)


@login_required
def gantt_data_api(request):
    """ガントチャートデータをJSON形式で返す"""
    projects = Project.objects.filter(
        work_start_date__isnull=False
    ).order_by('work_start_date')

    # Ganttデータを生成
    tasks = []
    for project in projects:
        if project.work_start_date and project.work_end_date:
            task = {
                'id': f'project-{project.id}',
                'name': project.site_name,
                'start': project.work_start_date.isoformat(),
                'end': project.work_end_date.isoformat(),
                'progress': project.progress or 0,
                'dependencies': ''
            }
            tasks.append(task)

    return JsonResponse({'tasks': tasks})


@login_required
def worker_resource_data_api(request):
    """職人のスケジュールデータをJSON形式で返す"""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': '開始日と終了日が必要です'}, status=400)

    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    # 職人と案件のマッピングを取得
    subcontracts = SubContract.objects.filter(
        project__work_start_date__lte=end,
        project__work_end_date__gte=start
    ).select_related('contractor', 'project')

    # データ構造を構築
    worker_schedules = {}
    for sc in subcontracts:
        contractor_id = sc.contractor.id
        if contractor_id not in worker_schedules:
            worker_schedules[contractor_id] = {
                'worker_id': contractor_id,
                'worker_name': sc.contractor.name,
                'projects': []
            }

        worker_schedules[contractor_id]['projects'].append({
            'project_id': sc.project.id,
            'project_name': sc.project.site_name,
            'start_date': sc.project.work_start_date.isoformat() if sc.project.work_start_date else None,
            'end_date': sc.project.work_end_date.isoformat() if sc.project.work_end_date else None,
            'type': sc.project.contract_type or 'other'
        })

    return JsonResponse(list(worker_schedules.values()), safe=False)
