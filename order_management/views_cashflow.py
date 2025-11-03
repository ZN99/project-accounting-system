"""
キャッシュフロー管理ビュー - Phase 1
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import Project, CashFlowTransaction
from .cashflow_utils import (
    get_monthly_accrual_revenue,
    get_monthly_cash_revenue,
    get_monthly_accrual_expenses,
    get_monthly_cash_expenses,
    get_monthly_comparison,
    get_daily_cash_flow,
    get_receivables_summary,
    get_payables_summary,
    get_cashflow_forecast
)
from .utils import safe_int


class CashFlowDashboardView(LoginRequiredMixin, TemplateView):
    """キャッシュフローダッシュボード"""
    template_name = 'order_management/cashflow_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 対象年月（パラメータで指定可能、デフォルトは当月）
        year = safe_int(self.request.GET.get('year', timezone.now().year))
        month = safe_int(self.request.GET.get('month', timezone.now().month))

        # 当月の発生主義 vs 現金主義
        context['monthly_comparison'] = get_monthly_comparison(year, month)

        # 日別キャッシュフロー
        context['daily_cashflow'] = get_daily_cash_flow(year, month)

        # 売掛金サマリー
        context['receivables'] = get_receivables_summary()

        # 買掛金サマリー
        context['payables'] = get_payables_summary()

        # キャッシュフロー予測（今後3ヶ月）
        context['forecast'] = get_cashflow_forecast(months=3)

        # 当月キャッシュフロー概要
        context['current_month_summary'] = self.get_current_month_summary(year, month)

        # 年月ナビゲーション
        context['current_year'] = year
        context['current_month'] = month
        context['prev_year'], context['prev_month'] = self.get_prev_month(year, month)
        context['next_year'], context['next_month'] = self.get_next_month(year, month)

        # グラフデータ（JSON形式）
        context['chart_data'] = self.get_chart_data(year, month)

        return context

    def get_current_month_summary(self, year, month):
        """当月キャッシュフロー概要"""
        comparison = get_monthly_comparison(year, month)
        receivables = get_receivables_summary()
        payables = get_payables_summary()

        return {
            'revenue_accrual': comparison['revenue']['accrual'],
            'revenue_cash': comparison['revenue']['cash'],
            'revenue_receivable': comparison['revenue']['receivable'],
            'expense_accrual': comparison['expenses']['accrual'],
            'expense_cash': comparison['expenses']['cash'],
            'expense_payable': comparison['expenses']['payable'],
            'net_accrual': comparison['net']['accrual'],
            'net_cash': comparison['net']['cash'],
            'total_receivables': receivables['total_receivable'],
            'total_payables': payables['total_payable'],
            'working_capital': receivables['total_receivable'] - payables['total_payable']
        }

    def get_chart_data(self, year, month):
        """グラフ用データ（JSON）"""
        import json

        daily_data = get_daily_cash_flow(year, month)

        # 日別入出金グラフデータ
        daily_chart = {
            'labels': [str(d['day']) + '日' for d in daily_data],
            'revenue': [float(d['revenue']) for d in daily_data],
            'expenses': [float(d['expenses']) for d in daily_data],
            'net': [float(d['net']) for d in daily_data]
        }

        # 過去6ヶ月の発生主義 vs 現金主義
        comparison_chart_data = []
        for i in range(5, -1, -1):
            target_date = datetime(year, month, 1) - timedelta(days=30 * i)
            comparison = get_monthly_comparison(target_date.year, target_date.month)
            comparison_chart_data.append({
                'month': f"{target_date.year}/{target_date.month}",
                'accrual_revenue': float(comparison['revenue']['accrual']),
                'cash_revenue': float(comparison['revenue']['cash']),
                'accrual_expense': float(comparison['expenses']['accrual']),
                'cash_expense': float(comparison['expenses']['cash'])
            })

        comparison_chart = {
            'labels': [d['month'] for d in comparison_chart_data],
            'accrual_revenue': [d['accrual_revenue'] for d in comparison_chart_data],
            'cash_revenue': [d['cash_revenue'] for d in comparison_chart_data],
            'accrual_expense': [d['accrual_expense'] for d in comparison_chart_data],
            'cash_expense': [d['cash_expense'] for d in comparison_chart_data]
        }

        return {
            'daily': json.dumps(daily_chart, ensure_ascii=False),
            'comparison': json.dumps(comparison_chart, ensure_ascii=False)
        }

    def get_prev_month(self, year, month):
        """前月を取得"""
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def get_next_month(self, year, month):
        """次月を取得"""
        if month == 12:
            return year + 1, 1
        return year, month + 1


class AccrualVsCashComparisonView(LoginRequiredMixin, TemplateView):
    """発生主義 vs 現金主義 比較ビュー"""
    template_name = 'order_management/cashflow_comparison.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 対象期間（デフォルトは過去12ヶ月）
        months = int(self.request.GET.get('months', 12))

        comparison_data = []
        today = timezone.now()

        for i in range(months - 1, -1, -1):
            target_date = datetime(today.year, today.month, 1) - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month

            comparison = get_monthly_comparison(year, month)
            comparison_data.append({
                'year': year,
                'month': month,
                'month_label': f"{year}年{month}月",
                'revenue_accrual': comparison['revenue']['accrual'],
                'revenue_cash': comparison['revenue']['cash'],
                'revenue_receivable': comparison['revenue']['receivable'],
                'expense_accrual': comparison['expenses']['accrual'],
                'expense_cash': comparison['expenses']['cash'],
                'expense_payable': comparison['expenses']['payable'],
                'net_accrual': comparison['net']['accrual'],
                'net_cash': comparison['net']['cash']
            })

        context['comparison_data'] = comparison_data
        context['months'] = months

        return context


class ReceivablesDetailView(LoginRequiredMixin, TemplateView):
    """売掛金詳細ビュー"""
    template_name = 'order_management/receivables_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        receivables = get_receivables_summary()
        context['receivables'] = receivables

        return context


class PayablesDetailView(LoginRequiredMixin, TemplateView):
    """買掛金詳細ビュー"""
    template_name = 'order_management/payables_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        payables = get_payables_summary()
        context['payables'] = payables

        return context


# ====================
# API Endpoints - Phase 1
# ====================

@login_required
@require_http_methods(["GET"])
def cashflow_monthly_api(request):
    """月次キャッシュフローデータAPI"""
    year = safe_int(request.GET.get('year', timezone.now().year))
    month = safe_int(request.GET.get('month', timezone.now().month))

    comparison = get_monthly_comparison(year, month)

    # Decimal to float for JSON serialization
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decimal_to_float(item) for item in obj]
        return obj

    return JsonResponse(decimal_to_float(comparison))


@login_required
@require_http_methods(["GET"])
def cashflow_daily_api(request):
    """日別キャッシュフローデータAPI"""
    year = safe_int(request.GET.get('year', timezone.now().year))
    month = safe_int(request.GET.get('month', timezone.now().month))

    daily_data = get_daily_cash_flow(year, month)

    # Convert dates and decimals for JSON
    result = []
    for day_data in daily_data:
        result.append({
            'date': day_data['date'].isoformat(),
            'day': day_data['day'],
            'revenue': float(day_data['revenue']),
            'expenses': float(day_data['expenses']),
            'net': float(day_data['net'])
        })

    return JsonResponse({'daily_data': result})


@login_required
@require_http_methods(["GET"])
def cashflow_forecast_api(request):
    """キャッシュフロー予測データAPI"""
    months = safe_int(request.GET.get('months', 3))

    forecast = get_cashflow_forecast(months=months)

    # Convert decimals for JSON
    result = []
    for month_data in forecast:
        result.append({
            'year': month_data['year'],
            'month': month_data['month'],
            'planned_revenue': float(month_data['planned_revenue']),
            'planned_expenses': float(month_data['planned_expenses']),
            'net': float(month_data['net'])
        })

    return JsonResponse({'forecast': result})


@login_required
@require_http_methods(["GET"])
def receivables_api(request):
    """売掛金データAPI"""
    receivables = get_receivables_summary()

    # Convert for JSON
    projects_data = []
    for item in receivables['projects']:
        projects_data.append({
            'project_id': item['project'].id,
            'management_no': item['project'].management_no,
            'site_name': item['project'].site_name,
            'client_name': item['project'].client_name,
            'accrual': float(item['accrual']),
            'cash': float(item['cash']),
            'receivable': float(item['receivable']),
            'days_overdue': item['days_overdue']
        })

    return JsonResponse({
        'total_receivable': float(receivables['total_receivable']),
        'count': receivables['count'],
        'projects': projects_data
    })


@login_required
@require_http_methods(["GET"])
def payables_api(request):
    """買掛金データAPI"""
    payables = get_payables_summary()

    # Convert for JSON
    subcontracts_data = []
    for item in payables['subcontracts']:
        subcontracts_data.append({
            'subcontract_id': item['subcontract'].id,
            'site_name': item['subcontract'].site_name,
            'contractor': item['subcontract'].contractor.name if item['subcontract'].contractor else 'N/A',
            'amount': float(item['amount']),
            'project_id': item['project'].id,
            'management_no': item['project'].management_no,
            'days_since_created': item['days_since_created']
        })

    return JsonResponse({
        'total_payable': float(payables['total_payable']),
        'count': payables['count'],
        'subcontracts': subcontracts_data
    })
