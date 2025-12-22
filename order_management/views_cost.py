from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import FixedCost, VariableCost, Project
from .forms import FixedCostForm, VariableCostForm, FixedCostFilterForm, VariableCostFilterForm
from .user_roles import has_role, UserRole, executive_required
from .mixins import PerPageMixin


class FixedCostListView(LoginRequiredMixin, PerPageMixin, ListView):
    """固定費一覧表示"""
    model = FixedCost
    template_name = 'order_management/cost/fixed_cost_list.html'
    context_object_name = 'fixed_costs'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("固定費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = FixedCost.objects.all().order_by('-created_at')

        # フィルタリング
        cost_type = self.request.GET.get('cost_type')
        is_active = self.request.GET.get('is_active')

        if cost_type:
            queryset = queryset.filter(cost_type=cost_type)

        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = FixedCostFilterForm(self.request.GET)

        # 統計情報
        queryset = self.get_queryset()
        context['total_active_costs'] = queryset.filter(is_active=True).count()
        total_monthly = sum(
            fc.monthly_amount for fc in queryset.filter(is_active=True)
        )
        context['total_monthly_amount'] = total_monthly
        context['total_yearly_amount'] = total_monthly * 12

        return context


class FixedCostCreateView(LoginRequiredMixin, CreateView):
    """固定費新規作成"""
    model = FixedCost
    form_class = FixedCostForm
    template_name = 'order_management/cost/fixed_cost_form.html'
    success_url = reverse_lazy('order_management:fixed_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("固定費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'固定費「{form.instance.name}」を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '固定費新規登録'
        context['submit_text'] = '登録する'
        return context


class FixedCostUpdateView(LoginRequiredMixin, UpdateView):
    """固定費編集"""
    model = FixedCost
    form_class = FixedCostForm
    template_name = 'order_management/cost/fixed_cost_form.html'
    success_url = reverse_lazy('order_management:fixed_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("固定費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'固定費「{form.instance.name}」を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '固定費編集'
        context['submit_text'] = '更新する'
        return context


class FixedCostDeleteView(LoginRequiredMixin, DeleteView):
    """固定費削除"""
    model = FixedCost
    template_name = 'order_management/cost/fixed_cost_confirm_delete.html'
    success_url = reverse_lazy('order_management:fixed_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("固定費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 年額を計算してコンテキストに追加
        context['yearly_amount'] = self.object.monthly_amount * 12
        return context

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'固定費「{obj.name}」を削除しました。')
        return super().delete(request, *args, **kwargs)


class VariableCostListView(LoginRequiredMixin, PerPageMixin, ListView):
    """変動費一覧表示"""
    model = VariableCost
    template_name = 'order_management/cost/variable_cost_list.html'
    context_object_name = 'variable_costs'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("変動費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VariableCost.objects.select_related('project').order_by('-incurred_date')

        # フィルタリング
        cost_type = self.request.GET.get('cost_type')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        project_id = self.request.GET.get('project')

        if cost_type:
            queryset = queryset.filter(cost_type=cost_type)

        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(incurred_date__gte=start_date_obj)
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(incurred_date__lte=end_date_obj)
            except ValueError:
                pass

        if project_id:
            try:
                queryset = queryset.filter(project_id=int(project_id))
            except (ValueError, TypeError):
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = VariableCostFilterForm(self.request.GET)

        # 統計情報
        queryset = self.get_queryset()
        context['total_costs'] = queryset.count()
        context['total_amount'] = sum(vc.amount for vc in queryset)

        # 今月の統計
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (this_month_start + timedelta(days=32)).replace(day=1)
        this_month_costs = queryset.filter(
            incurred_date__gte=this_month_start.date(),
            incurred_date__lt=next_month.date()
        )
        context['this_month_amount'] = sum(vc.amount for vc in this_month_costs)

        return context


class VariableCostCreateView(LoginRequiredMixin, CreateView):
    """変動費新規作成"""
    model = VariableCost
    form_class = VariableCostForm
    template_name = 'order_management/cost/variable_cost_form.html'
    success_url = reverse_lazy('order_management:variable_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("変動費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'変動費「{form.instance.name}」を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '変動費新規登録'
        context['submit_text'] = '登録する'
        return context


class VariableCostUpdateView(LoginRequiredMixin, UpdateView):
    """変動費編集"""
    model = VariableCost
    form_class = VariableCostForm
    template_name = 'order_management/cost/variable_cost_form.html'
    success_url = reverse_lazy('order_management:variable_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("変動費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'変動費「{form.instance.name}」を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '変動費編集'
        context['submit_text'] = '更新する'
        return context


class VariableCostDeleteView(LoginRequiredMixin, DeleteView):
    """変動費削除"""
    model = VariableCost
    template_name = 'order_management/cost/variable_cost_confirm_delete.html'
    success_url = reverse_lazy('order_management:variable_cost_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("変動費情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'変動費「{obj.name}」を削除しました。')
        return super().delete(request, *args, **kwargs)


@executive_required
def cost_dashboard(request):
    """コスト管理ダッシュボード"""
    now = timezone.now()
    current_month = now.month
    current_year = now.year

    # 固定費統計
    active_fixed_costs = FixedCost.objects.filter(is_active=True)
    total_monthly_fixed = sum(fc.monthly_amount for fc in active_fixed_costs)

    # 今月の変動費統計
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (this_month_start + timedelta(days=32)).replace(day=1)
    this_month_variable = VariableCost.objects.filter(
        incurred_date__gte=this_month_start.date(),
        incurred_date__lt=next_month.date()
    )
    total_this_month_variable = sum(vc.amount for vc in this_month_variable)

    # 年度累計変動費（4月開始）
    if current_month >= 4:
        fiscal_year_start = datetime(current_year, 4, 1).date()
    else:
        fiscal_year_start = datetime(current_year - 1, 4, 1).date()

    ytd_variable = VariableCost.objects.filter(incurred_date__gte=fiscal_year_start)
    total_ytd_variable = sum(vc.amount for vc in ytd_variable)

    # 最近の変動費
    recent_variable_costs = VariableCost.objects.select_related('project').order_by('-created_at')[:10]

    context = {
        'current_month': current_month,
        'current_year': current_year,
        'total_monthly_fixed': total_monthly_fixed,
        'active_fixed_costs_count': active_fixed_costs.count(),
        'total_this_month_variable': total_this_month_variable,
        'this_month_variable_count': this_month_variable.count(),
        'total_ytd_variable': total_ytd_variable,
        'ytd_variable_count': ytd_variable.count(),
        'recent_variable_costs': recent_variable_costs,
        'total_monthly_cost': total_monthly_fixed + total_this_month_variable,
    }

    return render(request, 'order_management/cost/cost_dashboard.html', context)