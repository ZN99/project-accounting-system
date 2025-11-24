"""
通知機能のビュー
"""
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """通知一覧ページ"""
    model = Notification
    template_name = 'order_management/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 50

    def get_queryset(self):
        """ユーザーの通知を新しい順に取得"""
        return self.request.user.notifications.select_related(
            'related_project', 'related_comment'
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 未読数
        context['unread_count'] = self.request.user.notifications.filter(
            is_read=False
        ).count()

        # 総数
        context['total_count'] = self.request.user.notifications.count()

        # 完工遅延の数
        context['overdue_count'] = self.request.user.notifications.filter(
            notification_type='work_completion_overdue'
        ).count()

        return context
