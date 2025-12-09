from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from decimal import Decimal

from .models import Project, FixedCost, VariableCost, ClientCompany
from subcontract_management.models import Subcontract, Contractor, InternalWorker
# ARCHIVED: 旧キャッシュフロー機能（アーカイブ済み）
# from .cashflow_utils import get_monthly_comparison, get_receivables_summary, get_payables_summary
from .utils import safe_int
from .notification_utils import check_and_create_overdue_notifications


class UltimateDashboardView(TemplateView):
    """統合型究極ダッシュボード - プロジェクト管理と会計を統合"""
    template_name = 'order_management/ultimate_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 完工遅延通知を自動チェック・生成
        try:
            created, updated, deleted = check_and_create_overdue_notifications()
            if created > 0 or updated > 0 or deleted > 0:
                print(f"完工遅延通知: 新規作成={created}, 更新={updated}, 削除={deleted}")
        except Exception as e:
            print(f"完工遅延通知の自動生成でエラーが発生しました: {e}")

        # 現在の日時と会計情報
        now = timezone.now()
        today = now.date()
        year = safe_int(self.request.GET.get('year', now.year))
        month = safe_int(self.request.GET.get('month', now.month))
        view_type = self.request.GET.get('view', 'financial')  # financial, operational

        # 月の開始日と終了日
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()

        # ====================
        # プロジェクト管理統計
        # ====================

        # プロジェクト基本統計
        total_projects = Project.objects.count()
        # アクティブな案件：受注確定でNGでないもの
        active_projects = Project.objects.filter(
            project_status='受注確定'
        ).exclude(
            project_status='NG'
        ).count()

        # 受注ヨミ別統計
        status_stats = Project.objects.values('project_status').annotate(
            count=Count('id'),
            total_amount=Sum('order_amount')
        ).order_by('project_status')

        # ステータス別カウント
        status_counts = {
            '完工': Project.objects.filter(project_status='完工').count(),
            '進行中': Project.objects.filter(project_status='進行中').count(),
            '施工日待ち': Project.objects.filter(project_status='施工日待ち').count(),
            'ネタ': Project.objects.filter(project_status='ネタ').count(),
            'NG': Project.objects.filter(project_status='NG').count(),
        }

        # 今月の案件統計
        this_month_projects = Project.objects.filter(
            created_at__year=year,
            created_at__month=month
        )
        new_projects_this_month = this_month_projects.count()
        new_orders_this_month = this_month_projects.filter(project_status='完工').count()

        # Phase 8: 優先度フィルタリング
        priority_filter = self.request.GET.get('priority')
        approval_filter = self.request.GET.get('approval_status')

        # 進行中案件（工事中）- Phase 8: 優先度順にソート
        # 受注確定の案件を進行中とみなす
        ongoing_query = Project.objects.filter(
            project_status='受注確定'
        )

        if priority_filter == 'high':
            ongoing_query = ongoing_query.filter(priority_score__gte=50)
        elif priority_filter == 'medium':
            ongoing_query = ongoing_query.filter(priority_score__gte=20, priority_score__lt=50)
        elif priority_filter == 'low':
            ongoing_query = ongoing_query.filter(priority_score__lt=20)

        if approval_filter:
            ongoing_query = ongoing_query.filter(approval_status=approval_filter)

        ongoing_projects = ongoing_query.order_by('-priority_score', '-created_at')[:10]

        # 近日開始予定案件 - Phase 8: 優先度順にソート
        # 受注確度が高い案件（A, B）を開始予定とみなす
        upcoming_query = Project.objects.filter(
            project_status__in=['A', 'B']
        )

        if priority_filter == 'high':
            upcoming_query = upcoming_query.filter(priority_score__gte=50)
        elif priority_filter == 'medium':
            upcoming_query = upcoming_query.filter(priority_score__gte=20, priority_score__lt=50)
        elif priority_filter == 'low':
            upcoming_query = upcoming_query.filter(priority_score__lt=20)

        if approval_filter:
            upcoming_query = upcoming_query.filter(approval_status=approval_filter)

        upcoming_projects = upcoming_query.order_by('-priority_score', '-created_at')[:10]

        # Phase 8: 高優先度案件（priority_score >= 70）
        high_priority_projects = Project.objects.filter(
            priority_score__gte=70
        ).exclude(
            project_status='完工'
        ).order_by('-priority_score')[:5]

        # Phase 8: 承認待ち案件
        pending_approval_projects = Project.objects.filter(
            approval_status='pending'
        ).order_by('-order_amount')[:5]

        # 月別推移データ（過去6ヶ月）
        monthly_trends = []
        for i in range(6):
            target_date = today.replace(day=1) - timedelta(days=i*30)
            month_start = target_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            month_projects = Project.objects.filter(
                created_at__date__range=[month_start, month_end]
            )

            monthly_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': calendar.month_name[month_start.month],
                'total': month_projects.count(),
                'received': month_projects.filter(project_status='完工').count(),
                'amount': month_projects.aggregate(Sum('order_amount'))['order_amount__sum'] or 0
            })

        monthly_trends.reverse()

        # プロジェクト完了率
        # current_stageが完工になっている案件を完了とみなす
        completed_projects = Project.objects.filter(
            current_stage='完工',
            created_at__year=year
        ).count()

        completion_rate = 0
        if total_projects > 0:
            completion_rate = (completed_projects / total_projects) * 100

        # ====================
        # 財務・会計統計（Accounting Dashboard から）
        # ====================

        # 入金データ（入金ベース） - 元請業者ベース
        receipt_projects = Project.objects.filter(
            Q(payment_due_date__range=[start_date, end_date]) |
            Q(project_status='完工', billing_amount__gt=0)
        ).exclude(client_company__isnull=True).select_related('client_company')

        receipt_total = 0
        receipt_received = 0
        receipt_pending = 0

        for project in receipt_projects:
            amount = project.billing_amount or project.order_amount or 0
            receipt_total += amount
            # 入金済みかどうかは payment_received_date で判定
            if project.payment_received_date:
                receipt_received += amount
            else:
                receipt_pending += amount

        # 出金データ（出金ベース）
        payment_subcontracts = Subcontract.objects.filter(
            Q(payment_date__range=[start_date, end_date]) |
            Q(billed_amount__gt=0)
        ).select_related('project', 'contractor', 'internal_worker')

        payment_total = 0
        payment_paid = 0
        payment_pending = 0

        for subcontract in payment_subcontracts:
            amount = subcontract.billed_amount or subcontract.contract_amount or 0
            payment_total += amount
            if subcontract.payment_status == 'paid':
                payment_paid += amount
            else:
                payment_pending += amount

        # キャッシュフロー計算
        net_cashflow = receipt_received - payment_paid
        projected_cashflow = receipt_total - payment_total

        # 通帳スタイルのトランザクション
        transactions = []

        # 入金トランザクション - 元請業者ベース
        for project in receipt_projects:
            amount = project.billing_amount or project.order_amount or 0
            if amount > 0:
                client_company_name = project.client_company.company_name if project.client_company else '不明な元請'
                transactions.append({
                    'date': project.payment_due_date or project.contract_date or start_date,
                    'description': f'入金: {project.site_name}',
                    'client': client_company_name,
                    'type': 'receipt',
                    'amount': amount,
                    'status': 'completed' if project.payment_received_date else 'pending',
                    'project': project,
                    'client_company': project.client_company  # 元請業者オブジェクトも追加
                })

        # 出金トランザクション
        for subcontract in payment_subcontracts:
            amount = subcontract.billed_amount or subcontract.contract_amount or 0
            if amount > 0:
                payee = subcontract.contractor.name if subcontract.contractor else subcontract.internal_worker.name
                transactions.append({
                    'date': subcontract.payment_date or start_date,
                    'description': f'出金: {subcontract.site_name}',
                    'client': payee,
                    'type': 'payment',
                    'amount': amount,
                    'status': subcontract.payment_status,
                    'project': subcontract.project
                })

        # 日付順でソート
        transactions.sort(key=lambda x: x['date'])

        # 残高計算
        balance = 0
        for transaction in transactions:
            if transaction['type'] == 'receipt':
                if transaction['status'] == 'completed':
                    balance += transaction['amount']
            else:
                if transaction['status'] == 'paid':
                    balance -= transaction['amount']
            transaction['balance'] = balance

        # 年間業績データ取得
        annual_performance = self.get_annual_performance(year)

        # 連続黒字月数を取得
        consecutive_profit_months = annual_performance.get('consecutive_profit_months', 0)

        # ====================
        # 統合分析データ（新規） - 元請業者ベース
        # ====================

        # 元請業者別の収益性分析
        client_company_performance = {}

        # 完工済みプロジェクトを元請業者でグループ化
        completed_projects = Project.objects.filter(
            project_status='完工',
            client_company__isnull=False
        ).select_related('client_company')

        for project in completed_projects:
            client_company = project.client_company
            company_id = client_company.id

            if company_id not in client_company_performance:
                client_company_performance[company_id] = {
                    'client_company': client_company,
                    'company_name': client_company.company_name,
                    'project_count': 0,
                    'total_revenue': Decimal('0'),
                    'total_costs': Decimal('0'),
                    'total_profit': Decimal('0'),
                    'avg_margin': Decimal('0'),
                    'projects': []
                }

            # プロジェクトの売上と原価を計算
            revenue = project.billing_amount or project.order_amount or Decimal('0')
            costs = Subcontract.objects.filter(project=project).aggregate(
                total=Sum('billed_amount')
            )['total'] or Decimal('0')
            profit = revenue - costs

            # 元請業者の実績に加算
            client_company_performance[company_id]['project_count'] += 1
            client_company_performance[company_id]['total_revenue'] += revenue
            client_company_performance[company_id]['total_costs'] += costs
            client_company_performance[company_id]['total_profit'] += profit
            client_company_performance[company_id]['projects'].append({
                'project': project,
                'revenue': revenue,
                'costs': costs,
                'profit': profit
            })

        # 各元請業者の平均利益率を計算
        for company_id, performance in client_company_performance.items():
            if performance['total_revenue'] > 0:
                performance['avg_margin'] = (performance['total_profit'] / performance['total_revenue']) * 100
            else:
                performance['avg_margin'] = Decimal('0')

        # 利益率でソート（降順）
        profitable_clients = sorted(
            client_company_performance.values(),
            key=lambda x: x['avg_margin'],
            reverse=True
        )

        # プロジェクト収益性分析（従来通り、参考用として残す）
        profitable_projects = []
        for project in Project.objects.filter(project_status='完工').select_related('client_company')[:10]:
            revenue = project.billing_amount or project.order_amount or 0
            costs = Subcontract.objects.filter(project=project).aggregate(
                total=Sum('billed_amount')
            )['total'] or 0

            if revenue > 0:
                profit_margin = ((revenue - costs) / revenue) * 100
                profitable_projects.append({
                    'project': project,
                    'revenue': revenue,
                    'costs': costs,
                    'profit': revenue - costs,
                    'margin': profit_margin
                })

        # 収益性でソート
        profitable_projects.sort(key=lambda x: x['margin'], reverse=True)

        # パイプライン価値（受注見込み案件の総額）
        pipeline_value = Project.objects.filter(
            project_status__in=['施工日待ち', 'ネタ']
        ).aggregate(total=Sum('order_amount'))['total'] or 0

        # コスト管理統計
        fixed_costs_monthly = FixedCost.objects.filter(is_active=True).aggregate(
            total=Sum('monthly_amount')
        )['total'] or 0

        variable_costs_monthly = VariableCost.objects.filter(
            incurred_date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_monthly_costs = fixed_costs_monthly + variable_costs_monthly

        # ====================
        # キャッシュフロー管理統計（Phase 1）- ARCHIVED
        # ====================

        # ARCHIVED: 旧キャッシュフロー機能（アーカイブ済み）
        # 月次キャッシュフロー比較（発生 vs 現金）
        # cashflow_comparison = get_monthly_comparison(year, month)

        # 売掛金・買掛金サマリー
        # receivables = get_receivables_summary()
        # payables = get_payables_summary()

        # デフォルト値を設定（新機能実装まで）
        cashflow_comparison = {}
        receivables = {'total_receivable': 0, 'count': 0}
        payables = {'total_payable': 0, 'count': 0}

        # ====================
        # コンテキストデータ統合
        # ====================

        context.update({
            # 基本情報
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'today': today,
            'view_type': view_type,
            'start_date': start_date,
            'end_date': end_date,

            # プロジェクト管理データ
            'total_projects': total_projects,
            'active_projects': active_projects,
            'new_projects_this_month': new_projects_this_month,
            'new_orders_this_month': new_orders_this_month,
            'completion_rate': completion_rate,
            'status_stats': status_stats,
            'status_counts': status_counts,
            'ongoing_projects': ongoing_projects,
            'upcoming_projects': upcoming_projects,
            'monthly_trends': monthly_trends,

            # Phase 8: 優先度管理
            'high_priority_projects': high_priority_projects,
            'pending_approval_projects': pending_approval_projects,
            'priority_filter': priority_filter or '',
            'approval_filter': approval_filter or '',

            # 財務データ
            'receipt_total': receipt_total,
            'receipt_received': receipt_received,
            'receipt_pending': receipt_pending,
            'payment_total': payment_total,
            'payment_paid': payment_paid,
            'payment_pending': payment_pending,
            'net_cashflow': net_cashflow,
            'projected_cashflow': projected_cashflow,
            'transactions': transactions[:20],  # 最新20件
            'annual_performance': annual_performance,

            # 統合分析データ - 元請業者ベース
            'profitable_clients': profitable_clients[:10],  # Top 10元請業者
            'client_company_performance': client_company_performance,  # 全元請業者の実績
            'profitable_projects': profitable_projects[:5],  # Top 5プロジェクト（参考用）
            'pipeline_value': pipeline_value,
            'fixed_costs_monthly': fixed_costs_monthly,
            'variable_costs_monthly': variable_costs_monthly,
            'total_monthly_costs': total_monthly_costs,
            'consecutive_profit_months': consecutive_profit_months,

            # キャッシュフロー管理データ（Phase 1）
            'cashflow_comparison': cashflow_comparison,
            'receivables_total': receivables['total_receivable'],
            'receivables_count': receivables['count'],
            'payables_total': payables['total_payable'],
            'payables_count': payables['count'],

            # ビュータイプ選択肢
            'view_type_choices': [
                ('financial', '財務詳細ビュー'),
                ('operational', '運用詳細ビュー'),
            ],
        })

        return context

    def get_annual_performance(self, year):
        """年間業績データを計算（AccountingDashboardViewから移植）"""
        # 会計年度: 4月-3月
        fiscal_year_start = datetime(year, 4, 1).date()
        fiscal_year_end = datetime(year + 1, 3, 31).date()
        current_date = timezone.now().date()
        current_month = current_date.month
        current_year = current_date.year

        # 月次データを初期化
        monthly_data = {}
        for i in range(12):
            month_offset = i + 4
            if month_offset > 12:
                target_year = year + 1
                target_month = month_offset - 12
            else:
                target_year = year
                target_month = month_offset

            monthly_data[i] = {
                'year': target_year,
                'month': target_month,
                'month_name': calendar.month_name[target_month],
                'revenue': Decimal('0'),
                'cost_of_sales': Decimal('0'),
                'cost_labor': Decimal('0'),
                'cost_materials': Decimal('0'),
                'gross_profit': Decimal('0'),
                'sales_expense': Decimal('0'),
                'fixed_costs': Decimal('0'),
                'operating_profit': Decimal('0'),
                'is_actual': False,
                'is_current': False,
                # 新規追加: プロジェクト統計
                'new_projects': 0,
                'completed_projects': 0,
            }

        # 実績データとフラグの設定
        for i, data in monthly_data.items():
            target_date = datetime(data['year'], data['month'], 1).date()
            if target_date <= current_date:
                data['is_actual'] = True
            if data['year'] == current_year and data['month'] == current_month:
                data['is_current'] = True

            # プロジェクト統計追加
            month_projects = Project.objects.filter(
                created_at__year=data['year'],
                created_at__month=data['month']
            )
            data['new_projects'] = month_projects.count()
            data['completed_projects'] = month_projects.filter(current_stage='完工').count()

        # 売上高・売上原価の計算
        revenue_projects = Project.objects.filter(
            project_status='完工',
            billing_amount__gt=0
        )

        for project in revenue_projects:
            # 売上計上日（入金予定日ベースに変更）
            revenue_date = project.payment_due_date
            if not revenue_date or not (fiscal_year_start <= revenue_date <= fiscal_year_end):
                continue

            month_index = self.get_fiscal_month_index(revenue_date, year)
            if month_index is not None:
                revenue = project.billing_amount or Decimal('0')
                monthly_data[month_index]['revenue'] += revenue

                subcontracts = Subcontract.objects.filter(project=project)
                for subcontract in subcontracts:
                    cost = subcontract.billed_amount or subcontract.contract_amount or Decimal('0')
                    monthly_data[month_index]['cost_of_sales'] += cost

                    if subcontract.worker_type == 'external':
                        monthly_data[month_index]['cost_labor'] += cost

        # 販管費の計算
        variable_costs = VariableCost.objects.filter(
            incurred_date__range=[fiscal_year_start, fiscal_year_end]
        )

        for cost in variable_costs:
            month_index = self.get_fiscal_month_index(cost.incurred_date, year)
            if month_index is not None:
                monthly_data[month_index]['sales_expense'] += cost.amount

        # 固定費の計算
        for i, data in monthly_data.items():
            target_year = data['year']
            target_month = data['month']

            fixed_costs = FixedCost.objects.filter(is_active=True)
            monthly_fixed_total = Decimal('0')

            for fixed_cost in fixed_costs:
                if fixed_cost.is_active_in_month(target_year, target_month):
                    monthly_fixed_total += fixed_cost.monthly_amount

            monthly_data[i]['fixed_costs'] = monthly_fixed_total

        # 損益計算
        for i, data in monthly_data.items():
            data['gross_profit'] = data['revenue'] - data['cost_of_sales']
            data['operating_profit'] = data['gross_profit'] - data['sales_expense'] - data['fixed_costs']

        # 今月度・年度累計の計算
        current_month_data = None
        ytd_data = {
            'revenue': Decimal('0'),
            'cost_of_sales': Decimal('0'),
            'gross_profit': Decimal('0'),
            'sales_expense': Decimal('0'),
            'fixed_costs': Decimal('0'),
            'operating_profit': Decimal('0'),
            'new_projects': 0,
            'completed_projects': 0,
        }

        for i, data in monthly_data.items():
            if data['is_current']:
                current_month_data = data

            if data['is_actual']:
                for key in ['revenue', 'cost_of_sales', 'gross_profit', 'sales_expense', 'fixed_costs', 'operating_profit']:
                    ytd_data[key] += data[key]
                ytd_data['new_projects'] += data['new_projects']
                ytd_data['completed_projects'] += data['completed_projects']

        # 利益率計算
        current_month_margin = Decimal('0')
        ytd_margin = Decimal('0')

        if current_month_data and current_month_data['revenue'] > 0:
            current_month_margin = (current_month_data['operating_profit'] / current_month_data['revenue']) * 100

        if ytd_data['revenue'] > 0:
            ytd_margin = (ytd_data['operating_profit'] / ytd_data['revenue']) * 100

        # 連続黒字月数の計算
        consecutive_profit_months = self.calculate_consecutive_profit_months(monthly_data, current_date)

        return {
            'current_date': current_date,
            'fiscal_year': year,
            'current_month_data': current_month_data,
            'current_month_margin': current_month_margin,
            'ytd_data': ytd_data,
            'ytd_margin': ytd_margin,
            'monthly_data': monthly_data,
            'consecutive_profit_months': consecutive_profit_months,
        }

    def get_fiscal_month_index(self, date, fiscal_year):
        """会計年度内の月インデックスを取得"""
        if date.month >= 4:
            if date.year == fiscal_year:
                return date.month - 4
        else:
            if date.year == fiscal_year + 1:
                return date.month + 8
        return None

    def calculate_consecutive_profit_months(self, monthly_data, current_date):
        """連続黒字月数を計算"""
        # 現在の月から逆順で確認していく
        consecutive_months = 0

        # 月次データを時系列順にソート（新しい月から古い月へ）
        sorted_months = []
        for key, data in monthly_data.items():
            # 実績がある月のみを対象とし、未来の月は除外
            if data['is_actual']:
                sorted_months.append(data)

        # 年月でソート（新しい順）
        sorted_months.sort(key=lambda x: (x['year'], x['month']), reverse=True)

        # 最新月から逆算して連続黒字月数を計算
        for month_data in sorted_months:
            if month_data['operating_profit'] > 0:
                consecutive_months += 1
            else:
                # 赤字の月が見つかったら連続記録終了
                break

        return consecutive_months