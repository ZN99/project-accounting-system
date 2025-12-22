from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, Avg, Prefetch, OuterRef, Exists, Subquery, Max
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
import json
from decimal import Decimal
from .models import Project, Invoice, InvoiceItem, ClientCompany, WorkType, Comment, CommentReadStatus
from subcontract_management.models import Contractor

try:
    from subcontract_management.models import InternalWorker
except ImportError:
    InternalWorker = None
from .forms import ProjectForm


@login_required
def dashboard(request):
    """ダッシュボード - 進捗状況の可視化"""
    today = timezone.now().date()

    # 基本統計（下書きを除外）
    total_projects = Project.objects.filter(is_draft=False).count()

    # 受注ヨミ別統計（下書きを除外）
    status_stats = Project.objects.filter(is_draft=False).values('project_status').annotate(
        count=Count('id'),
        total_amount=Sum('order_amount')
    ).order_by('project_status')

    # 月別推移データ
    monthly_stats = []
    for i in range(6):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        month_projects = Project.objects.filter(
            is_draft=False,
            created_at__date__range=[month_start, month_end]
        )

        monthly_stats.append({
            'month': month_start.strftime('%Y-%m'),
            'total': month_projects.count(),
            'received': month_projects.filter(project_status='完工').count(),
            'pending': month_projects.filter(project_status='ネタ').count(),
            'amount': month_projects.aggregate(Sum('order_amount'))['order_amount__sum'] or 0
        })

    monthly_stats.reverse()

    # 進行中案件（工事中・下書きを除外）
    # NOTE: work_start_date/work_end_date は @property のため、QuerySetフィルタでは使用できない
    # 代わりに、プロジェクトステータスでフィルタする
    ongoing_projects = Project.objects.filter(
        is_draft=False,
        project_status='受注確定'
    ).order_by('-created_at')[:10]  # 最新10件

    # 近日開始予定（下書きを除外）
    # NOTE: work_start_date は @property のため、QuerySetフィルタでは使用できない
    # 代わりに、受注確定の案件を表示
    upcoming_projects = Project.objects.filter(
        is_draft=False,
        project_status='受注確定'
    ).order_by('-created_at')[:10]  # 最新10件

    # 売上統計（下書きを除外）
    revenue_stats = {
        'total_estimate': Project.objects.filter(is_draft=False).aggregate(Sum('order_amount'))['order_amount__sum'] or 0,
        'total_billing': Project.objects.filter(is_draft=False).aggregate(Sum('billing_amount'))['billing_amount__sum'] or 0,
        'received_amount': Project.objects.filter(is_draft=False, project_status='完工').aggregate(Sum('billing_amount'))['billing_amount__sum'] or 0,
        'pending_amount': Project.objects.filter(is_draft=False, project_status='ネタ').aggregate(Sum('order_amount'))['order_amount__sum'] or 0,
    }

    # 今月の実績（下書きを除外）
    this_month_start = today.replace(day=1)
    this_month_projects = Project.objects.filter(is_draft=False, created_at__date__gte=this_month_start)

    context = {
        'total_projects': total_projects,
        'status_stats': status_stats,
        'monthly_stats': monthly_stats,
        'ongoing_projects': ongoing_projects[:5],  # 上位5件
        'upcoming_projects': upcoming_projects[:5],  # 上位5件
        'revenue_stats': revenue_stats,
        'this_month_projects': this_month_projects.count(),
        'this_month_received': this_month_projects.filter(project_status='完工').count(),
    }

    return render(request, 'order_management/dashboard.html', context)


@login_required
def project_list(request):
    """案件一覧表示"""
    # パフォーマンス最適化：関連データを事前取得
    # 下書きを除外

    # コメント情報の取得用サブクエリ
    latest_comment_subquery = Comment.objects.filter(
        project=OuterRef('pk')
    ).order_by('-created_at')

    # 既読状態の取得
    read_status_subquery = CommentReadStatus.objects.filter(
        project=OuterRef('pk'),
        user=request.user
    )

    projects = Project.objects.filter(is_draft=False).select_related().prefetch_related(
        'progress_steps',
        'progress_steps__template',
        Prefetch(
            'comments',
            queryset=Comment.objects.select_related('author').order_by('-created_at')[:1],
            to_attr='latest_comment_list'
        )
    ).annotate(
        comment_count=Count('comments'),
        last_read_at=Subquery(read_status_subquery.values('last_read_at')[:1]),
        latest_comment_date=Subquery(latest_comment_subquery.values('created_at')[:1])
    )

    # フィルタリング
    # 受注ヨミフィルター（営業見込み）
    order_forecast = request.GET.get('order_forecast')
    if order_forecast:
        projects = projects.filter(project_status=order_forecast)

    work_type = request.GET.get('work_type')
    if work_type:
        projects = projects.filter(work_type__icontains=work_type)

    project_manager = request.GET.get('project_manager')
    if project_manager:
        projects = projects.filter(project_manager__icontains=project_manager)

    # Phase 11: 詳細スケジュールステータスフィルター
    # Note: These are @property fields and cannot be filtered at database level
    # Filtering is done after queryset evaluation if needed
    witness_status = request.GET.get('witness_status')
    survey_status = request.GET.get('survey_status')
    estimate_status = request.GET.get('estimate_status')
    construction_status = request.GET.get('construction_status')

    # 担当者名フィルター（JSONField検索）
    assignee_name = request.GET.get('assignee_name')
    if assignee_name:
        # Only filter by construction_assignees which exists in the model
        projects = projects.filter(
            Q(construction_assignees__icontains=assignee_name)
        )

    # 検索 - 管理Noと現場名を別々にフィルタ
    management_no_query = request.GET.get('management_no')
    if management_no_query:
        projects = projects.filter(management_no__icontains=management_no_query)

    site_name_query = request.GET.get('site_name')
    if site_name_query:
        projects = projects.filter(
            Q(site_name__icontains=site_name_query) |
            Q(client_name__icontains=site_name_query)
        )

    # 工期フィルタ (work_start_date と work_end_date)
    # NOTE: work_start_date と work_end_date は @property のため、QuerySetフィルタでは使用できない
    # これらは ProjectProgressStep から計算される値であり、データベースフィールドではない
    # 必要であれば、ProjectProgressStep を直接フィルタする必要がある
    work_period_from = request.GET.get('work_period_from')
    work_period_to = request.GET.get('work_period_to')
    # FIXME: 以下のフィルタは FieldError を引き起こすため、コメントアウト
    # if work_period_from:
    #     projects = projects.filter(work_start_date__gte=work_period_from)
    # if work_period_to:
    #     projects = projects.filter(work_end_date__lte=work_period_to)

    # 利益フィルタ (profit_min/max) - 後でPython側でフィルタリング
    profit_min = request.GET.get('profit_min')
    profit_max = request.GET.get('profit_max')
    # Note: profit_amountはDBフィールドではなく計算値のため、
    # ページネーション後にPython側でフィルタリングを行います

    # ページネーション件数を事前に取得（stage_filterの有無に関わらず使用）
    per_page = int(request.GET.get('per_page', 50))
    # 有効な値のみ許可
    if per_page not in [25, 50, 100, 200]:
        per_page = 50

    # プロジェクトステータス（自動計算）フィルター
    stage_filter = request.GET.get('stage_filter')
    if stage_filter:
        # クエリセットを評価してリストに変換
        projects_list = list(projects)
        # 各プロジェクトのステージを計算してフィルタリング
        projects_list = [p for p in projects_list if p.get_current_project_stage()['stage'] == stage_filter]

        # 利益フィルタ（Python側でフィルタリング）
        if profit_min:
            profit_min_decimal = Decimal(str(profit_min))
            projects_list = [p for p in projects_list if p.get_revenue_breakdown().get('gross_profit', 0) >= profit_min_decimal]
        if profit_max:
            profit_max_decimal = Decimal(str(profit_max))
            projects_list = [p for p in projects_list if p.get_revenue_breakdown().get('gross_profit', 0) <= profit_max_decimal]

        # リストをページネーション可能な形式に変換
        from django.core.paginator import Paginator as ListPaginator
        total_count = len(projects_list)
        # 受注済み: 受注確定の案件のみ（A/Bはまだ受注が決まっていない）
        received_count = sum(1 for p in projects_list if p.project_status == '受注確定')
        # 進行中: 受注確定したが、まだ完工していない案件
        in_progress_count = sum(1 for p in projects_list if p.project_status == '受注確定' and p.get_current_project_stage()['stage'] != '完工')
        # 完了済み: 動的ステップシステムで「完工」段階の案件
        completed_count = sum(1 for p in projects_list if p.get_current_project_stage()['stage'] == '完工')

        paginator = ListPaginator(projects_list, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    else:
        # 利益フィルタがある場合はPython側でフィルタリングが必要
        if profit_min or profit_max:
            # クエリセットを評価してリストに変換
            projects_list = list(projects)

            # 利益フィルタ（Python側でフィルタリング）
            if profit_min:
                profit_min_decimal = Decimal(str(profit_min))
                projects_list = [p for p in projects_list if p.get_revenue_breakdown().get('gross_profit', 0) >= profit_min_decimal]
            if profit_max:
                profit_max_decimal = Decimal(str(profit_max))
                projects_list = [p for p in projects_list if p.get_revenue_breakdown().get('gross_profit', 0) <= profit_max_decimal]

            # 統計情報を計算
            total_count = len(projects_list)
            received_count = sum(1 for p in projects_list if p.project_status == '受注確定')
            in_progress_count = sum(1 for p in projects_list if p.project_status == '受注確定' and p.get_current_project_stage()['stage'] != '完工')
            completed_count = sum(1 for p in projects_list if p.get_current_project_stage()['stage'] == '完工')

            # リストをページネーション
            from django.core.paginator import Paginator as ListPaginator
            paginator = ListPaginator(projects_list, per_page)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            # 統計情報を計算（フィルター適用後の全体から）
            total_count = projects.count()
            # 受注済み: 受注確定の案件のみ（A/Bはまだ受注が決まっていない）
            received_count = projects.filter(project_status='受注確定').count()
            # 進行中・完了済みはget_current_project_stage()を使用するため全件評価が必要
            projects_list = list(projects)
            # 進行中: 受注確定したが、まだ完工していない案件
            in_progress_count = sum(1 for p in projects_list if p.project_status == '受注確定' and p.get_current_project_stage()['stage'] != '完工')
            completed_count = sum(1 for p in projects_list if p.get_current_project_stage()['stage'] == '完工')

            # QuerySetに順序を追加（ページネーション警告対策）
            projects = projects.order_by('-created_at')

            # ページネーション（per_pageは既に上で設定済み）
            paginator = Paginator(projects, per_page)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

    # プロジェクトステージの選択肢（自動計算）
    stage_choices = [
        '未開始',
        '立ち会い待ち',
        '立ち会い済み',
        '現調待ち',
        '現調済み',
        '見積もり審査中',
        '着工日待ち',
        '工事中',
        '完工',
    ]

    # Phase 11: スケジュールステータス選択肢をコンテキストに追加
    witness_status_choices = [
        ('waiting', '立ち会い待ち'),
        ('in_progress', '立ち会い中'),
        ('completed', '完了'),
    ]

    survey_status_choices = [
        ('not_required', '不要'),
        ('not_scheduled', '未予約'),
        ('scheduled', '予約済み'),
        ('completed', '完了'),
    ]

    estimate_status_choices = [
        ('not_issued', '未発行'),
        ('issued', '見積もり書発行'),
        ('under_review', '見積もり審査中'),
        ('approved', '承認'),
    ]

    construction_status_choices = [
        ('waiting', '着工日待ち'),
        ('in_progress', '工事中'),
        ('completed', '完工'),
    ]

    # デバッグ：page_objの内容を確認
    print(f"🔍 DEBUG: page_obj type: {type(page_obj)}")
    print(f"🔍 DEBUG: page_obj.object_list type: {type(page_obj.object_list)}")
    print(f"🔍 DEBUG: page_obj has {len(page_obj.object_list)} items")
    if len(page_obj.object_list) > 0:
        print(f"🔍 DEBUG: First 3 projects: {[p.management_no for p in list(page_obj.object_list)[:3]]}")
    else:
        print(f"⚠️  DEBUG: page_obj.object_list is EMPTY!")

    context = {
        'page_obj': page_obj,
        'projects': page_obj,
        # 新：プロジェクトステータス（自動計算）
        'stage_choices': stage_choices,
        'stage_filter': stage_filter,
        # 旧：受注ヨミ（営業見込み）
        'order_forecast_choices': Project.PROJECT_STATUS_CHOICES,
        'order_forecast': order_forecast,
        'work_type': work_type,
        'project_manager': project_manager,
        # 検索フィルタ（分離）
        'management_no': management_no_query,
        'site_name': site_name_query,
        # 工期フィルタ
        'work_period_from': work_period_from,
        'work_period_to': work_period_to,
        # 利益フィルタ
        'profit_min': profit_min,
        'profit_max': profit_max,
        'total_count': total_count,
        'received_count': received_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        # Phase 11: スケジュールフィルター関連
        'witness_status': witness_status,
        'witness_status_choices': witness_status_choices,
        'survey_status': survey_status,
        'survey_status_choices': survey_status_choices,
        'estimate_status': estimate_status,
        'estimate_status_choices': estimate_status_choices,
        'construction_status': construction_status,
        'construction_status_choices': construction_status_choices,
        'assignee_name': assignee_name,
        'per_page': per_page,  # ページネーション件数
    }

    return render(request, 'order_management/project_list.html', context)


@login_required
def project_draft_list(request):
    """下書き一覧表示"""
    # 下書きプロジェクトのみ取得
    drafts = Project.objects.filter(is_draft=True).order_by('-updated_at')

    # 検索フィルター
    search_query = request.GET.get('search')
    if search_query:
        drafts = drafts.filter(
            Q(management_no__icontains=search_query) |
            Q(site_name__icontains=search_query) |
            Q(client_name__icontains=search_query)
        )

    context = {
        'drafts': drafts,
        'search_query': search_query,
    }

    return render(request, 'order_management/project_draft_list.html', context)


@login_required
def project_draft_delete(request, pk):
    """下書きプロジェクトを削除"""
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '無効なリクエストです'}, status=400)

    try:
        project = Project.objects.get(pk=pk)

        # 下書きでないプロジェクトは削除不可
        if not project.is_draft:
            return JsonResponse({'success': False, 'message': '下書き以外のプロジェクトは削除できません'}, status=403)

        # プロジェクト名を保存してから削除
        project_name = project.site_name or "無題の下書き"
        project.delete()

        return JsonResponse({
            'success': True,
            'message': f'「{project_name}」を削除しました'
        })

    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'プロジェクトが見つかりません'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'削除中にエラーが発生しました: {str(e)}'}, status=500)


