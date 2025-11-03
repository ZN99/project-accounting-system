from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse
from django.db.models import Avg
from .models import ContractorReview, Project
from .forms import ContractorReviewForm
from subcontract_management.models import Contractor, Subcontract


class ContractorReviewCreateView(LoginRequiredMixin, CreateView):
    """職人評価作成 - Phase 8"""
    model = ContractorReview
    form_class = ContractorReviewForm
    template_name = 'order_management/review/contractor_review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        self.contractor = get_object_or_404(Contractor, pk=self.kwargs['contractor_pk'])

        # 既に評価済みかチェック
        existing_review = ContractorReview.objects.filter(
            project=self.project,
            contractor=self.contractor
        ).first()

        if existing_review:
            messages.warning(request, 'この職人は既に評価済みです。')
            return redirect('order_management:project_detail', pk=self.project.pk)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        review = form.save(commit=False)
        review.project = self.project
        review.contractor = self.contractor
        review.reviewed_by = self.request.user
        review.save()

        # 職人の平均評価を更新
        self._update_contractor_stats()

        messages.success(self.request, f'{self.contractor.name}さんの評価を登録しました。')
        return redirect('order_management:project_detail', pk=self.project.pk)

    def _update_contractor_stats(self):
        """職人の統計情報を更新"""
        contractor = self.contractor

        # 平均評価を計算
        reviews = ContractorReview.objects.filter(contractor=contractor)
        if reviews.exists():
            contractor.average_rating = reviews.aggregate(avg=Avg('overall_rating'))['avg'] or 0

            # 総案件数（ContractorReviewの数をカウント）
            contractor.total_projects = reviews.count()

            # 成功率（would_recommendがTrueの割合）
            recommend_count = reviews.filter(would_recommend=True).count()
            contractor.success_rate = (recommend_count / reviews.count()) * 100 if reviews.count() > 0 else 100

            contractor.save()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['contractor'] = self.contractor
        return context
