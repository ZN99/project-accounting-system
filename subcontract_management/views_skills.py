from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q, Avg, Count
from .models import Contractor
from order_management.models import ContractorReview
from .mixins import PerPageMixin


class ContractorSkillsDashboardView(LoginRequiredMixin, PerPageMixin, ListView):
    """職人スキル管理ダッシュボード - Phase 8"""
    model = Contractor
    template_name = 'subcontract_management/contractor_skills_dashboard.html'
    context_object_name = 'contractors'
    paginate_by = 20

    def get_queryset(self):
        queryset = Contractor.objects.annotate(
            review_count=Count('reviews')
        ).order_by('-trust_level', '-average_rating', 'name')

        # フィルタリング
        skill_level = self.request.GET.get('skill_level')
        trust_level = self.request.GET.get('trust_level')
        search = self.request.GET.get('search')
        is_active = self.request.GET.get('is_active')

        if skill_level:
            queryset = queryset.filter(skill_level=skill_level)

        if trust_level:
            queryset = queryset.filter(trust_level__gte=int(trust_level))

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(specialties__icontains=search) |
                Q(certifications__icontains=search)
            )

        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 統計情報
        all_contractors = Contractor.objects.all()
        context['total_contractors'] = all_contractors.count()
        context['high_trust_contractors'] = all_contractors.filter(trust_level__gte=4).count()
        context['expert_contractors'] = all_contractors.filter(skill_level='expert').count()

        # 平均評価
        avg_rating = all_contractors.aggregate(avg=Avg('average_rating'))['avg']
        context['avg_rating'] = round(avg_rating, 2) if avg_rating else 0

        # フィルタパラメータを保持
        context['current_skill_level'] = self.request.GET.get('skill_level', '')
        context['current_trust_level'] = self.request.GET.get('trust_level', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_is_active'] = self.request.GET.get('is_active', '')

        # 選択肢
        context['skill_level_choices'] = Contractor._meta.get_field('skill_level').choices
        context['trust_levels'] = range(1, 6)

        return context


class ContractorSkillsDetailView(LoginRequiredMixin, DetailView):
    """職人スキル詳細表示 - Phase 8"""
    model = Contractor
    template_name = 'subcontract_management/contractor_skills_detail.html'
    context_object_name = 'contractor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        contractor = self.get_object()

        # 評価履歴
        reviews = ContractorReview.objects.filter(
            contractor=contractor
        ).select_related('project', 'reviewed_by').order_by('-reviewed_at')[:10]

        context['reviews'] = reviews
        context['total_reviews'] = contractor.reviews.count()

        # 評価統計
        if contractor.reviews.exists():
            context['avg_quality'] = contractor.reviews.aggregate(avg=Avg('quality_score'))['avg']
            context['avg_speed'] = contractor.reviews.aggregate(avg=Avg('speed_score'))['avg']
            context['avg_communication'] = contractor.reviews.aggregate(avg=Avg('communication_score'))['avg']
        else:
            context['avg_quality'] = 0
            context['avg_speed'] = 0
            context['avg_communication'] = 0

        # 最近の案件
        from order_management.models import Project
        from .models import Subcontract

        recent_projects = Subcontract.objects.filter(
            contractor=contractor
        ).select_related('project').order_by('-created_at')[:10]

        context['recent_projects'] = recent_projects

        return context
