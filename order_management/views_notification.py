"""
通知機能のビュー
"""
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Notification
from .mixins import PerPageMixin


class NotificationListView(LoginRequiredMixin, PerPageMixin, ListView):
    """通知一覧ページ"""
    model = Notification
    template_name = 'order_management/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 50

    def get_queryset(self):
        """ユーザーの通知を取得（タブによってフィルタリング）"""
        queryset = self.request.user.notifications.select_related(
            'related_project', 'related_comment'
        )

        # タブパラメータを取得
        tab = self.request.GET.get('tab', 'unread')

        if tab == 'archived':
            # アーカイブ済み通知
            queryset = queryset.filter(is_archived=True)
        else:
            # 未読通知（デフォルト）
            queryset = queryset.filter(is_archived=False)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 現在のタブ
        context['current_tab'] = self.request.GET.get('tab', 'unread')

        # 未読数（アーカイブされていない通知のみ）
        context['unread_count'] = self.request.user.notifications.filter(
            is_read=False,
            is_archived=False
        ).count()

        # アーカイブ済み数
        context['archived_count'] = self.request.user.notifications.filter(
            is_archived=True
        ).count()

        # 総数（アーカイブされていない通知）
        context['total_count'] = self.request.user.notifications.filter(
            is_archived=False
        ).count()

        # 完工遅延の数（アーカイブされていない通知のみ）
        context['overdue_count'] = self.request.user.notifications.filter(
            notification_type='work_completion_overdue',
            is_archived=False
        ).count()

        return context


@login_required
@require_POST
def mark_as_read_and_archive(request, notification_id):
    """通知を既読＆アーカイブする"""
    try:
        notification = Notification.objects.get(
            pk=notification_id,
            recipient=request.user
        )
        notification.is_read = True
        notification.is_archived = True
        notification.archived_at = timezone.now()
        notification.save()

        return JsonResponse({
            'success': True,
            'message': '通知をアーカイブしました'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '通知が見つかりません'
        }, status=404)
