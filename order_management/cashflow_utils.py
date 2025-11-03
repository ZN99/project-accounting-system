"""
キャッシュフロー集計ユーティリティ - Phase 1
"""

from django.db.models import Sum, Q, F, Case, When, DecimalField, Value
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from .models import Project, CashFlowTransaction


def get_monthly_accrual_revenue(year, month):
    """月別発生主義売上（完工ベース）"""
    projects = Project.objects.filter(
        project_status='完工',
        completion_date__year=year,
        completion_date__month=month
    )

    total = projects.aggregate(
        total=Sum('billing_amount')
    )['total'] or Decimal('0')

    return {
        'year': year,
        'month': month,
        'total': total,
        'count': projects.count(),
        'projects': projects
    }


def get_monthly_cash_revenue(year, month):
    """月別現金主義売上（入金ベース）- CashFlowTransactionベース"""
    # revenue_cash で is_planned=False（実績）のみ
    total = CashFlowTransaction.objects.filter(
        transaction_type='revenue_cash',
        is_planned=False,
        transaction_date__year=year,
        transaction_date__month=month
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    count = CashFlowTransaction.objects.filter(
        transaction_type='revenue_cash',
        is_planned=False,
        transaction_date__year=year,
        transaction_date__month=month
    ).count()

    return {
        'year': year,
        'month': month,
        'total': total,
        'count': count,
        'projects': []
    }


def get_monthly_accrual_expenses(year, month):
    """月別発生主義支出（発注ベース）- CashFlowTransactionベース"""
    # expense_accrual で集計
    total = CashFlowTransaction.objects.filter(
        transaction_type='expense_accrual',
        transaction_date__year=year,
        transaction_date__month=month
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    count = CashFlowTransaction.objects.filter(
        transaction_type='expense_accrual',
        transaction_date__year=year,
        transaction_date__month=month
    ).count()

    return {
        'year': year,
        'month': month,
        'total': total,
        'count': count,
        'subcontracts': []
    }


def get_monthly_cash_expenses(year, month):
    """月別現金主義支出（支払ベース）- CashFlowTransactionベース"""
    # expense_cash で is_planned=False（実績）のみ
    total = CashFlowTransaction.objects.filter(
        transaction_type='expense_cash',
        is_planned=False,
        transaction_date__year=year,
        transaction_date__month=month
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    count = CashFlowTransaction.objects.filter(
        transaction_type='expense_cash',
        is_planned=False,
        transaction_date__year=year,
        transaction_date__month=month
    ).count()

    return {
        'year': year,
        'month': month,
        'total': total,
        'count': count,
        'subcontracts': []
    }


def get_monthly_comparison(year, month):
    """月別発生主義 vs 現金主義の比較"""
    accrual_revenue = get_monthly_accrual_revenue(year, month)
    cash_revenue = get_monthly_cash_revenue(year, month)
    accrual_expenses = get_monthly_accrual_expenses(year, month)
    cash_expenses = get_monthly_cash_expenses(year, month)

    return {
        'year': year,
        'month': month,
        'revenue': {
            'accrual': accrual_revenue['total'],
            'cash': cash_revenue['total'],
            'receivable': accrual_revenue['total'] - cash_revenue['total']
        },
        'expenses': {
            'accrual': accrual_expenses['total'],
            'cash': cash_expenses['total'],
            'payable': accrual_expenses['total'] - cash_expenses['total']
        },
        'net': {
            'accrual': accrual_revenue['total'] - accrual_expenses['total'],
            'cash': cash_revenue['total'] - cash_expenses['total']
        }
    }


def get_daily_cash_flow(year, month):
    """日別キャッシュフロー（入金・出金）- CashFlowTransactionベース"""
    from datetime import date
    from calendar import monthrange

    # 月の日数を取得
    _, last_day = monthrange(year, month)

    daily_data = []

    for day in range(1, last_day + 1):
        target_date = date(year, month, day)

        # 入金（実績のみ）
        revenue = CashFlowTransaction.objects.filter(
            transaction_type='revenue_cash',
            is_planned=False,
            transaction_date=target_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # 出金（実績のみ）
        expenses = CashFlowTransaction.objects.filter(
            transaction_type='expense_cash',
            is_planned=False,
            transaction_date=target_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        daily_data.append({
            'date': target_date,
            'day': day,
            'revenue': revenue,
            'expenses': expenses,
            'net': revenue - expenses
        })

    return daily_data


def get_receivables_summary():
    """売掛金サマリー（回収待ちの案件）"""
    projects = Project.objects.filter(
        project_status='完工',
        completion_date__isnull=False
    ).filter(
        Q(payment_received_date__isnull=True) |
        Q(payment_received_amount__lt=F('billing_amount'))
    )

    total_receivable = Decimal('0')
    project_list = []

    for project in projects:
        revenue_status = project.get_revenue_status()
        if revenue_status['receivable'] > 0:
            total_receivable += revenue_status['receivable']
            project_list.append({
                'project': project,
                'accrual': revenue_status['accrual'],
                'cash': revenue_status['cash'],
                'receivable': revenue_status['receivable'],
                'days_overdue': (datetime.now().date() - project.completion_date).days if project.completion_date else 0
            })

    # 期限超過順にソート
    project_list.sort(key=lambda x: x['days_overdue'], reverse=True)

    return {
        'total_receivable': total_receivable,
        'count': len(project_list),
        'projects': project_list
    }


def get_payables_summary():
    """買掛金サマリー（支払待ちの外注）"""
    try:
        from subcontract_management.models import Subcontract

        subcontracts = Subcontract.objects.filter(
            payment_date__isnull=True
        )

        total_payable = subcontracts.aggregate(
            total=Sum('contract_amount')
        )['total'] or Decimal('0')

        subcontract_list = []

        for sc in subcontracts:
            payment_amount = sc.contract_amount or Decimal('0')
            subcontract_list.append({
                'subcontract': sc,
                'amount': payment_amount,
                'project': sc.project,
                'days_since_created': (datetime.now().date() - sc.created_at.date()).days
            })

        # 作成日が古い順にソート
        subcontract_list.sort(key=lambda x: x['days_since_created'], reverse=True)

        return {
            'total_payable': total_payable,
            'count': len(subcontract_list),
            'subcontracts': subcontract_list
        }
    except ImportError:
        return {
            'total_payable': Decimal('0'),
            'count': 0,
            'subcontracts': []
        }


def get_cashflow_forecast(months=3):
    """キャッシュフロー予測（今後N ヶ月）- CashFlowTransactionベース"""
    from datetime import date
    from dateutil.relativedelta import relativedelta

    forecast_data = []
    today = date.today()

    for i in range(months):
        target_date = today + relativedelta(months=i)
        year = target_date.year
        month = target_date.month

        # 月の開始日と終了日
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        # 入金予定（revenue_cash で is_planned=True）
        planned_revenue = CashFlowTransaction.objects.filter(
            transaction_type='revenue_cash',
            is_planned=True,
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # 出金予定（expense_cash で is_planned=True）
        planned_expenses = CashFlowTransaction.objects.filter(
            transaction_type='expense_cash',
            is_planned=True,
            transaction_date__gte=month_start,
            transaction_date__lt=month_end
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        forecast_data.append({
            'year': year,
            'month': month,
            'planned_revenue': planned_revenue,
            'planned_expenses': planned_expenses,
            'net': planned_revenue - planned_expenses
        })

    return forecast_data
