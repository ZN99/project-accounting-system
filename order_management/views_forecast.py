"""
売上予測・収支シミュレーション ビュー - Phase 2
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import json

from .models import ForecastScenario
from .forecast_utils import (
    analyze_historical_performance,
    analyze_pipeline,
    generate_full_forecast,
    compare_scenarios
)


class ForecastDashboardView(LoginRequiredMixin, TemplateView):
    """売上予測ダッシュボード"""
    template_name = 'order_management/forecast_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # デフォルトシナリオ取得
        default_scenario = ForecastScenario.objects.filter(
            is_active=True,
            is_default=True
        ).first()

        # なければ最初のアクティブシナリオ
        if not default_scenario:
            default_scenario = ForecastScenario.objects.filter(
                is_active=True
            ).first()

        # シナリオIDが指定されていればそれを使用
        scenario_id = self.request.GET.get('scenario_id')
        if scenario_id:
            try:
                selected_scenario = ForecastScenario.objects.get(
                    id=scenario_id,
                    is_active=True
                )
            except ForecastScenario.DoesNotExist:
                selected_scenario = default_scenario
        else:
            selected_scenario = default_scenario

        # 予測データ取得
        if selected_scenario:
            # 予測結果がなければ計算
            if not selected_scenario.forecast_results:
                selected_scenario.calculate_forecast()
                selected_scenario.refresh_from_db()

            forecast_data = selected_scenario.forecast_results
            summary = selected_scenario.get_summary()

            # 月平均を計算
            if summary and selected_scenario.forecast_months > 0:
                summary['avg_monthly_revenue'] = float(summary['total_revenue']) / selected_scenario.forecast_months
                summary['avg_monthly_profit'] = float(summary['total_profit']) / selected_scenario.forecast_months
            else:
                summary['avg_monthly_revenue'] = 0
                summary['avg_monthly_profit'] = 0
        else:
            forecast_data = None
            summary = None

        # 過去実績分析
        historical = analyze_historical_performance(months=12)

        # パイプライン分析
        pipeline = analyze_pipeline()

        # 全シナリオ一覧
        all_scenarios = ForecastScenario.objects.filter(is_active=True)

        # チャートデータ準備
        chart_data = self.prepare_chart_data(forecast_data) if forecast_data else None

        context.update({
            'selected_scenario': selected_scenario,
            'forecast_data': forecast_data,
            'summary': summary,
            'historical': historical,
            'pipeline': pipeline,
            'all_scenarios': all_scenarios,
            'chart_data': chart_data
        })

        return context

    def prepare_chart_data(self, forecast_data):
        """チャート用データを準備"""
        monthly_revenue = forecast_data.get('monthly_revenue', [])
        monthly_profit = forecast_data.get('monthly_profit', [])

        return {
            'labels': [f"{m['month_name'][:3]} {m['year']}" for m in monthly_revenue],
            'revenue': [m['revenue'] for m in monthly_revenue],
            'profit': [m['operating_profit'] for m in monthly_profit],
            'revenue_data': monthly_revenue,
            'profit_data': monthly_profit
        }


class ScenarioListView(LoginRequiredMixin, ListView):
    """シナリオ一覧"""
    model = ForecastScenario
    template_name = 'order_management/scenario_list.html'
    context_object_name = 'scenarios'
    paginate_by = 20

    def get_queryset(self):
        return ForecastScenario.objects.filter(is_active=True).order_by('-created_at')


class ScenarioCreateView(LoginRequiredMixin, CreateView):
    """シナリオ作成"""
    model = ForecastScenario
    template_name = 'order_management/scenario_form.html'
    fields = [
        'name', 'description', 'scenario_type',
        'conversion_rate_neta', 'conversion_rate_waiting',
        'cost_rate', 'fixed_cost_multiplier', 'variable_cost_multiplier',
        'forecast_months', 'seasonality_enabled', 'is_default'
    ]
    success_url = reverse_lazy('order_management:forecast_dashboard')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        # 予測を自動計算
        self.object.calculate_forecast()

        messages.success(self.request, f'シナリオ「{self.object.name}」を作成しました')
        return response


class ScenarioUpdateView(LoginRequiredMixin, UpdateView):
    """シナリオ更新"""
    model = ForecastScenario
    template_name = 'order_management/scenario_form.html'
    fields = [
        'name', 'description', 'scenario_type',
        'conversion_rate_neta', 'conversion_rate_waiting',
        'cost_rate', 'fixed_cost_multiplier', 'variable_cost_multiplier',
        'forecast_months', 'seasonality_enabled', 'is_default', 'is_active'
    ]
    success_url = reverse_lazy('order_management:forecast_dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)

        # 予測を再計算
        self.object.calculate_forecast()

        messages.success(self.request, f'シナリオ「{self.object.name}」を更新しました')
        return response


class ScenarioDeleteView(LoginRequiredMixin, DeleteView):
    """シナリオ削除"""
    model = ForecastScenario
    template_name = 'order_management/scenario_confirm_delete.html'
    success_url = reverse_lazy('order_management:forecast_dashboard')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_message = f'シナリオ「{self.object.name}」を削除しました'
        response = super().delete(request, *args, **kwargs)
        messages.success(request, success_message)
        return response


class ScenarioCompareView(LoginRequiredMixin, TemplateView):
    """シナリオ比較"""
    template_name = 'order_management/scenario_compare.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 比較するシナリオIDを取得（最大3つ）
        scenario_ids = self.request.GET.getlist('scenario_ids')

        if not scenario_ids:
            # デフォルトで最悪・通常・最良を比較
            scenarios = ForecastScenario.objects.filter(
                is_active=True,
                scenario_type__in=['worst', 'normal', 'best']
            ).order_by('scenario_type')[:3]
            scenario_ids = [s.id for s in scenarios]

        # 比較データ生成
        if scenario_ids:
            comparison_data = compare_scenarios(scenario_ids)
        else:
            comparison_data = None

        # 全シナリオ一覧（選択用）
        all_scenarios = ForecastScenario.objects.filter(is_active=True)

        context.update({
            'comparison_data': comparison_data,
            'all_scenarios': all_scenarios,
            'selected_scenario_ids': [int(id) for id in scenario_ids]
        })

        return context


# ====================
# API Endpoints
# ====================

@login_required
@require_http_methods(["GET"])
def scenario_calculate_api(request, scenario_id):
    """シナリオ予測再計算API"""
    try:
        scenario = get_object_or_404(ForecastScenario, id=scenario_id)
        scenario.calculate_forecast()

        return JsonResponse({
            'success': True,
            'message': '予測を再計算しました',
            'forecast_data': scenario.forecast_results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def forecast_preview_api(request):
    """予測プレビューAPI（シナリオ作成時のリアルタイムプレビュー用）"""
    try:
        # パラメータ取得
        conversion_rate_neta = Decimal(request.GET.get('conversion_rate_neta', '30'))
        conversion_rate_waiting = Decimal(request.GET.get('conversion_rate_waiting', '80'))
        cost_rate = Decimal(request.GET.get('cost_rate', '75'))
        forecast_months = int(request.GET.get('forecast_months', '12'))
        scenario_type = request.GET.get('scenario_type', 'custom')

        # 一時シナリオ作成（保存しない）
        temp_scenario = ForecastScenario(
            name='Preview',
            scenario_type=scenario_type,
            conversion_rate_neta=conversion_rate_neta,
            conversion_rate_waiting=conversion_rate_waiting,
            cost_rate=cost_rate,
            forecast_months=forecast_months
        )

        # 予測生成
        forecast_data = generate_full_forecast(temp_scenario)

        return JsonResponse({
            'success': True,
            'forecast_data': forecast_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def scenario_compare_api(request):
    """シナリオ比較API"""
    try:
        data = json.loads(request.body)
        scenario_ids = data.get('scenario_ids', [])

        if not scenario_ids:
            return JsonResponse({
                'success': False,
                'error': 'シナリオIDが指定されていません'
            }, status=400)

        comparison_data = compare_scenarios(scenario_ids)

        return JsonResponse({
            'success': True,
            'comparison_data': comparison_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def pipeline_analysis_api(request):
    """パイプライン分析API"""
    try:
        pipeline = analyze_pipeline()

        return JsonResponse({
            'success': True,
            'pipeline': {
                'neta_count': pipeline['neta']['count'],
                'neta_value': float(pipeline['neta']['total_value']),
                'waiting_count': pipeline['waiting']['count'],
                'waiting_value': float(pipeline['waiting']['total_value']),
                'total_value': float(pipeline['total_pipeline_value'])
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def historical_analysis_api(request):
    """過去実績分析API"""
    try:
        months = int(request.GET.get('months', '12'))
        historical = analyze_historical_performance(months=months)

        return JsonResponse({
            'success': True,
            'historical': {
                'avg_revenue': float(historical['avg_revenue']),
                'avg_order_amount': float(historical['avg_order_amount']),
                'total_projects': historical['total_projects'],
                'completed_projects': historical['completed_projects'],
                'completion_rate': float(historical['completion_rate']),
                'monthly_revenue': historical['monthly_revenue']
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# 季節性指数管理
# =============================================================================

class SeasonalityEditView(LoginRequiredMixin, TemplateView):
    """季節性指数編集画面"""
    template_name = 'order_management/seasonality_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        scenario_id = kwargs.get('pk')
        scenario = get_object_or_404(ForecastScenario, id=scenario_id)

        # 季節性指数を取得または作成
        from .models import SeasonalityIndex
        seasonality, created = SeasonalityIndex.objects.get_or_create(
            forecast_scenario=scenario
        )

        # 月データを準備
        month_names = [
            '1月', '2月', '3月', '4月', '5月', '6月',
            '7月', '8月', '9月', '10月', '11月', '12月'
        ]

        months = []
        for i in range(1, 13):
            index = seasonality.get_index_for_month(i)
            months.append({
                'number': i,
                'name': month_names[i-1],
                'index': float(index),
                'percent': int(float(index) * 100)
            })

        context['scenario'] = scenario
        context['seasonality'] = seasonality
        context['months'] = months

        return context

    def post(self, request, *args, **kwargs):
        """季節性指数を保存"""
        from decimal import Decimal, InvalidOperation
        from .models import SeasonalityIndex
        from django.contrib import messages

        scenario_id = kwargs.get('pk')
        scenario = get_object_or_404(ForecastScenario, id=scenario_id)

        seasonality, created = SeasonalityIndex.objects.get_or_create(
            forecast_scenario=scenario
        )

        # 各月の指数を保存
        for month in range(1, 13):
            field_name = f'month_{month}'
            if field_name in request.POST:
                try:
                    value = Decimal(request.POST[field_name])
                    # バリデーション
                    if value < Decimal('0.00') or value > Decimal('3.00'):
                        messages.error(request, f'{month}月の指数は0.00〜3.00の範囲で入力してください')
                        return self.get(request, *args, **kwargs)
                    seasonality.set_index_for_month(month, value)
                except (ValueError, InvalidOperation):
                    messages.error(request, f'{month}月の指数が不正です')
                    return self.get(request, *args, **kwargs)

        seasonality.use_auto_calculation = False  # 手動設定に切り替え
        seasonality.save()

        # 予測を再計算
        scenario.calculate_forecast()

        messages.success(request, '季節性指数を保存し、予測を再計算しました')
        return redirect('order_management:scenario_update', pk=scenario.id)


@login_required
@require_http_methods(["POST"])
def seasonality_calculate_api(request, scenario_id):
    """過去データから季節性指数を自動計算するAPI"""
    from .models import SeasonalityIndex

    try:
        scenario = get_object_or_404(ForecastScenario, id=scenario_id)

        seasonality, created = SeasonalityIndex.objects.get_or_create(
            forecast_scenario=scenario
        )

        # 過去データから計算
        seasonality.calculate_from_historical_data()

        # 計算結果を返す
        seasonal_factors = {}
        for month in range(1, 13):
            seasonal_factors[month] = float(seasonality.get_index_for_month(month))

        return JsonResponse({
            'success': True,
            'seasonal_factors': seasonal_factors
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
