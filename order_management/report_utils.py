"""
レポート生成ユーティリティ - Phase 3

各種レポートの生成ロジックを提供します。
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from .models import (
    Project, CashFlowTransaction, ForecastScenario,
    ProjectProgress, Report
)


def generate_monthly_report(year, month):
    """
    月次経営レポートを生成

    Args:
        year: 年
        month: 月

    Returns:
        dict: レポートデータ
    """
    # 対象期間
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(year, month + 1, 1) - timedelta(days=1)

    # 1. 売上・利益サマリー
    completed_projects = Project.objects.filter(
        project_status='完工',
        completion_date__gte=period_start,
        completion_date__lte=period_end
    )

    total_revenue = sum(p.order_amount for p in completed_projects if p.order_amount) or Decimal('0')
    project_count = completed_projects.count()
    avg_order_amount = total_revenue / project_count if project_count > 0 else Decimal('0')

    # 原価率を仮定（75%）
    cost_rate = Decimal('0.75')
    total_cost = total_revenue * cost_rate
    total_profit = total_revenue - total_cost
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')

    # 2. プロジェクト進捗状況
    progress_summary = {
        '完工': Project.objects.filter(project_status='完工', completion_date__month=month).count(),
        '進行中': Project.objects.filter(project_status='進行中').count(),
        '施工日待ち': Project.objects.filter(project_status='施工日待ち').count(),
        'ネタ': Project.objects.filter(project_status='ネタ').count(),
        'NG': Project.objects.filter(project_status='NG', completion_date__month=month).count(),
    }

    # 3. キャッシュフロー状況
    revenue_transactions = CashFlowTransaction.objects.filter(
        transaction_type='revenue_cash',
        transaction_date__gte=period_start,
        transaction_date__lte=period_end
    )

    expense_transactions = CashFlowTransaction.objects.filter(
        transaction_type='expense_cash',
        transaction_date__gte=period_start,
        transaction_date__lte=period_end
    )

    total_cash_in = sum(t.amount for t in revenue_transactions if t.amount) or Decimal('0')
    total_cash_out = sum(t.amount for t in expense_transactions if t.amount) or Decimal('0')
    net_cash_flow = total_cash_in - total_cash_out

    # 4. 予実対比（前月との比較）
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    prev_period_start = date(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_period_end = date(prev_year + 1, 1, 1) - timedelta(days=1)
    else:
        prev_period_end = date(prev_year, prev_month + 1, 1) - timedelta(days=1)

    prev_completed = Project.objects.filter(
        project_status='完工',
        completion_date__gte=prev_period_start,
        completion_date__lte=prev_period_end
    )

    prev_revenue = sum(p.order_amount for p in prev_completed if p.order_amount) or Decimal('0')
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else Decimal('0')

    # レポートデータを構築
    report_data = {
        'period': {
            'year': year,
            'month': month,
            'start_date': period_start.isoformat(),
            'end_date': period_end.isoformat()
        },
        'revenue_summary': {
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'total_profit': float(total_profit),
            'profit_margin': float(profit_margin),
            'project_count': project_count,
            'avg_order_amount': float(avg_order_amount)
        },
        'progress_summary': progress_summary,
        'cashflow_summary': {
            'total_cash_in': float(total_cash_in),
            'total_cash_out': float(total_cash_out),
            'net_cash_flow': float(net_cash_flow)
        },
        'comparison': {
            'prev_revenue': float(prev_revenue),
            'revenue_growth': float(revenue_growth)
        }
    }

    return report_data


def generate_project_report(project_id):
    """
    プロジェクト別レポートを生成

    Args:
        project_id: プロジェクトID

    Returns:
        dict: レポートデータ
    """
    from django.shortcuts import get_object_or_404

    project = get_object_or_404(Project, id=project_id)

    # 1. プロジェクト詳細
    project_detail = {
        'management_no': project.management_no,
        'site_name': project.site_name,
        'site_address': project.site_address,
        'work_type': project.work_type,
        'project_status': project.project_status,
        'order_amount': float(project.order_amount) if project.order_amount else 0,
        'client_name': project.client_name,
        'project_manager': project.project_manager,
    }

    # 2. スケジュール情報
    schedule = {
        'estimate_issued_date': project.estimate_issued_date.isoformat() if project.estimate_issued_date else None,
        'contract_date': project.contract_date.isoformat() if project.contract_date else None,
        'work_start_date': project.work_start_date.isoformat() if project.work_start_date else None,
        'work_end_date': project.work_end_date.isoformat() if project.work_end_date else None,
        'completion_date': project.completion_date.isoformat() if project.completion_date else None,
    }

    # 3. 原価・利益分析
    # 外注コストを計算
    try:
        if hasattr(project, 'subcontract'):
            subcontract = project.subcontract
            total_subcontract_cost = subcontract.total_subcontract_amount or Decimal('0')
        else:
            total_subcontract_cost = Decimal('0')
    except:
        total_subcontract_cost = Decimal('0')

    # 材料費を計算
    try:
        material_orders = project.material_orders.all()
        total_material_cost = sum(
            (m.items.aggregate(total=models.Sum('total_price'))['total'] or Decimal('0'))
            for m in material_orders
        )
    except:
        total_material_cost = Decimal('0')

    # 人件費・その他原価（簡略化）
    labor_cost = Decimal('0')
    other_cost = Decimal('0')

    total_cost = total_subcontract_cost + total_material_cost + labor_cost + other_cost
    gross_profit = (project.order_amount or Decimal('0')) - total_cost
    profit_margin = (gross_profit / project.order_amount * 100) if project.order_amount and project.order_amount > 0 else Decimal('0')

    cost_analysis = {
        'total_cost': float(total_cost),
        'labor_cost': float(labor_cost),
        'material_cost': float(total_material_cost),
        'subcontract_cost': float(total_subcontract_cost),
        'other_cost': float(other_cost),
        'gross_profit': float(gross_profit),
        'profit_margin': float(profit_margin)
    }

    # 4. 進捗状況
    latest_progress = project.progress_records.order_by('-recorded_date').first()

    progress_info = {
        'has_progress': latest_progress is not None,
        'progress_rate': float(latest_progress.progress_rate) if latest_progress else 0,
        'status': latest_progress.status if latest_progress else 'unknown',
        'has_risk': latest_progress.has_risk if latest_progress else False,
        'risk_level': latest_progress.risk_level if latest_progress else None,
        'risk_description': latest_progress.risk_description if latest_progress else ''
    }

    # 5. キャッシュフロー
    transactions = project.cash_transactions.all()
    revenue_transactions = [t for t in transactions if t.transaction_type in ['revenue_accrual', 'revenue_cash']]
    expense_transactions = [t for t in transactions if t.transaction_type in ['expense_accrual', 'expense_cash']]

    total_revenue_tx = sum(t.amount for t in revenue_transactions if t.amount) or Decimal('0')
    total_expense_tx = sum(t.amount for t in expense_transactions if t.amount) or Decimal('0')

    cashflow_info = {
        'total_revenue_transactions': float(total_revenue_tx),
        'total_expense_transactions': float(total_expense_tx),
        'net_cashflow': float(total_revenue_tx - total_expense_tx),
        'transaction_count': len(transactions)
    }

    # レポートデータを構築（テンプレートに合わせた構造）
    report_data = {
        'project_info': {
            'name': project.management_no or project.site_name or "プロジェクト",
            'client': project.client_name or "-",
            'status': project.project_status or "-",
            'order_amount': float(project.order_amount or 0),
            'contract_date': project.contract_date.isoformat() if project.contract_date else None,
            'expected_completion': project.work_end_date.isoformat() if project.work_end_date else None,
        },
        'financial_summary': {
            'revenue': float(project.order_amount or 0),
            'total_cost': cost_analysis['total_cost'],
            'labor_cost': cost_analysis['labor_cost'],
            'material_cost': cost_analysis['material_cost'],
            'subcontract_cost': cost_analysis['subcontract_cost'],
            'other_cost': cost_analysis['other_cost'],
            'profit': cost_analysis['gross_profit'],
            'profit_margin': cost_analysis['profit_margin']
        },
        'progress': progress_info,
        'cost_breakdown': [
            {'category': '人件費', 'amount': cost_analysis['labor_cost'], 'percentage': (cost_analysis['labor_cost'] / cost_analysis['total_cost'] * 100) if cost_analysis['total_cost'] > 0 else 0},
            {'category': '材料費', 'amount': cost_analysis['material_cost'], 'percentage': (cost_analysis['material_cost'] / cost_analysis['total_cost'] * 100) if cost_analysis['total_cost'] > 0 else 0},
            {'category': '外注費', 'amount': cost_analysis['subcontract_cost'], 'percentage': (cost_analysis['subcontract_cost'] / cost_analysis['total_cost'] * 100) if cost_analysis['total_cost'] > 0 else 0},
            {'category': 'その他', 'amount': cost_analysis['other_cost'], 'percentage': (cost_analysis['other_cost'] / cost_analysis['total_cost'] * 100) if cost_analysis['total_cost'] > 0 else 0},
        ],
        'generated_at': timezone.now().isoformat()
    }

    return report_data


def generate_cashflow_report(year, month):
    """
    キャッシュフローレポートを生成

    Args:
        year: 年
        month: 月

    Returns:
        dict: レポートデータ
    """
    # 対象期間
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(year, month + 1, 1) - timedelta(days=1)

    # 1. 入出金予定
    scheduled_in = CashFlowTransaction.objects.filter(
        transaction_type='revenue_cash',
        transaction_date__gte=period_start,
        transaction_date__lte=period_end,
        is_planned=True
    )

    scheduled_out = CashFlowTransaction.objects.filter(
        transaction_type='expense_cash',
        transaction_date__gte=period_start,
        transaction_date__lte=period_end,
        is_planned=True
    )

    total_scheduled_in = sum(t.amount for t in scheduled_in if t.amount) or Decimal('0')
    total_scheduled_out = sum(t.amount for t in scheduled_out if t.amount) or Decimal('0')

    # 2. 売掛金・買掛金一覧
    receivables = []
    for tx in scheduled_in:
        receivables.append({
            'project_name': tx.project.site_name if tx.project else 'N/A',
            'amount': float(tx.amount),
            'due_date': tx.transaction_date.isoformat(),
            'description': tx.description
        })

    payables = []
    for tx in scheduled_out:
        payables.append({
            'project_name': tx.project.site_name if tx.project else 'N/A',
            'amount': float(tx.amount),
            'due_date': tx.transaction_date.isoformat(),
            'description': tx.description
        })

    # 3. 資金繰り表（今月〜3ヶ月先）
    cash_flow_forecast = []
    for i in range(4):
        forecast_month = month + i
        forecast_year = year
        if forecast_month > 12:
            forecast_month -= 12
            forecast_year += 1

        month_start = date(forecast_year, forecast_month, 1)
        if forecast_month == 12:
            month_end = date(forecast_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(forecast_year, forecast_month + 1, 1) - timedelta(days=1)

        month_in = CashFlowTransaction.objects.filter(
            transaction_type='revenue_cash',
            transaction_date__gte=month_start,
            transaction_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        month_out = CashFlowTransaction.objects.filter(
            transaction_type='expense_cash',
            transaction_date__gte=month_start,
            transaction_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        cash_flow_forecast.append({
            'year': forecast_year,
            'month': forecast_month,
            'inflow': float(month_in),
            'outflow': float(month_out),
            'net': float(month_in - month_out)
        })

    # 入出金スケジュール（テンプレート形式）
    cash_in_schedule = []
    for tx in scheduled_in:
        cash_in_schedule.append({
            'date': tx.transaction_date.isoformat(),
            'party_name': tx.project.client_name if tx.project else '-',
            'project_name': tx.project.site_name if tx.project else None,
            'amount': float(tx.amount),
            'is_planned': tx.is_planned
        })

    cash_out_schedule = []
    for tx in scheduled_out:
        cash_out_schedule.append({
            'date': tx.transaction_date.isoformat(),
            'party_name': '-',  # 後で取引先を追加
            'project_name': tx.project.site_name if tx.project else None,
            'amount': float(tx.amount),
            'is_planned': tx.is_planned
        })

    # レポートデータを構築（テンプレートに合わせた構造）
    report_data = {
        'summary': {
            'opening_balance': 0,  # 簡略化のため0
            'total_cash_in': float(total_scheduled_in),
            'total_cash_out': float(total_scheduled_out),
            'net_cash_flow': float(total_scheduled_in - total_scheduled_out),
            'closing_balance': float(total_scheduled_in - total_scheduled_out)
        },
        'cash_in_schedule': cash_in_schedule,
        'cash_out_schedule': cash_out_schedule,
        'accounts': {
            'receivable_balance': float(total_scheduled_in),
            'receivable_count': len(scheduled_in),
            'payable_balance': float(total_scheduled_out),
            'payable_count': len(scheduled_out)
        },
        'generated_at': timezone.now().isoformat()
    }

    return report_data


def generate_forecast_report(scenario_id):
    """
    予測レポートを生成

    Args:
        scenario_id: シナリオID

    Returns:
        dict: レポートデータ
    """
    from django.shortcuts import get_object_or_404

    scenario = get_object_or_404(ForecastScenario, id=scenario_id)

    # 予測がなければ計算
    if not scenario.forecast_results:
        scenario.calculate_forecast()
        scenario.refresh_from_db()

    # 1. シナリオ詳細
    scenario_detail = {
        'name': scenario.name,
        'description': scenario.description,
        'scenario_type': scenario.scenario_type,
        'conversion_rate_neta': float(scenario.conversion_rate_neta),
        'conversion_rate_waiting': float(scenario.conversion_rate_waiting),
        'cost_rate': float(scenario.cost_rate),
        'forecast_months': scenario.forecast_months,
        'seasonality_enabled': scenario.seasonality_enabled
    }

    # 2. 予測結果サマリー
    summary = scenario.get_summary()

    # 3. 月別予測データ
    monthly_data = scenario.forecast_results.get('monthly_data', [])

    # 4. 前提条件
    assumptions = {
        'base_calculation': '過去6ヶ月の実績平均',
        'pipeline_inclusion': 'ネタ・施工日待ち案件を考慮',
        'seasonality': '過去12ヶ月のパターンを反映' if scenario.seasonality_enabled else '季節性考慮なし',
        'cost_assumption': f'原価率 {scenario.cost_rate}%'
    }

    # 季節性指数データ
    seasonal_factors = []
    if hasattr(scenario, 'seasonalityindex'):
        si = scenario.seasonalityindex
        for month in range(1, 13):
            seasonal_factors.append({
                'month': month,
                'index': float(si.get_index_for_month(month))
            })

    # レポートデータを構築（テンプレートに合わせた構造）
    report_data = {
        'scenario_info': {
            'name': scenario.name,
            'forecast_months': scenario.forecast_months,
            'base_date': scenario.created_at.date().isoformat() if hasattr(scenario.created_at, 'date') else scenario.created_at.isoformat(),
            'created_at': scenario.created_at.isoformat()
        },
        'forecast_summary': {
            'total_revenue': summary.get('total_revenue', 0),
            'total_cost': summary.get('total_cost', 0),
            'total_profit': summary.get('total_profit', 0),
            'profit_margin': summary.get('profit_margin', 0),
            'avg_monthly_revenue': summary.get('avg_monthly_revenue', 0),
            'avg_monthly_profit': summary.get('avg_monthly_profit', 0)
        },
        'assumptions': {
            'revenue_growth_rate': 0,  # 簡略化
            'cost_growth_rate': 0,
            'use_seasonality': scenario.seasonality_enabled,
            'seasonal_factors': seasonal_factors
        },
        'monthly_breakdown': monthly_data,
        'risk_analysis': {
            'optimistic_profit': summary.get('total_profit', 0) * 1.1,
            'pessimistic_profit': summary.get('total_profit', 0) * 0.9
        },
        'generated_at': timezone.now().isoformat()
    }

    return report_data
