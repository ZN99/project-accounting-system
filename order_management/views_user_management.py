from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q

from .models import UserProfile
from .user_roles import UserRole, has_role


class ExecutiveRequiredMixin(UserPassesTestMixin):
    """役員権限必須のMixin"""

    def test_func(self):
        return has_role(self.request.user, UserRole.EXECUTIVE)

    def handle_no_permission(self):
        messages.error(self.request, 'この機能は役員のみアクセス可能です。')
        return redirect('order_management:dashboard')


class UserManagementDashboardView(LoginRequiredMixin, ExecutiveRequiredMixin, ListView):
    """ユーザー管理ダッシュボード"""
    model = User
    template_name = 'order_management/user_management_dashboard.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.select_related('userprofile').order_by('-is_staff', '-is_superuser', 'username')

        # 検索
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        # ロールフィルター
        role_filter = self.request.GET.get('role')
        if role_filter and role_filter != 'all':
            # UserProfileのrolesフィールドに指定されたロールが含まれるユーザーをフィルター
            queryset = queryset.filter(
                userprofile__roles__contains=[role_filter]
            )

        # スタッフフィルター
        staff_filter = self.request.GET.get('staff')
        if staff_filter == 'staff':
            queryset = queryset.filter(is_staff=True)
        elif staff_filter == 'non_staff':
            queryset = queryset.filter(is_staff=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ロール選択肢
        context['available_roles'] = UserRole.CHOICES

        # 統計情報
        context['stats'] = {
            'total_users': User.objects.count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'active_users': User.objects.filter(is_active=True).count(),
        }

        # ロール別カウント
        role_counts = {}
        for role_code, role_name in UserRole.CHOICES:
            count = UserProfile.objects.filter(roles__contains=[role_code]).count()
            role_counts[role_code] = count

        context['role_counts'] = role_counts

        # 現在のフィルター値
        context['current_search'] = self.request.GET.get('search', '')
        context['current_role'] = self.request.GET.get('role', 'all')
        context['current_staff'] = self.request.GET.get('staff', 'all')

        return context


class UserRoleEditView(LoginRequiredMixin, ExecutiveRequiredMixin, UpdateView):
    """ユーザーのロール編集"""
    model = UserProfile
    template_name = 'order_management/user_role_edit.html'
    fields = ['roles']
    success_url = reverse_lazy('order_management:user_management')

    def get_object(self, queryset=None):
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = self.object.user
        context['available_roles'] = UserRole.CHOICES

        # ロール別の権限説明
        context['role_permissions'] = {
            UserRole.SALES: [
                '案件管理',
                '顧客対応',
                '見積作成',
            ],
            UserRole.WORKER_DISPATCH: [
                '職人手配',
                '工事管理',
                '出金予定日入力',
            ],
            UserRole.ACCOUNTING: [
                '入出金管理',
                '請求書発行',
                '会計ダッシュボード',
                '出金状況変更',
            ],
            UserRole.EXECUTIVE: [
                '全機能アクセス',
                '純利益閲覧',
                '固定費閲覧',
                '全メンバー営業成績閲覧',
                'ユーザー管理',
            ],
        }

        return context

    def form_valid(self, form):
        messages.success(self.request, f'{self.object.user.username}のロールを更新しました。')
        return super().form_valid(form)


class UserRoleQuickEditView(LoginRequiredMixin, ExecutiveRequiredMixin, DetailView):
    """ユーザーロール簡易編集（Ajax対応）"""
    model = User

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        profile, _ = UserProfile.objects.get_or_create(user=user)

        action = request.POST.get('action')
        role = request.POST.get('role')

        if action == 'add' and role in [r[0] for r in UserRole.CHOICES]:
            if not profile.roles:
                profile.roles = []
            if role not in profile.roles:
                profile.roles.append(role)
                profile.save()
                messages.success(request, f'{user.username}に{role}ロールを追加しました。')
            else:
                messages.info(request, f'{user.username}は既に{role}ロールを持っています。')

        elif action == 'remove' and role in [r[0] for r in UserRole.CHOICES]:
            if profile.roles and role in profile.roles:
                profile.roles.remove(role)
                profile.save()
                messages.success(request, f'{user.username}から{role}ロールを削除しました。')
            else:
                messages.info(request, f'{user.username}は{role}ロールを持っていません。')

        # Ajax リクエストの場合
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'roles': profile.roles or [],
                'message': f'ロールを更新しました'
            })

        return redirect('order_management:user_management')
