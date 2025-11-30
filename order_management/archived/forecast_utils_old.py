"""
売上予測・収支シミュレーション ユーティリティ - Phase 2
"""

from django.db.models import Sum, Count, Avg, Q, F, DecimalField, Case, When
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import calendar

from .models import Project, FixedCost, VariableCost, ForecastScenario


# ====================
# 1. 過去実績分析
# ====================

def analyze_historical_performance(months=12):
    """
    過去N ヶ月の実績を分析

    Returns:
        dict: {
            'monthly_revenue': [...],  # 月次売上推移
            'avg_revenue': Decimal,    # 平均月次売上
            'avg_order_amount': Decimal,  # 平均受注額
            'total_projects': int,     # 総案件数
            'completion_rate': Decimal,  # 完工率
            'seasonal_index': {...}    # 季節性指数
        }
    """
    today = date.today()
    start_date = today - relativedelta(months=months)

    # 月次売上データ
    monthly_data = []
    total_revenue = Decimal('0')

    for i in range(months):
        target_date = start_date + relativedelta(months=i)
        year = target_date.year
        month = target_date.month

        # 完工案件の売上
        month_projects = Project.objects.filter(
            project_status='完工',
            completion_date__year=year,
            completion_date__month=month
        )

        month_revenue = month_projects.aggregate(
            total=Sum('billing_amount')
        )['total'] or Decimal('0')

        total_revenue += month_revenue

        monthly_data.append({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'revenue': month_revenue,
            'project_count': month_projects.count()
        })

    # 統計計算
    avg_revenue = total_revenue / months if months > 0 else Decimal('0')

    # 平均受注額
    completed_projects = Project.objects.filter(
        project_status='完工',
        completion_date__gte=start_date
    )
    avg_order_amount = completed_projects.aggregate(
        avg=Avg('billing_amount')
    )['avg'] or Decimal('0')

    # 総案件数と完工率
    total_projects = Project.objects.filter(
        created_at__gte=start_date
    ).count()

    completed_count = completed_projects.count()
    completion_rate = (completed_count / total_projects * 100) if total_projects > 0 else Decimal('0')

    # 季節性指数計算
    seasonal_index = calculate_seasonal_index(monthly_data, avg_revenue)

    return {
        'monthly_revenue': monthly_data,
        'avg_revenue': avg_revenue,
        'avg_order_amount': avg_order_amount,
        'total_projects': total_projects,
        'completed_projects': completed_count,
        'completion_rate': completion_rate,
        'seasonal_index': seasonal_index
    }


def calculate_seasonal_index(monthly_data, avg_revenue):
    """
    季節性指数を計算（1.0 = 平均月）

    Args:
        monthly_data: 月次データリスト
        avg_revenue: 平均売上

    Returns:
        dict: {月番号: 季節性指数}
    """
    if avg_revenue == 0:
        return {i: Decimal('1.0') for i in range(1, 13)}

    # 各月の売上を集計
    month_totals = defaultdict(list)
    for data in monthly_data:
        month_totals[data['month']].append(data['revenue'])

    # 各月の平均と指数を計算
    seasonal_index = {}
    for month in range(1, 13):
        if month in month_totals and month_totals[month]:
            month_avg = sum(month_totals[month]) / len(month_totals[month])
            seasonal_index[month] = month_avg / avg_revenue if avg_revenue > 0 else Decimal('1.0')
        else:
            seasonal_index[month] = Decimal('1.0')

    return seasonal_index


def get_conversion_rate_by_status(status='ネタ', months=12):
    """
    ステータス別の過去成約率を計算

    Args:
        status: プロジェクトステータス
        months: 分析期間（月数）

    Returns:
        Decimal: 成約率（0-1）
    """
    today = date.today()
    start_date = today - relativedelta(months=months)

    # 指定ステータスだった案件数
    status_projects = Project.objects.filter(
        created_at__gte=start_date,
        project_status=status
    ).count()

    # そのうち完工になった案件数
    # Note: この簡易実装では現在完工の案件をカウント
    # 実際にはステータス遷移履歴が必要
    completed_from_status = Project.objects.filter(
        created_at__gte=start_date,
        project_status='完工'
    ).count()

    # 簡易的な成約率計算
    if status == 'ネタ':
        # ネタの場合は低めの成約率
        return Decimal('0.30')  # 30%
    elif status == '施工日待ち':
        # 施工日待ちは高めの成約率
        return Decimal('0.80')  # 80%
    else:
        return Decimal('0.50')  # デフォルト50%


# ====================
# 2. パイプライン分析
# ====================

