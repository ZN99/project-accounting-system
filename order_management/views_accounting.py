from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q, Sum, Count, Case, When, DecimalField
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import Project, FixedCost, VariableCost
from .user_roles import has_any_role, UserRole
from subcontract_management.models import Subcontract, Contractor, InternalWorker
import calendar
from decimal import Decimal
from .utils import safe_int


class AccountingDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'order_management/accounting_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # 経理・役員のみアクセス可能
        if not has_any_role(request.user, [UserRole.ACCOUNTING, UserRole.EXECUTIVE]):
            raise PermissionDenied("会計ダッシュボードへのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 現在の月を取得（デフォルト）
        now = timezone.now()
        year = safe_int(self.request.GET.get('year', now.year))
        month = safe_int(self.request.GET.get('month', now.month))
        view_type = self.request.GET.get('view', 'summary')  # summary, ledger

        # 月の開始日と終了日
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()

        # === 入金データ（入金ベース） ===
        receipt_projects = Project.objects.filter(
            payment_due_date__range=[start_date, end_date],
            project_status='完工',
            billing_amount__gt=0
        ).exclude(client_name__isnull=True).exclude(client_name='')

        receipt_total = 0
        receipt_received = 0
        receipt_pending = 0

        for project in receipt_projects:
            amount = project.billing_amount or project.estimate_amount or 0
            receipt_total += amount
            if project.work_end_completed:
                receipt_received += amount
            else:
                receipt_pending += amount

        # === 出金データ（出金ベース） ===
        payment_subcontracts = Subcontract.objects.filter(
            payment_date__range=[start_date, end_date],
            billed_amount__gt=0
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

        # === 通帳スタイルのトランザクション（日付ベース） ===
        transactions = []

        # 入金トランザクション
        for project in receipt_projects:
            amount = project.billing_amount or project.order_amount or 0
            if amount > 0:
                transactions.append({
                    'date': project.payment_due_date or project.contract_date or start_date,
                    'description': f'入金: {project.site_name}',
                    'client': project.client_name,
                    'type': 'receipt',
                    'amount': amount,
                    'status': 'completed' if project.payment_status == 'executed' else 'pending',
                    'project': project
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

        # 残高計算（古い順に処理）
        transactions_sorted = sorted(transactions, key=lambda x: x['date'])

        running_balance = 0
        for transaction in transactions_sorted:
            if transaction['type'] == 'receipt':
                if transaction['status'] == 'completed':
                    running_balance += transaction['amount']
            else:  # payment
                if transaction['status'] == 'paid':
                    running_balance -= transaction['amount']

            # 各トランザクションに残高を直接保存
            transaction['balance'] = running_balance

        # 表示用に新しい順でソート
        transactions.sort(key=lambda x: x['date'], reverse=True)

        # 統計情報
        stats = {
            'total_receipt': receipt_total,
            'receipt_received': receipt_received,
            'receipt_pending': receipt_pending,
            'total_payment': payment_total,
            'payment_paid': payment_paid,
            'payment_pending': payment_pending,
            'net_cashflow': receipt_received - payment_paid,  # 実際のキャッシュフロー
            'projected_cashflow': receipt_total - payment_total,  # 予想キャッシュフロー
        }

        # ビュータイプの選択肢
        view_type_choices = [
            ('summary', 'サマリー表示'),
            ('ledger', '通帳表示'),
        ]

        # === 年間業績データ ===
        annual_performance = self.get_annual_performance(year)

        context.update({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'view_type': view_type,
            'view_type_choices': view_type_choices,
            'receipt_projects': receipt_projects,
            'payment_subcontracts': payment_subcontracts,
            'transactions': transactions,
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
            'annual_performance': annual_performance,
        })

        return context

    def get_annual_performance(self, year):
        """年間業績データを計算"""
        # 会計年度: 4月-3月
        fiscal_year_start = datetime(year, 4, 1).date()
        fiscal_year_end = datetime(year + 1, 3, 31).date()
        current_date = timezone.now().date()
        current_month = current_date.month
        current_year = current_date.year

        # 月次データを初期化（4月=0, 5月=1, ..., 3月=11）
        monthly_data = {}
        for i in range(12):
            month_offset = i + 4  # 4月から開始
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
                'revenue': Decimal('0'),           # 売上高
                'cost_of_sales': Decimal('0'),     # 売上原価
                'cost_labor': Decimal('0'),        # 職人さん人工
                'cost_materials': Decimal('0'),    # 資材
                'gross_profit': Decimal('0'),      # 売上総利益
                'sales_expense': Decimal('0'),     # 販管費
                'fixed_costs': Decimal('0'),       # 固定費
                'operating_profit': Decimal('0'),  # 営業利益
                'is_actual': False,                # 実績かどうか
                'is_current': False                # 今月かどうか
            }

        # 実績データと今月フラグの設定
        for i, data in monthly_data.items():
            target_date = datetime(data['year'], data['month'], 1).date()
            if target_date <= current_date:
                data['is_actual'] = True
            if data['year'] == current_year and data['month'] == current_month:
                data['is_current'] = True

        # === 売上高・売上原価の計算 ===
        # 受注済みプロジェクトから売上を計算
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
                # 売上高
                revenue = project.billing_amount or Decimal('0')
                monthly_data[month_index]['revenue'] += revenue

                # 売上原価（Subcontractから取得）
                subcontracts = Subcontract.objects.filter(project=project)
                for subcontract in subcontracts:
                    cost = subcontract.billed_amount or subcontract.contract_amount or Decimal('0')
                    monthly_data[month_index]['cost_of_sales'] += cost

                    # 職人さん人工 vs 資材の分類
                    if subcontract.worker_type == 'external':
                        monthly_data[month_index]['cost_labor'] += cost
                    # 資材費は現在のデータ構造では判断困難なため、一律職人さん人工として扱う

        # === 販管費の計算 ===
        variable_costs = VariableCost.objects.filter(
            incurred_date__range=[fiscal_year_start, fiscal_year_end]
        )

        for cost in variable_costs:
            month_index = self.get_fiscal_month_index(cost.incurred_date, year)
            if month_index is not None:
                monthly_data[month_index]['sales_expense'] += cost.amount

        # === 固定費の計算 ===
        for i, data in monthly_data.items():
            target_year = data['year']
            target_month = data['month']

            fixed_costs = FixedCost.objects.filter(is_active=True)
            monthly_fixed_total = Decimal('0')

            for fixed_cost in fixed_costs:
                if fixed_cost.is_active_in_month(target_year, target_month):
                    monthly_fixed_total += fixed_cost.monthly_amount

            monthly_data[i]['fixed_costs'] = monthly_fixed_total

        # === 損益計算 ===
        for i, data in monthly_data.items():
            data['gross_profit'] = data['revenue'] - data['cost_of_sales']
            data['operating_profit'] = data['gross_profit'] - data['sales_expense'] - data['fixed_costs']

        # === 今月度・年度累計の計算 ===
        current_month_data = None
        ytd_data = {
            'revenue': Decimal('0'),
            'cost_of_sales': Decimal('0'),
            'gross_profit': Decimal('0'),
            'sales_expense': Decimal('0'),
            'fixed_costs': Decimal('0'),
            'operating_profit': Decimal('0'),
        }

        for i, data in monthly_data.items():
            if data['is_current']:
                current_month_data = data

            if data['is_actual']:
                for key in ytd_data.keys():
                    ytd_data[key] += data[key]

        # 利益率計算
        current_month_margin = Decimal('0')
        ytd_margin = Decimal('0')

        if current_month_data and current_month_data['revenue'] > 0:
            current_month_margin = (current_month_data['operating_profit'] / current_month_data['revenue']) * 100

        if ytd_data['revenue'] > 0:
            ytd_margin = (ytd_data['operating_profit'] / ytd_data['revenue']) * 100

        return {
            'current_date': current_date,
            'fiscal_year': year,
            'current_month_data': current_month_data,
            'current_month_margin': current_month_margin,
            'ytd_data': ytd_data,
            'ytd_margin': ytd_margin,
            'monthly_data': monthly_data,
        }

    def get_fiscal_month_index(self, date, fiscal_year):
        """会計年度内の月インデックスを取得（4月=0, 5月=1, ..., 3月=11）"""
        if date.month >= 4:
            # 4月-12月
            if date.year == fiscal_year:
                return date.month - 4
        else:
            # 1月-3月
            if date.year == fiscal_year + 1:
                return date.month + 8

        return None