@login_required
def project_create(request):
    """案件新規作成"""
    from subcontract_management.models import InternalWorker, Subcontract

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()

            # 営業担当者（sales_manager）をproject_managerに保存
            sales_manager_id = request.POST.get('sales_manager')
            if sales_manager_id:
                try:
                    sales_worker = InternalWorker.objects.get(id=sales_manager_id)
                    project.project_manager = sales_worker.name
                    project.save()
                except InternalWorker.DoesNotExist:
                    pass

            # 実施体制に応じて作業者情報を処理
            implementation_type = request.POST.get('implementation_type')

            if implementation_type == 'outsource':
                # 外注先作業者の処理
                contractor_input_type = request.POST.get('contractor_input_type')
                contract_amount = request.POST.get('contract_amount')
                billed_amount = request.POST.get('billed_amount')
                payment_due_date = request.POST.get('payment_due_date')
                payment_status = request.POST.get('payment_status', 'pending')
                purchase_order_issued = request.POST.get('purchase_order_issued') == 'on'

                contractor = None

                if contractor_input_type == 'existing':
                    existing_contractor_id = request.POST.get('existing_contractor_id')
                    if existing_contractor_id:
                        contractor = Contractor.objects.get(id=existing_contractor_id)
                elif contractor_input_type == 'new':
                    new_contractor_name = request.POST.get('new_contractor_name')
                    if new_contractor_name:
                        contractor = Contractor.objects.create(
                            name=new_contractor_name,
                            address='',  # 後で詳細画面で設定
                            is_active=True
                        )

                # 外注契約を作成
                if contractor and contract_amount:
                    work_description = request.POST.get('external_work_description', '')

                    # stepフィールドを処理（プレフィックスがなければ追加）
                    step_value = request.POST.get('step', '')
                    if step_value and not step_value.startswith('step_'):
                        step_value = f'step_{step_value}'

                    Subcontract.objects.create(
                        project=project,
                        contractor=contractor,
                        worker_type='external',
                        work_description=work_description,
                        contract_amount=float(contract_amount) if contract_amount else 0,
                        billed_amount=float(billed_amount) if billed_amount else 0,
                        payment_due_date=payment_due_date if payment_due_date else None,
                        payment_status=payment_status,
                        purchase_order_issued=purchase_order_issued,
                        step=step_value if step_value else None
                    )

            elif implementation_type == 'internal':
                # 社内リソースの処理
                internal_input_type = request.POST.get('internal_input_type')
                internal_worker = None

                if internal_input_type == 'existing':
                    existing_internal_id = request.POST.get('existing_internal_id')
                    if existing_internal_id:
                        internal_worker = InternalWorker.objects.get(id=existing_internal_id)
                elif internal_input_type == 'new':
                    internal_worker_name = request.POST.get('internal_worker_name')
                    internal_department = request.POST.get('internal_department')
                    internal_hourly_rate = request.POST.get('internal_hourly_rate')
                    internal_specialties = request.POST.get('internal_specialties')
                    internal_is_active = request.POST.get('internal_is_active') == 'on'

                    if internal_worker_name:
                        internal_worker = InternalWorker.objects.create(
                            name=internal_worker_name,
                            department=internal_department,
                            hourly_rate=float(internal_hourly_rate) if internal_hourly_rate else 0,
                            specialties=internal_specialties,
                            is_active=internal_is_active
                        )

                # 社内担当を契約として作成
                if internal_worker:
                    # 新しいフィールドを取得
                    work_description = request.POST.get('work_description', '')
                    internal_pricing_type = request.POST.get('internal_pricing_type', 'hourly')
                    estimated_hours = request.POST.get('estimated_hours')
                    tax_type = request.POST.get('tax_type', 'include')
                    internal_contract_amount = request.POST.get('internal_contract_amount')
                    internal_payment_due_date = request.POST.get('internal_payment_due_date')
                    internal_payment_status = request.POST.get('internal_payment_status', 'pending')

                    # stepフィールドを処理（プレフィックスがなければ追加）
                    step_value = request.POST.get('step', '')
                    if step_value and not step_value.startswith('step_'):
                        step_value = f'step_{step_value}'

                    Subcontract.objects.create(
                        project=project,
                        internal_worker=internal_worker,
                        worker_type='internal',
                        work_description=work_description,
                        pricing_type=internal_pricing_type,
                        estimated_hours=float(estimated_hours) if estimated_hours else None,
                        tax_type=tax_type,
                        contract_amount=float(internal_contract_amount) if internal_contract_amount else 0,
                        billed_amount=float(internal_contract_amount) if internal_contract_amount else 0,
                        payment_due_date=internal_payment_due_date if internal_payment_due_date else None,
                        payment_status=internal_payment_status,
                        step=step_value if step_value else None
                    )

            # スケジュールステップデータの保存
            schedule_steps_json = request.POST.get('schedule_steps_data', '')
            if schedule_steps_json:
                from order_management.services.progress_step_service import save_project_progress_steps
                save_project_progress_steps(project, schedule_steps_json)

            messages.success(request, f'案件「{project.site_name}」を登録しました。')

            # AJAX リクエストの場合
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('order_management:project_detail', kwargs={'pk': project.pk}),
                    'message': f'案件「{project.site_name}」を登録しました。'
                })

            return redirect('order_management:project_detail', pk=project.pk)
        else:
            # フォームバリデーションエラー - AJAX の場合
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'フォームの入力内容に誤りがあります。'
                }, status=400)
    else:
        form = ProjectForm()

    # フォーム表示用のデータを準備
    from .models import ClientCompany
    from subcontract_management.models import ContractorFieldCategory
    client_companies = ClientCompany.objects.prefetch_related('contact_persons').filter(is_active=True).order_by('company_name')
    contractors = Contractor.objects.filter(is_active=True)  # 協力会社（作業者追加用）
    internal_workers = InternalWorker.objects.filter(is_active=True)

    # カスタムフィールド定義をカテゴリごとに取得（業者モーダル用）
    contractor_categories = ContractorFieldCategory.objects.filter(
        is_active=True
    ).prefetch_related('field_definitions').order_by('order')

    contractor_custom_fields_by_category = []
    for category in contractor_categories:
        fields_data = []
        for field_def in category.field_definitions.filter(is_active=True).order_by('order'):
            fields_data.append({
                'definition': field_def,
                'current_value': ''  # 新規作成なので空
            })

        if fields_data:  # フィールドがある場合のみ追加
            contractor_custom_fields_by_category.append({
                'category': category,
                'fields': fields_data
            })

    # 地方ごとの都道府県マッピング（業者モーダルの対応地域用）
    regions_mapping = {
        '北海道': ['北海道'],
        '東北': ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県'],
        '関東': ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県'],
        '中部': ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県'],
        '近畿': ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県'],
        '中国': ['鳥取県', '島根県', '岡山県', '広島県', '山口県'],
        '四国': ['徳島県', '香川県', '愛媛県', '高知県'],
        '九州': ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
    }

    # internal_workersをJSON形式でシリアライズ
    import json
    internal_workers_json = json.dumps([{
        'id': w.id,
        'name': w.name,
        'department': w.department,
        'hourly_rate': float(w.hourly_rate) if w.hourly_rate else 0,
        'specialties': w.specialties or '',
        'is_active': w.is_active
    } for w in internal_workers])

    # contractorsをJSON形式でシリアライズ（Phase 1.2で追加、Phase 4で更新）
    contractors_json = json.dumps([{
        'id': c.id,
        'name': c.name,
        'address': c.address or '',
        'phone': c.phone or '',
        'email': c.email or '',
        'contact_person': c.contact_person or '',
        'specialties': c.specialties or '',
        'payment_cycle': c.payment_cycle or '',
        'closing_day': c.closing_day if c.closing_day is not None else '',
        'payment_offset_months': c.payment_offset_months if c.payment_offset_months is not None else '',
        'payment_day': c.payment_day if c.payment_day is not None else '',
        'is_active': c.is_active,
    } for c in contractors])

    # 支払いサイクルの日本語マッピング
    payment_cycle_labels = {
        'monthly': '月1回',
        'bimonthly': '月2回',
        'weekly': '週1回',
        'custom': 'その他'
    }

    # client_companiesをJSON形式でシリアライズ
    def get_primary_contact(company):
        """主担当者を取得するヘルパー関数"""
        primary = company.contact_persons.filter(is_primary=True).first()
        if not primary:
            primary = company.contact_persons.first()
        return primary

    client_companies_json = json.dumps([{
        'id': c.id,
        'company_name': c.company_name,
        'address': c.address or '',
        'phone': get_primary_contact(c).phone if get_primary_contact(c) else '',
        'contact_person': get_primary_contact(c).name if get_primary_contact(c) else '',
        'payment_cycle': c.payment_cycle or '',
        'payment_cycle_label': payment_cycle_labels.get(c.payment_cycle, c.payment_cycle) if c.payment_cycle else '',
        'closing_day': c.closing_day,
        'payment_offset_months': c.payment_offset_months,
        'payment_day': c.payment_day,
        'is_active': c.is_active
    } for c in client_companies])

    return render(request, 'order_management/project_form.html', {
        'form': form,
        'title': '案件新規登録',
        'client_companies': client_companies,  # 元請会社
        'client_companies_json': client_companies_json,
        'contractors': contractors,  # 協力会社（作業者追加で使用）
        'contractors_json': contractors_json,  # Phase 1.2で追加
        'internal_workers': internal_workers,
        'internal_workers_json': internal_workers_json,
        'contractor_custom_fields_by_category': contractor_custom_fields_by_category,  # 業者モーダル用カスタムフィールド
        'regions_mapping': regions_mapping,  # 都道府県マッピング
    })