def analyze_pipeline():
    """
    現在のパイプライン（ネタ、施工日待ち）を分析

    Returns:
        dict: {
            'neta': {...},  # ネタ案件情報
            'waiting': {...},  # 施工日待ち案件情報
            'total_pipeline_value': Decimal
        }
    """
    # ネタ案件
    neta_projects = Project.objects.filter(project_status='ネタ')
    neta_total = neta_projects.aggregate(
        total=Sum('order_amount')
    )['total'] or Decimal('0')

    # 施工日待ち案件
    waiting_projects = Project.objects.filter(project_status='施工日待ち')
    waiting_total = waiting_projects.aggregate(
        total=Sum('order_amount')
    )['total'] or Decimal('0')

    return {
        'neta': {
            'count': neta_projects.count(),
            'total_value': neta_total,
            'projects': neta_projects
        },
        'waiting': {
            'count': waiting_projects.count(),
            'total_value': waiting_total,
            'projects': waiting_projects
        },
        'total_pipeline_value': neta_total + waiting_total
    }


# ====================
# 3. 売上予測生成
# ====================

def generate_revenue_forecast(scenario, months=None):
    """
    売上予測を生成

    Args:
        scenario: ForecastScenario インスタンス
        months: 予測月数（Noneの場合はscenario.forecast_monthsを使用）

    Returns:
        list: 月次売上予測データ
    """
    if months is None:
        months = scenario.forecast_months

    today = date.today()

    # 過去実績を分析
    historical = analyze_historical_performance(months=12)
    avg_revenue = historical['avg_revenue']
    seasonal_index = historical['seasonal_index']

    # パイプライン分析
    pipeline = analyze_pipeline()

    # 成約率取得
    conversion_rates = scenario.get_conversion_rates()

    # 月次予測データ
    forecast_data = []

    for i in range(months):
        target_date = today + relativedelta(months=i)
        year = target_date.year
        month = target_date.month

        # 基準売上（過去平均）
        base_revenue = avg_revenue

        # 季節性調整
        if scenario.seasonality_enabled:
            base_revenue *= seasonal_index.get(month, Decimal('1.0'))

        # パイプラインからの期待売上（初月のみ）
        pipeline_revenue = Decimal('0')
        if i == 0:  # 初月のみパイプライン考慮
            neta_expected = pipeline['neta']['total_value'] * conversion_rates['ネタ']
            waiting_expected = pipeline['waiting']['total_value'] * conversion_rates['施工日待ち']
            pipeline_revenue = neta_expected + waiting_expected

        # 最悪・通常・最良シナリオ
        if scenario.scenario_type == 'worst':
            multiplier = Decimal('0.7')  # 最悪: 70%
        elif scenario.scenario_type == 'best':
            multiplier = Decimal('1.3')  # 最良: 130%
        else:
            multiplier = Decimal('1.0')  # 通常: 100%

        forecast_revenue = (base_revenue + pipeline_revenue) * multiplier

        forecast_data.append({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'revenue': float(forecast_revenue),
            'base_revenue': float(base_revenue),
            'pipeline_revenue': float(pipeline_revenue),
            'seasonal_factor': float(seasonal_index.get(month, Decimal('1.0')))
        })

    return forecast_data


# ====================
# 4. 損益予測計算
# ====================

def generate_profit_forecast(scenario, revenue_forecast):
    """
    損益予測を生成

    Args:
        scenario: ForecastScenario インスタンス
        revenue_forecast: 売上予測データ

    Returns:
        list: 月次損益予測データ
    """
    # 固定費取得
    monthly_fixed_costs = FixedCost.objects.filter(
        is_active=True
    ).aggregate(
        total=Sum('monthly_amount')
    )['total'] or Decimal('0')

    monthly_fixed_costs *= scenario.fixed_cost_multiplier

    # 過去の変動費平均
    today = date.today()
    past_3_months = today - relativedelta(months=3)
    avg_variable_costs = VariableCost.objects.filter(
        incurred_date__gte=past_3_months
    ).aggregate(
        avg=Avg('amount')
    )['avg'] or Decimal('0')

    avg_variable_costs *= scenario.variable_cost_multiplier

    # 損益計算
    profit_data = []

    for month_data in revenue_forecast:
        revenue = Decimal(str(month_data['revenue']))

        # 原価計算
        cost_of_sales = revenue * (scenario.cost_rate / Decimal('100'))

        # 粗利益
        gross_profit = revenue - cost_of_sales

        # 営業利益
        operating_profit = gross_profit - monthly_fixed_costs - avg_variable_costs

        # 利益率
        profit_margin = (operating_profit / revenue * 100) if revenue > 0 else Decimal('0')

        profit_data.append({
            'year': month_data['year'],
            'month': month_data['month'],
            'month_name': month_data['month_name'],
            'revenue': float(revenue),
            'cost_of_sales': float(cost_of_sales),
            'gross_profit': float(gross_profit),
            'fixed_costs': float(monthly_fixed_costs),
            'variable_costs': float(avg_variable_costs),
            'operating_profit': float(operating_profit),
            'profit_margin': float(profit_margin)
        })

    return profit_data


