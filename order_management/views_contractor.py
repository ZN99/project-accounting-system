"""業者管理ビュー"""
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from .models import Project
from subcontract_management.models import Contractor


class ContractorDashboardView(LoginRequiredMixin, TemplateView):
    """業者ダッシュボード"""
    template_name = 'order_management/contractor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contractors'] = Contractor.objects.all().order_by('name')
        return context


class ContractorProjectsView(LoginRequiredMixin, TemplateView):
    """業者別案件一覧"""
    template_name = 'order_management/contractor_projects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor_id = self.kwargs.get('contractor_id')
        contractor = get_object_or_404(Contractor, id=contractor_id)

        # この業者が担当している案件を取得
        projects = Project.objects.filter(
            subcontracts__contractor=contractor
        ).distinct().order_by('-created_at')

        context['contractor'] = contractor
        context['projects'] = projects
        return context


class ContractorEditView(LoginRequiredMixin, UpdateView):
    """業者編集"""
    model = Contractor
    template_name = 'order_management/contractor_edit.html'
    fields = ['name', 'contractor_type', 'address', 'phone', 'email', 'contact_person', 'hourly_rate', 'specialties', 'is_active']
    success_url = reverse_lazy('order_management:contractor_dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # フォームフィールドにBootstrapクラスを追加
        form.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: ○○建設株式会社'
        })
        form.fields['contractor_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 東京都渋谷区...'
        })
        form.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 03-1234-5678'
        })
        form.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: info@example.com'
        })
        form.fields['contact_person'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 山田 太郎'
        })
        form.fields['hourly_rate'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '3000',
            'min': '0',
            'step': '100'
        })
        form.fields['specialties'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 建築工事、内装工事'
        })
        form.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input'
        })

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
