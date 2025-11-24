from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import ClientCompany, Project
from .forms import ClientCompanyForm, ClientCompanyFilterForm
from .user_roles import has_role, UserRole


class ClientCompanyListView(LoginRequiredMixin, ListView):
    """元請会社一覧表示 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_list.html'
    context_object_name = 'client_companies'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ClientCompany.objects.annotate(
            project_count=Count('projects')
        ).order_by('-created_at')

        # フィルタリング
        is_active = self.request.GET.get('is_active')
        search = self.request.GET.get('search')

        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(contact_person__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ClientCompanyFilterForm(self.request.GET)

        # 統計情報
        context['total_companies'] = ClientCompany.objects.count()
        context['active_companies'] = ClientCompany.objects.filter(is_active=True).count()

        return context


class ClientCompanyDetailView(LoginRequiredMixin, DetailView):
    """元請会社詳細表示 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_detail.html'
    context_object_name = 'company'

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 関連案件
        company = self.get_object()
        context['recent_projects'] = company.projects.all().order_by('-created_at')[:10]
        context['total_projects'] = company.projects.count()
        context['active_projects'] = company.projects.exclude(project_status='完工').count()

        return context


class ClientCompanyCreateView(LoginRequiredMixin, CreateView):
    """元請会社新規登録 - Phase 8"""
    model = ClientCompany
    form_class = ClientCompanyForm
    template_name = 'order_management/client_company/client_company_form.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'元請会社「{form.instance.company_name}」を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '元請会社新規登録'
        context['submit_text'] = '登録する'
        return context


class ClientCompanyUpdateView(LoginRequiredMixin, UpdateView):
    """元請会社編集 - Phase 8"""
    model = ClientCompany
    form_class = ClientCompanyForm
    template_name = 'order_management/client_company/client_company_form.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 管理部・役員のみアクセス可能
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
            raise PermissionDenied("元請会社情報へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'元請会社「{form.instance.company_name}」を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = '元請会社編集'
        context['submit_text'] = '更新する'
        return context


class ClientCompanyDeleteView(LoginRequiredMixin, DeleteView):
    """元請会社削除 - Phase 8"""
    model = ClientCompany
    template_name = 'order_management/client_company/client_company_confirm_delete.html'
    success_url = reverse_lazy('order_management:client_company_list')

    def dispatch(self, request, *args, **kwargs):
        # 役員のみアクセス可能（削除は慎重に）
        if not has_role(request.user, UserRole.EXECUTIVE):
            raise PermissionDenied("元請会社の削除権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'元請会社「{obj.company_name}」を削除しました。')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context['related_projects_count'] = company.projects.count()
        return context


@login_required
def client_company_api(request, company_id):
    """元請会社詳細API - Phase 8

    案件登録フォームで元請会社選択時に、
    鍵受け渡し場所などの情報を取得するためのAPI
    """
    try:
        company = ClientCompany.objects.get(pk=company_id, is_active=True)
        return JsonResponse({
            'success': True,
            'data': {
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': company.contact_person,
                'email': company.email,
                'phone': company.phone,
                'default_key_handover_location': company.default_key_handover_location,
                'key_handover_notes': company.key_handover_notes,
                'approval_threshold': float(company.approval_threshold),
                'special_notes': company.special_notes,
            }
        })
    except ClientCompany.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '元請会社が見つかりません'
        }, status=404)


@login_required
def client_company_list_ajax(request):
    """元請会社一覧取得API - AJAX用

    元請管理パネルで最新の元請会社一覧を取得する
    """
    try:
        companies = ClientCompany.objects.all().order_by('-created_at')

        companies_data = []
        for company in companies:
            companies_data.append({
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': company.contact_person or '',
                'email': company.email or '',
                'phone': company.phone or '',
                'address': company.address or '',
                'website': company.website or '',
                'payment_cycle': company.payment_cycle or '',
                'payment_cycle_label': company.get_payment_cycle_display() if company.payment_cycle else '',
                'closing_day': company.closing_day,
                'payment_day': company.payment_day,
                'default_key_handover_location': company.default_key_handover_location or '',
                'key_handover_notes': company.key_handover_notes or '',
                'special_notes': company.special_notes or '',
                'is_active': company.is_active,
                'created_at': company.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(company, 'created_at') else '',
            })

        return JsonResponse({
            'success': True,
            'companies': companies_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def client_company_create_ajax(request):
    """元請会社AJAX作成 - モーダルから作成

    案件登録中に元請会社を作成するためのAJAXエンドポイント
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'POSTリクエストのみ対応しています'
        }, status=405)

    # 権限チェック
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.COORDINATION_DEPT)):
        return JsonResponse({
            'success': False,
            'error': '元請会社の作成権限がありません'
        }, status=403)

    form = ClientCompanyForm(request.POST, request.FILES)

    if form.is_valid():
        company = form.save()

        # ファイルURLを取得
        completion_template_url = ''
        if company.completion_report_template:
            try:
                completion_template_url = company.completion_report_template.url
            except:
                completion_template_url = ''

        # 成功時のレスポンス
        return JsonResponse({
            'success': True,
            'company': {
                'id': company.id,
                'company_name': company.company_name,
                'contact_person': company.contact_person or '',
                'email': company.email or '',
                'phone': company.phone or '',
                'address': company.address or '',
                'website': company.website or '',
                'payment_cycle': company.payment_cycle or '',
                'payment_cycle_display': company.get_payment_cycle_display() if company.payment_cycle else '',
                'closing_day': company.closing_day,
                'payment_day': company.payment_day,
                'default_key_handover_location': company.default_key_handover_location or '',
                'key_handover_notes': company.key_handover_notes or '',
                'completion_report_template_url': completion_template_url,
                'completion_report_notes': company.completion_report_notes or '',
                'special_notes': company.special_notes or '',
                'is_active': company.is_active,
            }
        })
    else:
        # バリデーションエラー
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)