# ====================
# 5. キャッシュフロー予測
# ====================

def generate_cashflow_forecast(scenario, months=None):
    """
    キャッシュフロー予測を生成

    Args:
        scenario: ForecastScenario インスタンス
        months: 予測月数

    Returns:
        list: 月次キャッシュフロー予測データ
    """
    if months is None:
        months = scenario.forecast_months

    # 売上予測取得
    revenue_forecast = generate_revenue_forecast(scenario, months)

    # キャッシュフロー計算（簡易版）
    # 実際には入金サイト・支払サイトを考慮
    cashflow_data = []

    for month_data in revenue_forecast:
        revenue = Decimal(str(month_data['revenue']))

        # 入金（売上の90%が当月入金と仮定）
        cash_inflow = revenue * Decimal('0.9')

        # 出金（原価 + 経費）
        cost_rate = scenario.cost_rate / Decimal('100')
        cash_outflow = revenue * cost_rate

        # ネットキャッシュフロー
        net_cashflow = cash_inflow - cash_outflow

        cashflow_data.append({
            'year': month_data['year'],
            'month': month_data['month'],
            'month_name': month_data['month_name'],
            'cash_inflow': float(cash_inflow),
            'cash_outflow': float(cash_outflow),
            'net_cashflow': float(net_cashflow)
        })

    return cashflow_data


# ====================
# 6. 統合予測生成
# ====================

def generate_full_forecast(scenario):
    """
    完全な予測を生成してシナリオに保存

    Args:
        scenario: ForecastScenario インスタンス

    Returns:
        dict: 完全な予測データ
    """
    months = scenario.forecast_months

    # 各種予測生成
    revenue_forecast = generate_revenue_forecast(scenario, months)
    profit_forecast = generate_profit_forecast(scenario, revenue_forecast)
    cashflow_forecast = generate_cashflow_forecast(scenario, months)

    # パイプライン分析
    pipeline = analyze_pipeline()

    # 過去実績
    historical = analyze_historical_performance(months=12)

    # サマリー計算
    total_revenue = sum(Decimal(str(m['revenue'])) for m in revenue_forecast)
    total_profit = sum(Decimal(str(m['operating_profit'])) for m in profit_forecast)
    avg_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')

    # 統合データ
    full_forecast = {
        'scenario_id': scenario.id,
        'scenario_name': scenario.name,
        'generated_at': datetime.now().isoformat(),
        'forecast_months': months,

        # サマリー
        'total_revenue': float(total_revenue),
        'total_profit': float(total_profit),
        'profit_margin': float(avg_profit_margin),

        # 月次データ
        'monthly_revenue': revenue_forecast,
        'monthly_profit': profit_forecast,
        'monthly_cashflow': cashflow_forecast,

        # パイプライン
        'pipeline': {
            'neta_count': pipeline['neta']['count'],
            'neta_value': float(pipeline['neta']['total_value']),
            'waiting_count': pipeline['waiting']['count'],
            'waiting_value': float(pipeline['waiting']['total_value']),
            'total_value': float(pipeline['total_pipeline_value'])
        },

        # 過去実績
        'historical': {
            'avg_revenue': float(historical['avg_revenue']),
            'avg_order_amount': float(historical['avg_order_amount']),
            'completion_rate': float(historical['completion_rate'])
        }
    }

    return full_forecast


# ====================
# 7. シナリオ比較
# ====================

def compare_scenarios(scenario_ids):
    """
    複数シナリオを比較

    Args:
        scenario_ids: ForecastScenarioのIDリスト

    Returns:
        dict: 比較データ
    """
    scenarios = ForecastScenario.objects.filter(id__in=scenario_ids)

    comparison_data = {
        'scenarios': [],
        'comparison_table': [],
        'chart_data': {
            'labels': [],
            'datasets': []
        }
    }

    for scenario in scenarios:
        # 予測結果がなければ計算
        if not scenario.forecast_results:
            scenario.calculate_forecast()
            scenario.refresh_from_db()

        results = scenario.forecast_results

        comparison_data['scenarios'].append({
            'id': scenario.id,
            'name': scenario.name,
            'type': scenario.scenario_type,
            'total_revenue': results.get('total_revenue', 0),
            'total_profit': results.get('total_profit', 0),
            'profit_margin': results.get('profit_margin', 0)
        })

        # チャート用データ
        monthly_revenue = results.get('monthly_revenue', [])
        comparison_data['chart_data']['datasets'].append({
            'label': scenario.name,
            'data': [m['revenue'] for m in monthly_revenue]
        })

    # ラベル（月）
    if scenarios.exists():
        first_scenario = scenarios.first()
        monthly_revenue = first_scenario.forecast_results.get('monthly_revenue', [])
        comparison_data['chart_data']['labels'] = [
            f"{m['year']}/{m['month']}" for m in monthly_revenue
        ]

    return comparison_data
