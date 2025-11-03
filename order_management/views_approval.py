from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q
from .models import ApprovalLog, Project, Notification
from .forms import ApprovalRequestForm, ApprovalActionForm
from .user_roles import has_role, UserRole


class ApprovalListView(LoginRequiredMixin, ListView):
    """承認リスト表示 - Phase 8"""
    model = ApprovalLog
    template_name = 'order_management/approval/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = ApprovalLog.objects.select_related(
            'project', 'requester', 'approver'
        ).order_by('-requested_at')

        # 役割に応じてフィルタリング
        view_type = self.request.GET.get('view', 'pending')

        if view_type == 'my_requests':
            # 自分が申請したもの
            queryset = queryset.filter(requester=user)
        elif view_type == 'pending':
            # 承認待ちのもの（役員のみ）
            if has_role(user, UserRole.EXECUTIVE):
                queryset = queryset.filter(status='pending')
            else:
                # 役員以外は自分が申請したものだけ
                queryset = queryset.filter(requester=user, status='pending')
        elif view_type == 'approved':
            queryset = queryset.filter(status='approved')
        elif view_type == 'rejected':
            queryset = queryset.filter(status='rejected')

        # 承認種別でフィルタ
        approval_type = self.request.GET.get('approval_type')
        if approval_type:
            queryset = queryset.filter(approval_type=approval_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_type'] = self.request.GET.get('view', 'pending')
        context['approval_type_filter'] = self.request.GET.get('approval_type', '')

        # 統計
        context['pending_count'] = ApprovalLog.objects.filter(status='pending').count()
        context['my_requests_count'] = ApprovalLog.objects.filter(requester=self.request.user).count()

        # 役員かどうか
        context['is_executive'] = has_role(self.request.user, UserRole.EXECUTIVE)

        return context


class ApprovalDetailView(LoginRequiredMixin, DetailView):
    """承認詳細表示 - Phase 8"""
    model = ApprovalLog
    template_name = 'order_management/approval/approval_detail.html'
    context_object_name = 'approval'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        approval = self.get_object()

        # 役員かつ承認待ちの場合、アクションフォームを表示
        if has_role(self.request.user, UserRole.EXECUTIVE) and approval.status == 'pending':
            context['action_form'] = ApprovalActionForm()
            context['can_approve'] = True
        else:
            context['can_approve'] = False

        return context


class ApprovalRequestView(LoginRequiredMixin, CreateView):
    """承認申請 - Phase 8"""
    model = ApprovalLog
    form_class = ApprovalRequestForm
    template_name = 'order_management/approval/approval_request_form.html'

    def dispatch(self, request, *args, **kwargs):
        # プロジェクトを取得
        self.project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.save(commit=False)
        approval.project = self.project
        approval.requester = self.request.user
        approval.status = 'pending'
        approval.save()

        # プロジェクトのステータス更新
        if approval.approval_type in ['estimate', 'project_start']:
            self.project.approval_status = 'pending'
            self.project.save()

        # 役員に通知
        from django.contrib.auth import get_user_model
        User = get_user_model()
        executives = User.objects.filter(userprofile__role='EXECUTIVE')

        for exec_user in executives:
            Notification.objects.create(
                user=exec_user,
                notification_type='approval_request',
                title='承認申請',
                message=f'{self.request.user.get_full_name() or self.request.user.username}さんから承認申請があります: {approval.get_approval_type_display()}',
                related_project=self.project
            )

        messages.success(self.request, '承認申請を送信しました。')
        return redirect('order_management:project_detail', pk=self.project.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context

    def get_success_url(self):
        return reverse('order_management:project_detail', kwargs={'pk': self.project.pk})


@login_required
def approval_action(request, pk):
    """承認処理（承認/却下）- Phase 8"""
    approval = get_object_or_404(ApprovalLog, pk=pk)

    # 役員チェック
    if not has_role(request.user, UserRole.EXECUTIVE):
        messages.error(request, '承認権限がありません。')
        return redirect('order_management:approval_detail', pk=pk)

    # 既に処理済みチェック
    if approval.status != 'pending':
        messages.error(request, 'この承認は既に処理されています。')
        return redirect('order_management:approval_detail', pk=pk)

    if request.method == 'POST':
        form = ApprovalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            approval_comment = form.cleaned_data['approval_comment']
            rejection_reason = form.cleaned_data['rejection_reason']

            approval.approver = request.user
            approval.approved_at = timezone.now()

            if action == 'approve':
                approval.status = 'approved'
                approval.approval_comment = approval_comment

                # プロジェクトのステータス更新
                if approval.approval_type in ['estimate', 'project_start']:
                    approval.project.approval_status = 'approved'
                    approval.project.approved_by = request.user
                    approval.project.approved_at = timezone.now()
                    approval.project.save()

                messages.success(request, '承認しました。')
                notification_message = f'承認申請が承認されました: {approval.get_approval_type_display()}'
            else:
                approval.status = 'rejected'
                approval.rejection_reason = rejection_reason

                # プロジェクトのステータス更新
                if approval.approval_type in ['estimate', 'project_start']:
                    approval.project.approval_status = 'rejected'
                    approval.project.save()

                messages.success(request, '却下しました。')
                notification_message = f'承認申請が却下されました: {approval.get_approval_type_display()}\n理由: {rejection_reason}'

            approval.save()

            # 申請者に通知
            if approval.requester:
                Notification.objects.create(
                    user=approval.requester,
                    notification_type='approval_response',
                    title=f'承認申請: {approval.get_status_display()}',
                    message=notification_message,
                    related_project=approval.project
                )

            return redirect('order_management:approval_detail', pk=pk)
    else:
        form = ApprovalActionForm()

    return render(request, 'order_management/approval/approval_action.html', {
        'approval': approval,
        'form': form
    })
