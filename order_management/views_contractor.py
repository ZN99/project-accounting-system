"""業者管理ビュー"""
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from .models import Contractor, Project


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
    fields = ['name', 'specialty', 'phone', 'email', 'address']
    success_url = reverse_lazy('order_management:contractor_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