@login_required
def project_save_as_draft(request, pk=None):
    """プロジェクトを下書きとして保存（新規作成または更新）"""
    import json
    from django.http import JsonResponse
    from subcontract_management.models import InternalWorker

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTメソッドが必要です'}, status=400)

    try:
        # 既存プロジェクトの更新または新規作成
        if pk:
            project = get_object_or_404(Project, pk=pk)
            form = ProjectForm(request.POST, instance=project)
        else:
            form = ProjectForm(request.POST)

        # バリデーション（下書きなので必須項目チェックを緩和）
        # 管理Noは自動生成するか、空でも許可
        if not request.POST.get('management_no'):
            # 管理Noが空の場合、仮の番号を生成
            temp_no = f"DRAFT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            mutable_post = request.POST.copy()
            mutable_post['management_no'] = temp_no
            form = ProjectForm(mutable_post, instance=project if pk else None)

        # 下書きとして保存（バリデーションエラーを無視）
        if form.is_valid():
            project = form.save(commit=False)
            project.is_draft = True
            project.save()
            # ManyToManyフィールドを保存（work_typesなど）
            form.save_m2m()

            # 営業担当者の保存
            sales_manager_id = request.POST.get('sales_manager')
            if sales_manager_id:
                try:
                    sales_worker = InternalWorker.objects.get(id=sales_manager_id)
                    project.project_manager = sales_worker.name
                    project.save()
                except InternalWorker.DoesNotExist:
                    pass

            # 追加項目（dynamic_steps、schedule_stepsなど）を保存
            if 'dynamic_steps_data' in request.POST:
                try:
                    dynamic_steps = json.loads(request.POST.get('dynamic_steps_data', '{}'))
                    if not project.additional_items:
                        project.additional_items = {}
                    project.additional_items['dynamic_steps'] = dynamic_steps
                    project.save()
                except json.JSONDecodeError:
                    pass

            # スケジュールステップデータの保存（下書きでも保存）
            if 'schedule_steps_data' in request.POST:
                schedule_steps_json = request.POST.get('schedule_steps_data', '')
                if schedule_steps_json:
                    try:
                        from order_management.services.progress_step_service import save_project_progress_steps
                        save_project_progress_steps(project, schedule_steps_json)
                    except Exception as e:
                        print(f"⚠ Error saving progress steps in draft: {e}")

            return JsonResponse({
                'success': True,
                'project_id': project.pk,
                'message': '下書きとして保存しました',
                'updated_at': timezone.localtime(project.updated_at).strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            # バリデーションエラーがあっても下書きとして保存を試みる
            from django.db.models import ForeignKey, ManyToManyField, DecimalField, IntegerField, CharField, TextField
            from decimal import Decimal, InvalidOperation

            project = Project()
            if pk:
                project = get_object_or_404(Project, pk=pk)

            # モデルのフィールド情報を取得
            fk_fields = {}
            m2m_fields = {}
            decimal_fields = set()
            integer_fields = set()
            char_text_fields = set()

            for field in Project._meta.get_fields():
                if isinstance(field, ForeignKey):
                    fk_fields[field.name] = field.related_model
                elif isinstance(field, ManyToManyField):
                    m2m_fields[field.name] = field
                elif isinstance(field, DecimalField):
                    decimal_fields.add(field.name)
                elif isinstance(field, IntegerField):
                    integer_fields.add(field.name)
                elif isinstance(field, (CharField, TextField)):
                    char_text_fields.add(field.name)

            # フォームデータを手動で設定（ManyToManyフィールド以外）
            for field_name in form.fields:
                if field_name in request.POST:
                    value = request.POST.get(field_name)

                    # ManyToManyフィールドはスキップ（後で処理）
                    if field_name in m2m_fields:
                        continue

                    # ForeignKeyフィールドの特別処理
                    if field_name in fk_fields and value:
                        try:
                            related_model = fk_fields[field_name]
                            related_instance = related_model.objects.get(pk=value)
                            setattr(project, field_name, related_instance)
                        except Exception:
                            pass  # 無効なIDやモデル取得エラーの場合はスキップ

                    # DecimalFieldの特別処理
                    elif field_name in decimal_fields:
                        try:
                            if value == '' or value is None:
                                setattr(project, field_name, None)
                            else:
                                setattr(project, field_name, Decimal(str(value)))
                        except (ValueError, TypeError, InvalidOperation):
                            pass  # 型変換エラーの場合はスキップ

                    # IntegerFieldの特別処理
                    elif field_name in integer_fields:
                        try:
                            if value == '' or value is None:
                                setattr(project, field_name, None)
                            else:
                                setattr(project, field_name, int(value))
                        except (ValueError, TypeError):
                            pass  # 型変換エラーの場合はスキップ

                    # CharField/TextFieldの特別処理（空文字列を保存）
                    elif field_name in char_text_fields:
                        try:
                            # CharField/TextFieldは空文字列を許可（Noneではなく''）
                            setattr(project, field_name, value if value is not None else '')
                        except (ValueError, TypeError):
                            pass  # 型変換エラーの場合はスキップ

                    else:
                        # その他のフィールド
                        try:
                            setattr(project, field_name, value if value != '' else None)
                        except (ValueError, TypeError):
                            pass  # 型変換エラーの場合はスキップ

            # 営業担当者（sales_manager）をproject_managerに保存
            sales_manager_id = request.POST.get('sales_manager')
            if sales_manager_id:
                try:
                    sales_worker = InternalWorker.objects.get(id=sales_manager_id)
                    project.project_manager = sales_worker.name
                except InternalWorker.DoesNotExist:
                    pass

            project.is_draft = True
            project.save()

            # ManyToManyフィールドの保存（プロジェクトが保存された後に実行）
            for field_name in m2m_fields:
                if field_name in request.POST:
                    values = request.POST.getlist(field_name)
                    if values:
                        try:
                            m2m_manager = getattr(project, field_name)
                            m2m_manager.set(values)
                        except Exception as e:
                            print(f"⚠ Error setting M2M field {field_name}: {e}")

            # スケジュールステップデータの保存（下書きでも保存）
            if 'schedule_steps_data' in request.POST:
                schedule_steps_json = request.POST.get('schedule_steps_data', '')
                if schedule_steps_json:
                    try:
                        from order_management.services.progress_step_service import save_project_progress_steps
                        save_project_progress_steps(project, schedule_steps_json)
                    except Exception as e:
                        print(f"⚠ Error saving progress steps in draft (validation error path): {e}")

            return JsonResponse({
                'success': True,
                'project_id': project.pk,
                'message': '下書きとして保存しました（一部フィールドは未検証）',
                'updated_at': timezone.localtime(project.updated_at).strftime('%Y-%m-%d %H:%M:%S')
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Auto-save error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def project_detail(request, pk):
    """案件詳細表示"""
    from subcontract_management.models import Contractor, Subcontract, ProjectProfitAnalysis
    from subcontract_management.forms import SubcontractForm

    project = get_object_or_404(Project.objects.select_related('client_company'), pk=pk)

    # 外注情報を取得
    subcontracts = Subcontract.objects.filter(project=project).select_related('contractor')
    contractors = Contractor.objects.filter(is_active=True)

    # 社内担当者を取得
    from subcontract_management.models import InternalWorker
    internal_workers = InternalWorker.objects.filter(is_active=True)

    # 現地調査情報を取得
    # TODO: surveysアプリを実装したら有効化
    #from surveys.models import Survey
    #surveys = Survey.objects.filter(project=project).select_related('surveyor').order_by('-scheduled_date')
    surveys = []  # surveysアプリ未実装のため空リストを返す

    # 外注統計計算
    # 基本契約金額の合計（被請求額がある場合はそれを使用、なければ契約金額）
    total_subcontract_cost = sum((s.billed_amount if s.billed_amount else s.contract_amount) or 0 for s in subcontracts)
    total_material_cost = sum(s.total_material_cost or 0 for s in subcontracts)

    # 追加費用の合計（dynamic_cost_items から計算）
    total_additional_cost = 0
    for s in subcontracts:
        if s.dynamic_cost_items:
            for item in s.dynamic_cost_items:
                if 'cost' in item:
                    total_additional_cost += float(item['cost'])

    # MaterialOrderの資材発注合計を追加
    material_order_total = sum(m.total_amount or 0 for m in project.material_orders.all())

    unpaid_amount = sum((s.billed_amount if s.billed_amount else s.contract_amount) or 0 for s in subcontracts.filter(payment_status='pending'))

    # 暫定利益率計算用の既存総費用（追加費用を含む）
    # get_total_cost() = (billed_amount or contract_amount) + total_material_cost + additional_cost (from dynamic_cost_items)
    existing_total_cost = sum(s.get_total_cost() for s in subcontracts)

    # 利益分析
    profit_analysis = None
    try:
        profit_analysis = ProjectProfitAnalysis.objects.get(project=project)
    except ProjectProfitAnalysis.DoesNotExist:
        pass

    # 経理情報の計算
    from decimal import Decimal

    revenue = project.billing_amount  # 売上高
    cost_of_sales = total_subcontract_cost + total_material_cost + total_additional_cost + material_order_total  # 売上原価（外注費＋材料費＋追加費用＋資材発注）
    selling_expenses = project.expense_amount_1 + project.expense_amount_2 + project.parking_fee  # 販売費（諸経費＋駐車場代）
    gross_profit = revenue - cost_of_sales  # 粗利
    gross_profit_rate = (gross_profit / revenue * Decimal('100')) if revenue > 0 else Decimal('0')  # 粗利率

    # 販管費は計算に含めない（実際の販管費データがない為）
    # operating_profit = gross_profit - selling_expenses  # 営業利益（販売費のみ差し引き）
    # operating_profit_rate = (operating_profit / revenue * Decimal('100')) if revenue > 0 else Decimal('0')  # 営業利益率

    # 経理情報をまとめる
    financial_info = {
        'revenue': revenue,
        'cost_of_sales': cost_of_sales,
        'selling_expenses': selling_expenses,
        'gross_profit': gross_profit,
        'gross_profit_rate': gross_profit_rate,
        # 詳細内訳
        'subcontract_cost': total_subcontract_cost,
        'material_cost': total_material_cost,
        'additional_cost': total_additional_cost,
        'material_order_cost': material_order_total,  # 資材発注費用を追加
        'expense_1': project.expense_amount_1,
        'expense_2': project.expense_amount_2,
        'parking_fee': project.parking_fee,
    }

    # 新規外注フォーム
    subcontract_form = SubcontractForm()

    # ProjectProgressStepテーブルからステップを読み込む
    from order_management.models import ProjectProgressStep
    from order_management.services.progress_step_service import STEP_TEMPLATES

    # ステップキーのマッピング（テンプレート名 -> キー）
    template_to_key = {}
    for key, config in STEP_TEMPLATES.items():
        template_to_key[config['name']] = key

    # ProjectProgressStepから読み込み
    progress_steps = ProjectProgressStep.objects.filter(
        project=project,
        is_active=True
    ).select_related('template').order_by('order')

    ordered_steps = []
    step_order = []

    if progress_steps.exists():
        # ProjectProgressStepから読み込む
        for step in progress_steps:
            # テンプレート名からキーを取得（step_プレフィックス付き）
            step_key_without_prefix = template_to_key.get(step.template.name)
            if not step_key_without_prefix:
                continue

            # step_プレフィックスを付ける
            step_key = f'step_{step_key_without_prefix}'

            # scheduled_dateを取得
            scheduled_date = ''
            if step.value and isinstance(step.value, dict):
                scheduled_date = step.value.get('scheduled_date', '')

            step_data = {
                'key': step_key,
                'order': step.order,
                'completed': step.is_completed,
                'is_dynamic': True,
                'data': {
                    'type': 'date',  # フロントエンドが期待するフィールド
                    'date': scheduled_date,  # フロントエンドが期待するフィールド
                    'scheduled_date': scheduled_date,
                    'completed': step.is_completed
                }
            }
            ordered_steps.append(step_data)

            # step_orderも作成（互換性のため）
            step_order.append({
                'step': step_key,
                'label': step.template.name,
                'order': step.order
            })
    else:
        # ProjectProgressStepが存在しない場合、デフォルトステップを設定
        DEFAULT_STEPS = [
            {'step': 'step_attendance', 'order': 1},
            {'step': 'step_survey', 'order': 2},
            {'step': 'step_estimate', 'order': 3},
            {'step': 'step_construction_start', 'order': 4},
            {'step': 'step_completion', 'order': 5},
        ]

        for step_item in DEFAULT_STEPS:
            step_key = step_item['step']
            step_data = {
                'key': step_key,
                'order': step_item['order'],
                'completed': False,
                'is_dynamic': False,
                'data': {}
            }
            ordered_steps.append(step_data)
            step_order.append(step_item)

    # ProjectProgressStepからcomplex_step_fieldsを構築
    complex_step_fields = {}
    for step in progress_steps:
        step_key_without_prefix = template_to_key.get(step.template.name)
        if not step_key_without_prefix:
            continue

        # step_プレフィックス付きのキーを使用
        step_key = f'step_{step_key_without_prefix}'

        # scheduled_date
        if step.value and isinstance(step.value, dict):
            scheduled_date = step.value.get('scheduled_date', '')
            if scheduled_date:
                complex_step_fields[f'{step_key}_scheduled_date'] = scheduled_date

        # completed
        if step.is_completed:
            complex_step_fields[f'{step_key}_completed'] = 'true'

    # 動的ステップデータは後方互換性のために保持（使用されていない）
    dynamic_steps = {}
    if project.additional_items:
        dynamic_steps = project.additional_items.get('dynamic_steps', {})

    import json

    # ステップ別の下請け情報を取得
    attendance_subcontracts = subcontracts.filter(step='step_attendance')
    survey_subcontracts = subcontracts.filter(step='step_survey')
    construction_start_subcontracts = subcontracts.filter(step='step_construction_start')

    # ステップ別の下請け情報をJSON化（JavaScript用）
    def serialize_subcontracts(subs):
        return json.dumps([{
            'id': s.id,
            'contractor_name': s.contractor.name if s.contractor else '業者未設定',
            'contract_amount': float(s.contract_amount or 0),
            'billed_amount': float(s.billed_amount) if s.billed_amount else None,
            'payment_status': s.payment_status,
            'payment_status_display': s.get_payment_status_display(),
            'payment_status_color': 'success' if s.payment_status == 'paid' else ('info' if s.payment_status == 'processing' else 'warning'),
        } for s in subs])

    attendance_subcontracts_json = serialize_subcontracts(attendance_subcontracts)
    survey_subcontracts_json = serialize_subcontracts(survey_subcontracts)
    construction_start_subcontracts_json = serialize_subcontracts(construction_start_subcontracts)

    # 資材発注情報をJSON化（JavaScript用）
    material_orders = project.material_orders.all()
    material_orders_json = json.dumps([{
        'id': m.id,
        'contractor': {'name': m.contractor.name} if m.contractor else None,
        'total_amount': float(m.total_amount or 0),
        'order_date': m.order_date.strftime('%Y/%m/%d') if m.order_date else None,
        'status': m.status,
        'status_display': m.get_status_display(),
        'items': [{
            'material_name': item.material_name,
        } for item in m.items.all()[:1]] if m.items.exists() else []
    } for m in material_orders])

    # 発注先の支払いサイクル情報をJSON化（JavaScript用）
    contractors_json = json.dumps([{
        'id': c.id,
        'name': c.name,
        'address': c.address if c.address else '',
        'phone': c.phone if c.phone else '',
        'contact_person': c.contact_person if c.contact_person else '',
        'specialties': c.specialties if c.specialties else '',
        'payment_cycle': c.payment_cycle if c.payment_cycle else '',
        'payment_cycle_display': c.get_payment_cycle_display() if c.payment_cycle else '-',
        'closing_day': c.closing_day if c.closing_day else None,
        'payment_offset_months': c.payment_offset_months if c.payment_offset_months is not None else None,
        'payment_offset_months_display': c.get_payment_offset_months_display() if c.payment_offset_months is not None else '-',
        'payment_day': c.payment_day if c.payment_day else None,
        'is_active': c.is_active,
    } for c in contractors])

    # 元請会社情報を取得してJSON化（JavaScript用）
    client_companies = ClientCompany.objects.all().order_by('company_name')

    # 支払いサイクルの日本語マッピング
    payment_cycle_labels = {
        'monthly': '月1回',
        'bimonthly': '月2回',
        'weekly': '週1回',
        'custom': 'その他'
    }

    def get_primary_contact(company):
        """主担当者を取得するヘルパー関数"""
        primary = company.contact_persons.filter(is_primary=True).first()
        if not primary:
            primary = company.contact_persons.first()
        return primary

    client_companies_json = json.dumps([{
        'id': c.id,
        'company_name': c.company_name,
        'address': c.address or '',
        'phone': get_primary_contact(c).phone if get_primary_contact(c) else '',
        'contact_person': get_primary_contact(c).name if get_primary_contact(c) else '',
        'payment_cycle': c.payment_cycle or '',
        'payment_cycle_label': payment_cycle_labels.get(c.payment_cycle, c.payment_cycle) if c.payment_cycle else '',
        'closing_day': c.closing_day,
        'payment_offset_months': c.payment_offset_months,
        'payment_day': c.payment_day,
        'is_active': c.is_active
    } for c in client_companies])

    # 工事種別マスターを取得してJSON化（JavaScript用）
    work_types = WorkType.objects.filter(is_active=True).order_by('display_order')
    work_types_json = json.dumps([{
        'id': w.id,
        'name': w.name,
    } for w in work_types])

    # 見積もりステップのファイルを取得
    estimate_files = project.files.filter(related_step='estimate').order_by('-uploaded_at')
    estimate_files_json = json.dumps([{
        'id': f.id,
        'file_name': f.file_name,
        'file_size': f.get_file_size_display(),
        'file_type': f.file_type,
        'uploaded_at': f.uploaded_at.strftime('%Y-%m-%d %H:%M') if f.uploaded_at else '',
        'uploaded_by': f.uploaded_by.username if f.uploaded_by else '不明'
    } for f in estimate_files])

    # プロジェクトの現在の進捗状況を取得（キャッシュされた値）
    stage = project.get_current_project_stage()

    return render(request, 'order_management/project_detail.html', {
        'project': project,
        'subcontracts': subcontracts,
        'contractors': contractors,
        'contractors_json': contractors_json,
        'client_companies': client_companies,
        'client_companies_json': client_companies_json,
        'work_types': work_types,
        'work_types_json': work_types_json,
        'internal_workers': internal_workers,
        'surveys': surveys,  # 追加
        'subcontract_form': subcontract_form,
        'total_subcontract_cost': total_subcontract_cost,
        'total_material_cost': total_material_cost,
        'unpaid_amount': unpaid_amount,
        'existing_total_cost': existing_total_cost,
        'profit_analysis': profit_analysis,
        'financial_info': financial_info,
        'dynamic_steps': dynamic_steps,
        'step_order': step_order,
        'ordered_steps': ordered_steps,
        'ordered_steps_json': json.dumps(ordered_steps),
        'dynamic_steps_json': json.dumps(dynamic_steps),
        'complex_step_fields': complex_step_fields,
        'complex_step_fields_json': json.dumps(complex_step_fields),
        'estimate_files': estimate_files,
        'estimate_files_json': estimate_files_json,
        'stage': stage,  # プロジェクト進捗状況（キャッシュ値）
        # ステップ別下請け情報
        'attendance_subcontracts': attendance_subcontracts,
        'survey_subcontracts': survey_subcontracts,
        'construction_start_subcontracts': construction_start_subcontracts,
        'attendance_subcontracts_json': attendance_subcontracts_json,
        'survey_subcontracts_json': survey_subcontracts_json,
        'construction_start_subcontracts_json': construction_start_subcontracts_json,
        'material_orders_json': material_orders_json,
    })


@login_required
def update_progress(request, pk):
    """進捗状況の更新（統一エンドポイント）"""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        import json

        # AJAXリクエストかどうかをチェック（編集完了ボタン用）
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax_save')

        estimate_issued_date = request.POST.get('estimate_issued_date')
        estimate_notes = request.POST.get('estimate_notes')
        contractor_estimate_amount = request.POST.get('contractor_estimate_amount')
        contract_date = request.POST.get('contract_date')
        work_start_date = request.POST.get('work_start_date')
        work_end_date = request.POST.get('work_end_date')
        invoice_issued = request.POST.get('invoice_issued')
        work_start_completed = request.POST.get('work_start_completed')
        work_end_completed = request.POST.get('work_end_completed')
        estimate_not_required = request.POST.get('estimate_not_required')

        # 完了報告フィールド
        completion_report_date = request.POST.get('completion_report_date')
        completion_report_status = request.POST.get('completion_report_status')
        completion_report_content = request.POST.get('completion_report_content')
        completion_report_notes = request.POST.get('completion_report_notes')

        # 日付フィールドの更新（空文字列も処理）
        # DEPRECATED: estimate_issued_date, work_start_date, work_end_date moved to ProjectProgressStep
        if contract_date is not None:
            project.contract_date = contract_date if contract_date else None
        if invoice_issued is not None:
            # Boolean値に変換
            project.invoice_issued = invoice_issued.lower() == 'true' if invoice_issued else False

        # 完了チェックボックスの更新
        # DEPRECATED: work_start_completed, work_end_completed moved to ProjectProgressStep
        project.estimate_not_required = estimate_not_required == 'on'

        # 見積もり関連テキストフィールドの更新
        if estimate_notes is not None:
            project.estimate_notes = estimate_notes
        if contractor_estimate_amount is not None:
            project.contractor_estimate_amount = contractor_estimate_amount

        # 完了報告フィールドの更新
        if completion_report_date is not None:
            project.completion_report_date = completion_report_date if completion_report_date else None
        if completion_report_status is not None:
            project.completion_report_status = completion_report_status if completion_report_status else 'not_created'
        if completion_report_content is not None:
            project.completion_report_content = completion_report_content
        if completion_report_notes is not None:
            project.completion_report_notes = completion_report_notes

        # 完了報告ファイルのアップロード処理
        if 'completion_report_file' in request.FILES:
            project.completion_report_file = request.FILES['completion_report_file']

        # 完了チェックボックスの更新
        completion_report_completed = request.POST.get('completion_report_completed')
        project.completion_report_completed = completion_report_completed == 'on'

        # 進捗コメントの更新
        progress_comment = request.POST.get('progress_comment')
        if progress_comment is not None:
            project.progress_comment = progress_comment

        # 追加項目の処理
        additional_items = {}
        for key, value in request.POST.items():
            if key.startswith('additional_item_'):
                # additional_item_xxx形式のキーから項目名を抽出
                item_key = key.replace('additional_item_', '')
                if value.strip():  # 空でない値のみ保存
                    additional_items[item_key] = value.strip()

        # ProjectProgressStepの処理（step_orderの代わり）
        from order_management.models import ProjectProgressStep
        from order_management.services.progress_step_service import STEP_TEMPLATES

        # ステップテンプレートのマッピング（キー名 -> テンプレート名）
        key_to_template = {
            'attendance': '立ち会い日',
            'survey': '現調日',
            'estimate': '見積書発行日',
            'construction_start': '着工日',
            'completion': '完工日',
            'contract': '契約',
            'invoice': '請求書発行',
            'permit_application': '許可申請',
            'material_order': '資材発注',
            'inspection': '検査',
        }

        # 複合ステップのフィールドデータを処理
        complex_step_fields = {}
        for key, value in request.POST.items():
            if key.startswith('dynamic_field_'):
                # dynamic_field_プレフィックスを削除してフィールド名を取得
                field_name = key.replace('dynamic_field_', '')
                if value.strip():  # 空でない値のみ保存
                    complex_step_fields[field_name] = value.strip()
                else:
                    # 空の値の場合、Noneを設定（削除ではなく）
                    complex_step_fields[field_name] = None

        # ProjectProgressStepを更新
        # まず、complex_step_fieldsから各ステップのデータを抽出してProjectProgressStepを更新
        from order_management.models import ProgressStepTemplate

        for step_key, template_name in key_to_template.items():
            # 🔧 FIX: step_プレフィックスありとなし両方をサポート
            # HTMLから送信されるキーは "step_attendance_scheduled_date" の形式
            scheduled_date_key = f'{step_key}_scheduled_date'
            scheduled_date_key_with_prefix = f'step_{step_key}_scheduled_date'
            completed_key = f'{step_key}_completed'
            completed_key_with_prefix = f'step_{step_key}_completed'
            actual_date_key_with_prefix = f'step_{step_key}_actual_date'

            # 両方の形式をチェック（step_プレフィックスありを優先）
            scheduled_date = (complex_step_fields.get(scheduled_date_key_with_prefix) or
                            complex_step_fields.get(scheduled_date_key))
            actual_date = complex_step_fields.get(actual_date_key_with_prefix)
            completed_str = (complex_step_fields.get(completed_key_with_prefix) or
                           complex_step_fields.get(completed_key))
            completed = completed_str in ['on', 'true', True]

            # 🔧 FIX: このステップに関するフィールドが送信されていない場合はスキップ
            # これにより、ユーザーが追加していないステップのProjectProgressStepが勝手に作成されるのを防ぐ
            has_scheduled_date = (scheduled_date_key_with_prefix in complex_step_fields or
                                scheduled_date_key in complex_step_fields)
            has_completed = (completed_key_with_prefix in complex_step_fields or
                           completed_key in complex_step_fields)
            has_actual_date = actual_date_key_with_prefix in complex_step_fields

            if not has_scheduled_date and not has_completed and not has_actual_date:
                # このステップに関するデータが送信されていないのでスキップ
                continue

            # テンプレートを取得
            try:
                template = ProgressStepTemplate.objects.get(name=template_name)
            except ProgressStepTemplate.DoesNotExist:
                continue

            # ProjectProgressStepを取得または作成
            progress_step, created = ProjectProgressStep.objects.get_or_create(
                project=project,
                template=template,
                defaults={'order': list(key_to_template.keys()).index(step_key) + 1}
            )

            # 値を更新
            if has_completed:
                progress_step.is_completed = completed

            # valueフィールドの初期化
            if not progress_step.value:
                progress_step.value = {}

            # 予定日を更新
            if has_scheduled_date:
                if scheduled_date:
                    progress_step.value['scheduled_date'] = scheduled_date
                elif 'scheduled_date' in progress_step.value:
                    # 空にされた場合は削除
                    del progress_step.value['scheduled_date']

            # 実施日を更新
            if has_actual_date:
                if actual_date:
                    progress_step.value['actual_date'] = actual_date
                elif 'actual_date' in progress_step.value:
                    # 空にされた場合は削除
                    del progress_step.value['actual_date']

            progress_step.save()

        # 既存の追加項目と新しい項目をマージ
        if not project.additional_items:
            project.additional_items = {}

        # 追加項目を更新
        if additional_items:
            project.additional_items.update(additional_items)

        # 複合ステップのフィールドデータを保存（後方互換性のため残す）
        if complex_step_fields:
            project.additional_items['complex_step_fields'] = complex_step_fields

            # DEPRECATED: Dual-write to old fields removed - data now only in ProjectProgressStep

        project.save()
        project.refresh_from_db()

        # AJAX リクエストの場合はJSONレスポンスを返す
        if is_ajax:
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': '変更を保存しました'
            })

        # メッセージを表示しない（ユーザーの要望）
        # messages.success(request, '進捗状況を更新しました。')

    return redirect('order_management:project_detail', pk=pk)


@login_required
def add_subcontract(request, pk):
    """案件詳細ページから作業者を追加（外注・社内リソース対応）"""
    from subcontract_management.models import Contractor, Subcontract
    from datetime import datetime

    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)

        # 作業者タイプを取得
        worker_type = request.POST.get('worker_type', 'external')

        # 共通フィールド
        contract_amount_raw = request.POST.get('contract_amount', '')
        logger.info(f"=== 作業者追加デバッグ ===")
        logger.info(f"contract_amount (raw): '{contract_amount_raw}'")

        contract_amount = contract_amount_raw.strip()
        try:
            contract_amount = float(contract_amount) if contract_amount else 0
            logger.info(f"contract_amount (processed): {contract_amount}")
        except ValueError:
            logger.error(f"contract_amount 変換エラー: '{contract_amount}'")
            contract_amount = 0

        billed_amount = request.POST.get('billed_amount', '').strip()
        try:
            billed_amount = float(billed_amount) if billed_amount else 0
        except ValueError:
            billed_amount = 0

        payment_due_date = request.POST.get('payment_due_date', '').strip() or None
        payment_date = request.POST.get('payment_date', '').strip() or None
        payment_status = request.POST.get('payment_status') or 'pending'

        material_item_1 = request.POST.get('material_item_1', '').strip()
        material_cost_1 = request.POST.get('material_cost_1', '').strip()
        try:
            material_cost_1 = float(material_cost_1) if material_cost_1 else 0
        except ValueError:
            material_cost_1 = 0

        material_item_2 = request.POST.get('material_item_2', '').strip()
        material_cost_2 = request.POST.get('material_cost_2', '').strip()
        try:
            material_cost_2 = float(material_cost_2) if material_cost_2 else 0
        except ValueError:
            material_cost_2 = 0

        material_item_3 = request.POST.get('material_item_3', '').strip()
        material_cost_3 = request.POST.get('material_cost_3', '').strip()
        try:
            material_cost_3 = float(material_cost_3) if material_cost_3 else 0
        except ValueError:
            material_cost_3 = 0

        purchase_order_issued = request.POST.get('purchase_order_issued') == 'on'

        # 動的部材費の処理
        dynamic_material_costs = []
        if worker_type == 'external':
            # 外注先の場合
            material_items = request.POST.getlist('material_items[]')
            material_costs = request.POST.getlist('material_costs[]')
        else:
            # 社内リソースの場合
            material_items = request.POST.getlist('internal_material_items[]')
            material_costs = request.POST.getlist('internal_material_costs[]')

        # 動的部材費データを構築
        for i in range(len(material_items)):
            if i < len(material_costs) and material_items[i].strip():
                try:
                    cost = float(material_costs[i]) if material_costs[i] else 0
                    dynamic_material_costs.append({
                        'item': material_items[i].strip(),
                        'cost': cost
                    })
                except (ValueError, IndexError):
                    pass

        # 外注先情報（外注の場合のみ）
        contractor_input_type = request.POST.get('contractor_input_type', 'existing')
        existing_contractor_id = request.POST.get('existing_contractor_id', '').strip() or None
        contractor_name = request.POST.get('contractor_name', '').strip()
        contractor_address = request.POST.get('contractor_address', '').strip()

        # 社内リソース情報（社内の場合のみ）
        internal_input_type = request.POST.get('internal_input_type', 'new')
        existing_internal_id = request.POST.get('existing_internal_id', '').strip() or None
        internal_worker_name = request.POST.get('internal_worker_name', '').strip()
        internal_department = request.POST.get('internal_department', '').strip()
        internal_pricing_type = request.POST.get('internal_pricing_type', 'hourly')

        internal_hourly_rate = request.POST.get('internal_hourly_rate', '').strip()
        try:
            internal_hourly_rate = float(internal_hourly_rate) if internal_hourly_rate else None
        except ValueError:
            internal_hourly_rate = None

        estimated_hours = request.POST.get('estimated_hours', '').strip()
        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
        except ValueError:
            estimated_hours = None

        # 税込/税抜と動的費用項目
        tax_type = request.POST.get('tax_type', 'include')

        # 動的費用項目の処理（社内リソース用）
        dynamic_cost_items = []
        cost_items = request.POST.getlist('cost_items[]')
        cost_amounts = request.POST.getlist('cost_amounts[]')

        for i in range(len(cost_items)):
            if i < len(cost_amounts) and cost_items[i].strip():
                try:
                    amount = float(cost_amounts[i]) if cost_amounts[i] else 0
                    dynamic_cost_items.append({
                        'item': cost_items[i].strip(),
                        'cost': amount
                    })
                except (ValueError, IndexError):
                    pass

        # 追加費用項目の処理（外注先用）
        dynamic_additional_cost_items = []
        if worker_type == 'external':
            additional_cost_items = request.POST.getlist('additional_cost_items[]')
            additional_cost_amounts = request.POST.getlist('additional_cost_amounts[]')

            for i in range(len(additional_cost_items)):
                if i < len(additional_cost_amounts) and additional_cost_items[i].strip():
                    try:
                        amount = float(additional_cost_amounts[i]) if additional_cost_amounts[i] else 0
                        dynamic_additional_cost_items.append({
                            'item': additional_cost_items[i].strip(),
                            'cost': amount
                        })
                    except (ValueError, IndexError):
                        pass

        try:
            contractor = None
            internal_worker = None

            # 外注の場合のみ業者の取得または作成
            if worker_type == 'external':
                if contractor_input_type == 'existing' and existing_contractor_id:
                    # 既存業者を選択した場合
                    contractor = Contractor.objects.get(pk=existing_contractor_id)
                    created = False
                elif contractor_input_type == 'new' and contractor_name:
                    # 新規業者を入力した場合
                    contractor, created = Contractor.objects.get_or_create(
                        name=contractor_name,
                        defaults={
                            'address': contractor_address,
                            'contractor_type': 'company',
                            'is_active': True
                        }
                    )
                else:
                    # 外注先が選択されていない場合
                    messages.error(request, '外注先を選択してください。')
                    raise ValueError('外注先が選択されていません')

            # 社内リソースの場合の処理
            elif worker_type == 'internal':
                from subcontract_management.models import InternalWorker

                if internal_input_type == 'existing' and existing_internal_id:
                    # 既存担当者を選択した場合
                    internal_worker = InternalWorker.objects.get(pk=existing_internal_id)
                    # 担当者情報を自動設定
                    internal_worker_name = internal_worker.name
                    internal_department = internal_worker.get_department_display()
                    if not internal_hourly_rate:
                        internal_hourly_rate = internal_worker.hourly_rate

            # 日付フィールドの処理
            payment_due_date_obj = None
            payment_date_obj = None
            if payment_due_date and payment_due_date.strip():
                try:
                    payment_due_date_obj = datetime.strptime(payment_due_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if payment_date and payment_date.strip():
                try:
                    payment_date_obj = datetime.strptime(payment_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # stepフィールドを処理（プレフィックスがなければ追加）
            step_value = request.POST.get('step', '')
            if step_value and not step_value.startswith('step_'):
                step_value = f'step_{step_value}'

            # 作業管理レコードを作成
            subcontract_data = {
                'project': project,
                'management_no': project.management_no or '',
                'site_name': project.site_name or '',
                'site_address': project.site_address or '',
                'worker_type': worker_type,
                'contract_amount': contract_amount,
                'billed_amount': billed_amount,
                'payment_due_date': payment_due_date_obj,
                'payment_date': payment_date_obj,
                'payment_status': payment_status,
                'material_item_1': material_item_1,
                'material_cost_1': material_cost_1,
                'material_item_2': material_item_2,
                'material_cost_2': material_cost_2,
                'material_item_3': material_item_3,
                'material_cost_3': material_cost_3,
                'purchase_order_issued': purchase_order_issued,
                'dynamic_material_costs': dynamic_material_costs,
                'tax_type': tax_type,
                'step': step_value if step_value else None
            }

            # 外注の場合
            if worker_type == 'external':
                subcontract_data['contractor'] = contractor
                # 外注先の場合、dynamic_cost_itemsを追加費用項目として使用
                subcontract_data['dynamic_cost_items'] = dynamic_additional_cost_items
            # 社内リソースの場合
            else:
                subcontract_data.update({
                    'internal_worker': internal_worker,
                    'internal_worker_name': internal_worker_name,
                    'internal_department': internal_department,
                    'internal_pricing_type': internal_pricing_type,
                    'internal_hourly_rate': internal_hourly_rate,
                    'estimated_hours': estimated_hours,
                    'dynamic_cost_items': dynamic_cost_items
                })

                # 社内リソースの場合、contract_amountを計算
                total_dynamic_cost = sum(item['cost'] for item in dynamic_cost_items) if dynamic_cost_items else 0

                if internal_pricing_type == 'hourly':
                    # 時給ベース：基本料金 + 追加費用
                    base_amount = 0
                    if internal_hourly_rate and estimated_hours:
                        base_amount = float(internal_hourly_rate) * float(estimated_hours)
                    calculated_amount = base_amount + total_dynamic_cost
                    # フォームから送信された値を使用（JavaScriptで計算済み）
                    # ただし、0または空の場合は再計算した値を使用
                    if not contract_amount or float(contract_amount) == 0:
                        subcontract_data['contract_amount'] = calculated_amount
                else:
                    # 案件単位：フォームから送信された値またはdynamic_cost_itemsの合計
                    if not contract_amount or float(contract_amount) == 0:
                        subcontract_data['contract_amount'] = total_dynamic_cost

            # 保存直前のデータをログ出力
            logger.info(f"保存するSubcontractデータ:")
            logger.info(f"  - contract_amount: {subcontract_data.get('contract_amount')}")
            logger.info(f"  - billed_amount: {subcontract_data.get('billed_amount')}")
            logger.info(f"  - contractor: {subcontract_data.get('contractor')}")

            subcontract = Subcontract.objects.create(**subcontract_data)

            logger.info(f"保存後のSubcontractレコード:")
            logger.info(f"  - ID: {subcontract.id}")
            logger.info(f"  - contract_amount: {subcontract.contract_amount}")
            logger.info(f"  - billed_amount: {subcontract.billed_amount}")

            if worker_type == 'external':
                if 'created' in locals() and created:
                    messages.success(request, f'新しい外注先「{contractor_name}」を登録し、案件に追加しました。')
                else:
                    messages.success(request, f'外注先を案件に追加しました。')
            else:
                messages.success(request, f'社内リソース「{internal_worker_name}」を案件に追加しました。')

            # 成功時のみリダイレクト
            return redirect('order_management:project_detail', pk=pk)

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)

            error_details = traceback.format_exc()
            logger.error(f"作業者追加エラー: {error_details}")

            # デバッグ情報をログに出力
            logger.error(f"POST data: {request.POST}")
            logger.error(f"Worker type: {worker_type}")
            logger.error(f"Subcontract data: {subcontract_data if 'subcontract_data' in locals() else 'Not created'}")

            # ユーザーフレンドリーなエラーメッセージ
            error_message = str(e)
            if 'UNIQUE constraint' in error_message:
                messages.error(request, '同じ作業者が既に登録されています。')
            elif 'NOT NULL constraint' in error_message:
                # どのフィールドでエラーが発生したかを特定
                import re
                field_match = re.search(r'NOT NULL constraint failed: (\w+\.\w+)', error_message)
                if field_match:
                    field_name = field_match.group(1)
                    messages.error(request, f'必須項目が入力されていません: {field_name}')
                    logger.error(f"NOT NULL constraint on field: {field_name}")
                else:
                    messages.error(request, f'必須項目が入力されていません。詳細: {error_message}')
            elif 'FOREIGN KEY constraint' in error_message:
                messages.error(request, '選択された業者またはスタッフが見つかりません。')
            else:
                messages.error(request, f'作業者の追加中にエラーが発生しました: {str(e)}')

            # エラー時はフォームページに留まる（下のGET処理と同じコンテキストを使用）

    # GETリクエストの場合、フォームを表示
    from subcontract_management.models import Contractor, Subcontract
    contractors = Contractor.objects.all().order_by('-is_active', 'name')
    staff_members = User.objects.filter(is_staff=True).order_by('username')

    # 既存の作業費用を計算（利益率計算用）
    existing_subcontracts = Subcontract.objects.filter(project=project).select_related('contractor')
    existing_total_cost = sum(sc.get_total_cost() for sc in existing_subcontracts)

    # 社内作業者リスト
    internal_workers = []
    try:
        from subcontract_management.models import InternalWorker as IW
        internal_workers = IW.objects.all().order_by('name')
    except ImportError:
        pass

    # 業者管理パネル用にJSON形式でも渡す
    import json
    contractors_json = json.dumps([{
        'id': c.id,
        'name': c.name,
        'address': c.address or '',
        'phone': c.phone or '',
        'email': c.email or '',
        'contact_person': c.contact_person or '',
        'specialties': c.specialties or '',
        'is_active': c.is_active
    } for c in contractors])

    context = {
        'project': project,
        'contractors': contractors,
        'contractors_json': contractors_json,
        'staff_members': staff_members,
        'internal_workers': internal_workers,
        'existing_subcontracts': existing_subcontracts,
        'existing_total_cost': existing_total_cost,
    }
    return render(request, 'order_management/add_subcontract.html', context)


@login_required
def project_update(request, pk):
    """案件編集"""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = ProjectForm(request.POST, instance=project)
            if form.is_valid():
                project = form.save(commit=False)

                # 営業担当者（sales_manager）をproject_managerに保存
                sales_manager_id = request.POST.get('sales_manager')
                if sales_manager_id:
                    try:
                        from subcontract_management.models import InternalWorker
                        sales_worker = InternalWorker.objects.get(id=sales_manager_id)
                        project.project_manager = sales_worker.name
                    except InternalWorker.DoesNotExist:
                        pass

                # ============================================================================
                # SSOT Architecture: Dual-write pattern for gradual migration
                # - Write to both old fields (legacy) and ProjectProgressStep (new)
                # - Old fields will be deprecated in Phase 6
                # ============================================================================
                from order_management.services.progress_step_service import (
                    set_step_scheduled_date,
                    set_step_assignees
                )

                # 立ち会い（attendance）
                witness_date = request.POST.get('witness_date')
                if witness_date:
                    # Write to ProjectProgressStep (SSOT)
                    set_step_scheduled_date(project, 'attendance', witness_date)

                witness_assignees_str = request.POST.get('witness_assignees', '')
                if witness_assignees_str:
                    witness_assignees = [name.strip() for name in witness_assignees_str.split(',') if name.strip()]
                    # Write to ProjectProgressStep (SSOT)
                    set_step_assignees(project, 'attendance', witness_assignees)

                # 現地調査（survey）
                survey_date = request.POST.get('survey_date')
                if survey_date:
                    # Write to ProjectProgressStep (SSOT)
                    set_step_scheduled_date(project, 'survey', survey_date)

                survey_assignees_str = request.POST.get('survey_assignees', '')
                if survey_assignees_str:
                    survey_assignees = [name.strip() for name in survey_assignees_str.split(',') if name.strip()]
                    # Write to ProjectProgressStep (SSOT)
                    set_step_assignees(project, 'survey', survey_assignees)

                # 着工（construction_start）
                construction_assignees_str = request.POST.get('construction_assignees', '')
                if construction_assignees_str:
                    construction_assignees = [name.strip() for name in construction_assignees_str.split(',') if name.strip()]
                    # Write to ProjectProgressStep (SSOT)
                    set_step_assignees(project, 'construction_start', construction_assignees)

                project.save()

                # スケジュールステップデータの保存
                schedule_steps_json = request.POST.get('schedule_steps_data', '')
                if schedule_steps_json:
                    from order_management.services.progress_step_service import save_project_progress_steps
                    save_project_progress_steps(project, schedule_steps_json)

                return JsonResponse({
                    'success': True,
                    'message': f'案件「{project.site_name}」を更新しました。'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'フォームにエラーがあります。'
                }, status=400)

        # 通常のPOSTリクエストの場合（編集フォーム保存）
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)

            # 営業担当者（sales_manager）をproject_managerに保存
            sales_manager_id = request.POST.get('sales_manager')
            if sales_manager_id:
                try:
                    from subcontract_management.models import InternalWorker
                    sales_worker = InternalWorker.objects.get(id=sales_manager_id)
                    project.project_manager = sales_worker.name
                except InternalWorker.DoesNotExist:
                    pass

            # DEPRECATED: Detailed schedule management fields now handled by ProjectProgressStep (SSOT)
            # Legacy status fields kept for backward compatibility
            project.survey_status = request.POST.get('survey_status', 'not_required')
            project.estimate_status = request.POST.get('estimate_status', 'not_issued')

            project.save()

            # スケジュールステップデータの保存
            schedule_steps_json = request.POST.get('schedule_steps_data', '')
            if schedule_steps_json:
                from order_management.services.progress_step_service import save_project_progress_steps
                save_project_progress_steps(project, schedule_steps_json)

            messages.success(request, f'案件「{project.site_name}」を更新しました。')
            return redirect('order_management:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    # フォーム表示用のデータを準備
    from .models import ClientCompany
    from subcontract_management.models import InternalWorker
    client_companies = ClientCompany.objects.prefetch_related('contact_persons').filter(is_active=True).order_by('company_name')
    contractors = Contractor.objects.filter(is_active=True)  # 協力会社（作業者追加用）
    internal_workers = InternalWorker.objects.filter(is_active=True)

    # internal_workersをJSON形式でシリアライズ
    import json
    internal_workers_json = json.dumps([{
        'id': w.id,
        'name': w.name,
        'department': w.department,
        'hourly_rate': float(w.hourly_rate) if w.hourly_rate else 0,
        'specialties': w.specialties or '',
        'is_active': w.is_active
    } for w in internal_workers])

    # 支払いサイクルの日本語マッピング
    payment_cycle_labels = {
        'monthly': '月1回',
        'bimonthly': '月2回',
        'weekly': '週1回',
        'custom': 'その他'
    }

    # client_companiesをJSON形式でシリアライズ
    def get_primary_contact(company):
        """主担当者を取得するヘルパー関数"""
        primary = company.contact_persons.filter(is_primary=True).first()
        if not primary:
            primary = company.contact_persons.first()
        return primary

    client_companies_json = json.dumps([{
        'id': c.id,
        'company_name': c.company_name,
        'address': c.address or '',
        'phone': get_primary_contact(c).phone if get_primary_contact(c) else '',
        'contact_person': get_primary_contact(c).name if get_primary_contact(c) else '',
        'payment_cycle': c.payment_cycle or '',
        'payment_cycle_label': payment_cycle_labels.get(c.payment_cycle, c.payment_cycle) if c.payment_cycle else '',
        'closing_day': c.closing_day,
        'payment_offset_months': c.payment_offset_months,
        'payment_day': c.payment_day,
        'is_active': c.is_active
    } for c in client_companies])

    # スケジュールステップデータの読み込み
    from order_management.services.progress_step_service import load_project_progress_steps
    existing_schedule_steps = load_project_progress_steps(project)

    # プロジェクトに紐づくsubcontract（実施体制・業者情報）を取得
    try:
        from subcontract_management.models import Subcontract
        subcontracts = Subcontract.objects.filter(project=project).select_related('contractor')
    except:
        subcontracts = []

    # contractorsをJSON形式でシリアライズ
    contractors_json = json.dumps([{
        'id': c.id,
        'name': c.name,
        'contact_person': c.contact_person or '',
        'phone': c.phone or '',
        'email': c.email or '',
        'is_active': c.is_active,
        'closing_day': c.closing_day if c.closing_day is not None else '',
        'payment_offset_months': c.payment_offset_months if c.payment_offset_months is not None else '',
        'payment_day': c.payment_day if c.payment_day is not None else '',
        'payment_cycle': c.payment_cycle or '',
    } for c in contractors])

    # subcontractsをJSON形式でシリアライズ（processWorkers初期化用）
    subcontracts_json = json.dumps([{
        'id': s.id,
        'step': s.step,
        'contractor_id': s.contractor.id if s.contractor else None,
        'contractor_name': s.contractor.name if s.contractor else '',
        'contract_amount': float(s.contract_amount) if s.contract_amount else 0,
        'billed_amount': float(s.billed_amount) if s.billed_amount else 0,
        'payment_due_date': s.payment_due_date.isoformat() if s.payment_due_date else '',
        'payment_status': s.payment_status or 'pending',
        'work_description': s.work_description or '',
    } for s in subcontracts])

    return render(request, 'order_management/project_form.html', {
        'form': form,
        'title': '案件編集',
        'project': project,
        'client_companies': client_companies,  # 元請会社
        'client_companies_json': client_companies_json,
        'contractors': contractors,  # 協力会社（作業者追加で使用）
        'contractors_json': contractors_json,  # 協力会社（JSON形式）
        'internal_workers': internal_workers,
        'internal_workers_json': internal_workers_json,
        'existing_schedule_steps': existing_schedule_steps,  # 既存のスケジュールステップデータ
        'subcontracts': subcontracts,  # 既存の実施体制・業者データ
        'subcontracts_json': subcontracts_json,  # subcontracts（JSON形式）
    })


@login_required
def project_delete(request, pk):
    """案件削除"""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        site_name = project.site_name
        project.delete()
        messages.success(request, f'案件「{site_name}」を削除しました。')
        return redirect('order_management:project_list')

    return render(request, 'order_management/project_confirm_delete.html', {
        'project': project
    })


@login_required
def update_forecast(request, pk):
    """受注ヨミを更新（AJAX）"""
    if request.method == 'POST':
        from django.http import JsonResponse

        project = get_object_or_404(Project, pk=pk)
        new_status = request.POST.get('project_status')

        # 有効な選択肢かチェック
        valid_choices = [choice[0] for choice in Project.PROJECT_STATUS_CHOICES]
        if new_status not in valid_choices:
            return JsonResponse({'success': False, 'error': '無効な選択肢です'})

        project.project_status = new_status
        project.save()

        return JsonResponse({
            'success': True,
            'message': f'受注ヨミを「{new_status}」に更新しました'
        })

    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ許可されています'})


@login_required
def update_project_stage(request, pk):
    """
    プロジェクト進捗状況を更新（AJAX）

    SSOT Architecture:
    - Server-side calculation using calculate_current_stage()
    - Legacy: Also accepts client-side calculated stage/color for backward compatibility
    """
    if request.method == 'POST':
        from django.http import JsonResponse

        project = get_object_or_404(Project, pk=pk)

        # Option 1: Use server-side calculation (SSOT)
        # Always calculate stage from ProjectProgressStep
        calculated_stage = project.calculate_current_stage()

        # Option 2: Use client-sent values (Legacy compatibility)
        client_stage = request.POST.get('stage')
        client_color = request.POST.get('color')

        # Prefer server-side calculation, fall back to client values
        if calculated_stage:
            stage = calculated_stage['stage']
            color = calculated_stage['color']
        elif client_stage and client_color:
            # Legacy: Use client-provided values
            stage = client_stage
            color = client_color
        else:
            return JsonResponse({'success': False, 'error': 'stageとcolorが計算できませんでした'})

        project.current_stage = stage
        project.current_stage_color = color
        project.save(update_fields=['current_stage', 'current_stage_color'])

        return JsonResponse({
            'success': True,
            'message': f'進捗状況を「{stage}」に更新しました',
            'stage': stage,
            'color': color
        })

    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ許可されています'})


@csrf_exempt
@login_required
def project_api_list(request):
    """DataTables用API"""
    if request.method == 'GET':
        # パフォーマンス最適化：関連データを事前取得し、必要な列のみ選択（下書きを除外）
        projects = Project.objects.filter(is_draft=False).select_related().prefetch_related(
            'progress_steps',
            'progress_steps__template'
        ).only(
            'id', 'management_no', 'site_name', 'site_address', 'work_type',
            'project_status', 'client_name', 'project_manager',
            'order_amount', 'billing_amount', 'work_start_date', 'work_end_date',
            'created_at', 'updated_at'
        )

        # DataTables検索
        search_value = request.GET.get('search[value]', '')
        if search_value:
            projects = projects.filter(
                Q(management_no__icontains=search_value) |
                Q(site_name__icontains=search_value) |
                Q(client_name__icontains=search_value) |
                Q(project_manager__icontains=search_value)
            )

        # ソート
        order_column = request.GET.get('order[0][column]', '')
        order_dir = request.GET.get('order[0][dir]', 'asc')

        if order_column:
            columns = [
                'management_no', 'site_name', 'site_address', 'work_type',
                'project_status', 'client_name', 'project_manager',
                'order_amount', 'billing_amount', 'work_start_date'
            ]

            if int(order_column) < len(columns):
                order_field = columns[int(order_column)]
                if order_dir == 'desc':
                    order_field = f'-{order_field}'
                projects = projects.order_by(order_field)

        # ページング
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))

        total_count = projects.count()
        projects = projects[start:start + length]

        # データ整形
        data = []
        for project in projects:
            data.append({
                'id': project.pk,
                'management_no': project.management_no,
                'site_name': project.site_name,
                'site_address': project.site_address,
                'work_type': project.work_type,
                'project_status': project.project_status,
                'client_name': project.client_name,
                'project_manager': project.project_manager,
                'order_amount': str(project.order_amount),
                'billing_amount': str(project.billing_amount),
                'amount_difference': str(project.amount_difference),
                'work_start_date': project.work_start_date.strftime('%Y-%m-%d') if project.work_start_date else '',
                'work_end_date': project.work_end_date.strftime('%Y-%m-%d') if project.work_end_date else '',
                'invoice_issued': project.invoice_issued,
                'status_color': project.get_status_color_hex()
            })

        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': total_count,
            'recordsFiltered': total_count,
            'data': data
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
@login_required
def staff_api(request, staff_id=None):
    """担当者のCRUD操作用API"""
    if not InternalWorker:
        return JsonResponse({'error': 'InternalWorker model not available'}, status=400)

    if request.method == 'GET':
        # 社内担当者一覧取得
        workers = InternalWorker.objects.filter(is_active=True).order_by('name')
        worker_list = []
        for worker in workers:
            worker_list.append({
                'id': worker.id,
                'name': worker.name,
                'department': worker.department,
                'hourly_rate': float(worker.hourly_rate) if worker.hourly_rate else 0,
                'specialties': worker.specialties or '',
                'is_active': worker.is_active
            })
        return JsonResponse({'success': True, 'workers': worker_list})

    elif request.method == 'POST':
        # 新規作成
        data = json.loads(request.body)

        try:
            staff = InternalWorker.objects.create(
                employee_id=data.get('employee_id', f'EMP{InternalWorker.objects.count() + 1:03d}'),
                name=data['name'],
                department=data.get('department', ''),
                phone=data.get('phone', ''),
                hourly_rate=data.get('hourly_rate', 0),
                specialties=data.get('specialties', ''),
                is_active=data.get('active', True)
            )

            return JsonResponse({
                'success': True,
                'staff': {
                    'id': str(staff.id),
                    'name': staff.name,
                    'department': staff.get_department_display(),
                    'phone': staff.phone,
                    'hourly_rate': staff.hourly_rate,
                    'specialties': staff.specialties,
                    'active': staff.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'PUT' and staff_id:
        # 更新
        try:
            staff = get_object_or_404(InternalWorker, id=staff_id)
            data = json.loads(request.body)

            staff.name = data['name']
            staff.department = data.get('department', '')
            staff.phone = data.get('phone', '')
            staff.hourly_rate = data.get('hourly_rate', 0)
            staff.specialties = data.get('specialties', '')
            staff.is_active = data.get('active', True)
            staff.save()

            return JsonResponse({
                'success': True,
                'staff': {
                    'id': str(staff.id),
                    'name': staff.name,
                    'department': staff.get_department_display(),
                    'phone': staff.phone,
                    'hourly_rate': staff.hourly_rate,
                    'specialties': staff.specialties,
                    'active': staff.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'DELETE' and staff_id:
        # 削除
        try:
            staff = get_object_or_404(InternalWorker, id=staff_id)
            staff.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
@login_required
def contractor_api(request, contractor_id=None):
    """業者のCRUD操作用API"""

    if request.method == 'GET':
        # 業者一覧取得
        contractors = Contractor.objects.filter(is_active=True).order_by('-is_ordering', 'name')
        contractor_list = []
        for contractor in contractors:
            contractor_list.append({
                'id': contractor.id,
                'name': contractor.name,
                'address': contractor.address,
                'phone': contractor.phone,
                'email': contractor.email,
                'contact_person': contractor.contact_person,
                'specialties': contractor.specialties,
                'classification': contractor.get_classification_display(),
                'is_ordering': contractor.is_ordering,
                'is_receiving': contractor.is_receiving,
                'is_supplier': contractor.is_supplier,
                'is_other': contractor.is_other,
                'other_description': contractor.other_description,
                'is_active': contractor.is_active
            })
        return JsonResponse({'contractors': contractor_list})

    elif request.method == 'POST':
        # 新規作成
        data = json.loads(request.body)

        try:
            contractor = Contractor.objects.create(
                name=data['name'],
                address=data.get('address', ''),
                phone=data.get('phone', ''),
                email=data.get('email', ''),
                contact_person=data.get('contact_person', ''),
                specialties=data.get('specialties', ''),
                is_ordering=data.get('is_ordering', False),
                is_receiving=data.get('is_receiving', False),
                is_supplier=data.get('is_supplier', False),
                is_other=data.get('is_other', False),
                other_description=data.get('other_description', ''),
                is_active=data.get('is_active', True)
            )

            return JsonResponse({
                'success': True,
                'contractor': {
                    'id': contractor.id,
                    'name': contractor.name,
                    'address': contractor.address,
                    'phone': contractor.phone,
                    'email': contractor.email,
                    'contact_person': contractor.contact_person,
                    'specialties': contractor.specialties,
                    'classification': contractor.get_classification_display(),
                    'is_ordering': contractor.is_ordering,
                    'is_receiving': contractor.is_receiving,
                    'is_supplier': contractor.is_supplier,
                    'is_other': contractor.is_other,
                    'other_description': contractor.other_description,
                    'is_active': contractor.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'PUT' and contractor_id:
        # 更新
        try:
            contractor = get_object_or_404(Contractor, id=contractor_id)
            data = json.loads(request.body)

            contractor.name = data.get('name', contractor.name)
            contractor.address = data.get('address', contractor.address)
            contractor.phone = data.get('phone', contractor.phone)
            contractor.email = data.get('email', contractor.email)
            contractor.contact_person = data.get('contact_person', contractor.contact_person)
            contractor.specialties = data.get('specialties', contractor.specialties)
            contractor.is_ordering = data.get('is_ordering', contractor.is_ordering)
            contractor.is_receiving = data.get('is_receiving', contractor.is_receiving)
            contractor.is_supplier = data.get('is_supplier', contractor.is_supplier)
            contractor.is_other = data.get('is_other', contractor.is_other)
            contractor.other_description = data.get('other_description', contractor.other_description)
            contractor.is_active = data.get('is_active', contractor.is_active)
            contractor.save()

            return JsonResponse({
                'success': True,
                'contractor': {
                    'id': contractor.id,
                    'name': contractor.name,
                    'address': contractor.address,
                    'phone': contractor.phone,
                    'email': contractor.email,
                    'contact_person': contractor.contact_person,
                    'specialties': contractor.specialties,
                    'classification': contractor.get_classification_display(),
                    'is_ordering': contractor.is_ordering,
                    'is_receiving': contractor.is_receiving,
                    'is_supplier': contractor.is_supplier,
                    'is_other': contractor.is_other,
                    'other_description': contractor.other_description,
                    'is_active': contractor.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    elif request.method == 'DELETE' and contractor_id:
        # 削除
        try:
            contractor = get_object_or_404(Contractor, id=contractor_id)
            contractor.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def ordering_dashboard(request):
    """発注ダッシュボード"""
    projects = Project.objects.filter(is_draft=False, project_status='完工').order_by('-created_at')

    # ページネーション
    paginator = Paginator(projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'projects': page_obj,
        'page_obj': page_obj,
    }

    return render(request, 'order_management/ordering_dashboard.html', context)


@login_required
def receipt_dashboard(request):
    """受注ダッシュボード"""
    projects = Project.objects.filter(is_draft=False, project_status='完工').order_by('-created_at')

    # ページネーション
    paginator = Paginator(projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'projects': page_obj,
        'page_obj': page_obj,
    }

    return render(request, 'order_management/receipt_dashboard.html', context)


@csrf_exempt
@login_required
def generate_client_invoice_api(request):
    """得意先向け請求書生成API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')

            if not project_id:
                return JsonResponse({'success': False, 'error': 'Project ID is required'}, status=400)

            project = get_object_or_404(Project, pk=project_id)

            # 請求書番号を生成
            today = timezone.now()
            year_month = today.strftime('%Y%m')
            invoice_number = f"INV-{year_month}-{Invoice.objects.filter(invoice_number__startswith=f'INV-{year_month}').count() + 1:03d}"

            # 税抜金額から税込金額を計算
            subtotal = project.billing_amount or Decimal('0')
            tax_rate = Decimal('10.00')
            tax_amount = (subtotal * tax_rate / Decimal('100')).quantize(Decimal('1'))
            total_amount = subtotal + tax_amount

            # 請求書を作成
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                client_name=project.client_name,
                client_address=project.client_address,
                issue_date=today.date(),
                due_date=today.date() + timedelta(days=30),
                billing_period_start=project.work_start_date or today.date(),
                billing_period_end=project.work_end_date or today.date(),
                subtotal=subtotal,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                total_amount=total_amount,
                status='draft',
                created_by=request.user.username if request.user.is_authenticated else 'system'
            )

            # 請求書明細を作成
            InvoiceItem.objects.create(
                invoice=invoice,
                project=project,
                description=f"{project.work_type} - {project.site_name}",
                work_period_start=project.work_start_date,
                work_period_end=project.work_end_date,
                quantity=Decimal('1.00'),
                unit='式',
                unit_price=subtotal,
                amount=subtotal,
                order=1
            )

            return JsonResponse({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total_amount': str(total_amount),
                'message': f'請求書 {invoice_number} を生成しました'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
@login_required
def get_client_invoice_preview_api(request):
    """クライアント向け複数プロジェクト請求書プレビューAPI"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            client_name = data.get('client_name')
            project_ids = data.get('project_ids', [])

            # 年月の指定があれば、その月の入金予定日でフィルター
            year = data.get('year')
            month = data.get('month')

            if not client_name or not project_ids:
                return JsonResponse({'error': 'クライアント名またはプロジェクトIDが指定されていません'}, status=400)

            # 指定されたプロジェクトを取得（下書きを除外）
            projects = Project.objects.filter(is_draft=False, id__in=project_ids, client_name=client_name)

            # 年月が指定されている場合は、入金予定日でフィルター
            if year and month:
                import calendar
                from datetime import datetime
                start_date = datetime(int(year), int(month), 1).date()
                end_date = datetime(int(year), int(month), calendar.monthrange(int(year), int(month))[1]).date()
                projects = projects.filter(
                    payment_due_date__gte=start_date,
                    payment_due_date__lte=end_date
                )

            if not projects.exists():
                return JsonResponse({'error': '指定されたプロジェクトが見つかりません'}, status=404)

            # 合計金額を計算
            total_subtotal = sum((p.order_amount or Decimal('0')) for p in projects)
            tax_rate = Decimal('10.00')
            tax_amount = (total_subtotal * tax_rate / Decimal('100')).quantize(Decimal('1'))
            total_amount = total_subtotal + tax_amount

            # 請求書番号を生成
            today = timezone.now()
            year_month = today.strftime('%Y%m')
            preview_invoice_number = f"INV-{year_month}-{Invoice.objects.filter(invoice_number__startswith=f'INV-{year_month}').count() + 1:03d}"

            # 項目リストを作成
            items = []
            for project in projects:
                project_amount = project.order_amount or Decimal('0')
                items.append({
                    'description': f"{project.work_type} - {project.site_name}",
                    'quantity': 1.0,
                    'unit': '式',
                    'unit_price': float(project_amount),
                    'amount': float(project_amount),
                    'work_period': f"{project.work_start_date.strftime('%Y/%m/%d') if project.work_start_date else '未定'} ～ {project.work_end_date.strftime('%Y/%m/%d') if project.work_end_date else '未定'}"
                })

            preview_data = {
                'invoice_number': preview_invoice_number,
                'issue_date': today.strftime('%Y年%m月%d日'),
                'due_date': (today + timedelta(days=30)).strftime('%Y年%m月%d日'),
                'client_name': client_name,
                'billing_period': f"{today.strftime('%Y年%m月分')}",
                'items': items,
                'subtotal': f"{total_subtotal:,}",
                'tax_amount': f"{tax_amount:,}",
                'total_amount': f"{total_amount:,}",
                'project_count': len(projects)
            }

            return JsonResponse({
                'success': True,
                'preview_data': preview_data
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
@login_required
def generate_invoices_by_client_api(request):
    """入金予定日ベースで当月の請求書を受注先別に生成するAPI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            year = int(data.get('year', timezone.now().year))
            month = int(data.get('month', timezone.now().month))

            # 月の開始日と終了日
            import calendar
            from datetime import datetime
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()

            # 入金予定日が当月のプロジェクトのみ取得（下書きを除外）
            projects = Project.objects.filter(
                is_draft=False,
                payment_due_date__gte=start_date,
                payment_due_date__lte=end_date,
                order_amount__gt=0
            ).exclude(
                client_name__isnull=True
            ).exclude(
                client_name=''
            )

            # 受注先別にグループ化
            client_projects = {}
            for project in projects:
                client_name = project.client_name
                if client_name not in client_projects:
                    client_projects[client_name] = []
                client_projects[client_name].append(project)

            # 請求書を生成
            invoices_created = []
            for client_name, client_project_list in client_projects.items():
                # 合計金額を計算
                subtotal = sum((p.billing_amount or p.order_amount or Decimal('0')) for p in client_project_list)
                tax_rate = Decimal('10.00')
                tax_amount = (subtotal * tax_rate / Decimal('100')).quantize(Decimal('1'))
                total_amount = subtotal + tax_amount

                # 請求書番号を生成
                today = timezone.now()
                year_month = today.strftime('%Y%m')
                invoice_count = Invoice.objects.filter(invoice_number__startswith=f'INV-{year_month}').count()
                invoice_number = f"INV-{year_month}-{invoice_count + 1:03d}"

                # 請求書を作成
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    client_name=client_name,
                    client_address=client_project_list[0].site_address if client_project_list else '',
                    issue_date=today.date(),
                    due_date=today.date() + timedelta(days=30),
                    billing_period_start=start_date,
                    billing_period_end=end_date,
                    subtotal=subtotal,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    status='draft',
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )

                # 請求書明細を作成（当月の入金予定案件のみ）
                for idx, project in enumerate(client_project_list, 1):
                    project_amount = project.billing_amount or project.order_amount or Decimal('0')
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        project=project,
                        description=f"{project.work_type} - {project.site_name}",
                        work_period_start=project.work_start_date,
                        work_period_end=project.work_end_date,
                        quantity=Decimal('1.00'),
                        unit='式',
                        unit_price=project_amount,
                        amount=project_amount,
                        order=idx
                    )

                invoices_created.append({
                    'client_name': client_name,
                    'invoice_number': invoice_number,
                    'amount': float(total_amount)
                })

            return JsonResponse({
                'success': True,
                'invoice_count': len(invoices_created),
                'invoices': invoices_created,
                'message': f'{len(invoices_created)}件の請求書を生成しました'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
@login_required
def get_invoice_preview_api(request, project_id):
    """請求書プレビューデータ取得API"""
    if request.method == 'GET':
        try:
            project = get_object_or_404(Project, pk=project_id)

            # 税抜金額から税込金額を計算
            subtotal = project.billing_amount or Decimal('0')
            tax_rate = Decimal('10.00')
            tax_amount = (subtotal * tax_rate / Decimal('100')).quantize(Decimal('1'))
            total_amount = subtotal + tax_amount

            # 請求書プレビューデータを生成
            today = timezone.now()
            year_month = today.strftime('%Y%m')
            preview_invoice_number = f"INV-{year_month}-{Invoice.objects.filter(invoice_number__startswith=f'INV-{year_month}').count() + 1:03d}"

            preview_data = {
                'invoice_number': preview_invoice_number,
                'issue_date': today.strftime('%Y年%m月%d日'),
                'client_name': project.client_name,
                'client_address': project.client_address,
                'billing_period': f"{project.work_start_date.strftime('%Y年%m月%d日') if project.work_start_date else '未定'} ～ {project.work_end_date.strftime('%Y年%m月%d日') if project.work_end_date else '未定'}",
                'items': [
                    {
                        'description': f"{project.work_type} - {project.site_name}",
                        'quantity': '1.00',
                        'unit': '式',
                        'unit_price': f"{subtotal:,}",
                        'amount': f"{subtotal:,}"
                    }
                ],
                'subtotal': f"{subtotal:,}",
                'tax_rate': '10%',
                'tax_amount': f"{tax_amount:,}",
                'total_amount': f"{total_amount:,}",
                'due_date': (today.date() + timedelta(days=30)).strftime('%Y年%m月%d日')
            }

            return JsonResponse({
                'success': True,
                'preview_data': preview_data
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def project_comments(request, pk):
    """
    プロジェクトの詳細コメントを取得・追加するAPIエンドポイント
    """
    try:
        project = get_object_or_404(Project, pk=pk)
    except Exception:
        return JsonResponse({'error': 'Project not found'}, status=404)

    if request.method == 'GET':
        # コメント一覧を取得
        comments = project.detailed_comments if project.detailed_comments else []
        return JsonResponse({'success': True, 'comments': comments})

    elif request.method == 'POST':
        # 新しいコメントを追加
        try:
            import json
            from datetime import datetime

            data = json.loads(request.body)
            comment_text = data.get('comment', '').strip()

            if not comment_text:
                return JsonResponse({'success': False, 'error': 'コメントが空です'}, status=400)

            # 現在のユーザー名を取得
            user_name = request.user.get_full_name() or request.user.username

            # 新しいコメントオブジェクト
            new_comment = {
                'comment': comment_text,
                'user': user_name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # コメントリストを取得（なければ空リスト）
            comments = project.detailed_comments if project.detailed_comments else []

            # 新しいコメントを追加（最新が最後）
            comments.append(new_comment)

            # プロジェクトに保存
            project.detailed_comments = comments
            project.save()

            return JsonResponse({'success': True, 'comment': new_comment})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
@require_POST
def update_project_field(request, pk):
    """案件詳細フィールドのインライン編集"""
    import json
    from decimal import Decimal
    from datetime import datetime

    project = get_object_or_404(Project, pk=pk)

    try:
        data = json.loads(request.body)
        field_name = data.get('field')
        field_value = data.get('value')

        # 許可されたフィールドのみ更新
        allowed_fields = {
            'management_no', 'site_name', 'work_type', 'site_address',
            'order_amount', 'billing_amount', 'parking_fee',
            'estimate_issued_date', 'contract_date',
            'work_start_date', 'work_end_date', 'payment_due_date',
            'client_name', 'client_address', 'client_company', 'project_manager',
            'expense_item_1', 'expense_amount_1', 'expense_item_2', 'expense_amount_2',
            'notes'
        }

        if field_name not in allowed_fields:
            return JsonResponse({'success': False, 'error': '更新が許可されていないフィールドです'}, status=403)

        # フィールドのタイプに応じて変換
        if field_name == 'client_company':
            # 元請会社のForeignKey更新
            if field_value and str(field_value).strip() and str(field_value).strip().lower() != 'none':
                try:
                    client_company_id = int(field_value)
                    client_company = ClientCompany.objects.get(id=client_company_id)
                    project.client_company = client_company
                    # 元請名・住所も自動同期
                    project.client_name = client_company.company_name
                    project.client_address = client_company.address
                except (ValueError, ClientCompany.DoesNotExist):
                    return JsonResponse({'success': False, 'error': '元請会社が見つかりません'}, status=400)
            else:
                project.client_company = None
                project.client_name = ''
                project.client_address = ''
            project.save()
        elif field_name in ['order_amount', 'billing_amount', 'parking_fee', 'expense_amount_1', 'expense_amount_2']:
            # 数値フィールド
            if field_value and str(field_value).strip() and str(field_value).strip().lower() != 'none':
                try:
                    field_value = Decimal(str(field_value).strip())
                except (ValueError, TypeError):
                    field_value = 0
            else:
                field_value = 0
            # フィールドを更新
            setattr(project, field_name, field_value)
            project.save()
        elif field_name in ['estimate_issued_date', 'contract_date', 'work_start_date', 'work_end_date', 'payment_due_date']:
            # 日付フィールド
            if field_value and str(field_value).strip() and str(field_value).strip().lower() != 'none':
                field_value = datetime.strptime(field_value, '%Y-%m-%d').date()
            else:
                field_value = None
            # フィールドを更新
            setattr(project, field_name, field_value)
            project.save()
        else:
            # その他のテキストフィールド
            setattr(project, field_name, field_value)
            project.save()

        return JsonResponse({'success': True, 'message': f'{field_name}を更新しました'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'値の形式が正しくありません: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def mark_comments_read(request, project_id):
    """プロジェクトのコメントを既読にする"""
    try:
        project = get_object_or_404(Project, pk=project_id)

        # CommentReadStatusを作成または更新
        read_status, created = CommentReadStatus.objects.update_or_create(
            project=project,
            user=request.user,
            defaults={'last_read_at': timezone.now()}
        )

        return JsonResponse({
            'success': True,
            'message': 'コメントを既読にしました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
