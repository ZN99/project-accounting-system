"""
通知関連のユーティリティ関数
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Project, Notification

User = get_user_model()


def check_and_create_overdue_notifications():
    """
    完工遅延通知を自動チェック・生成する
    ダッシュボード表示時やバックグラウンドタスクから呼び出される

    Returns:
        tuple: (created_count, updated_count, deleted_count)
    """
    # 完工予定日が過ぎて、かつ完工済みでない案件を取得
    today = timezone.now().date()

    overdue_projects = Project.objects.filter(
        work_end_date__lt=today,  # 今日より前（昨日以前）
        work_end_completed=False
    )

    created_count = 0
    updated_count = 0
    deleted_count = 0

    # スタッフユーザーを取得（通知の送信先）
    staff_users = User.objects.filter(is_staff=True, is_active=True)

    if not staff_users.exists():
        return (0, 0, 0)

    # 遅延している案件に対して通知を生成または更新
    for project in overdue_projects:
        days_overdue = (today - project.work_end_date).days

        # 各スタッフユーザーに通知を送る
        for user in staff_users:
            # 既に同じ案件の完工遅延通知が存在するかチェック
            existing_notification = Notification.objects.filter(
                recipient=user,
                notification_type='work_completion_overdue',
                related_project=project,
                is_archived=False  # アーカイブされていない通知のみ更新
            ).first()

            if not existing_notification:
                # 通知を新規作成
                Notification.objects.create(
                    recipient=user,
                    notification_type='work_completion_overdue',
                    title=f'完工遅延: {project.site_name}',
                    message=f'完工予定日を{days_overdue}日過ぎています（予定: {project.work_end_date}）',
                    link=f'/orders/{project.id}/',
                    related_project=project
                )
                created_count += 1
            else:
                # 既存の通知のメッセージを更新（日数が変わるため）
                existing_notification.message = f'完工予定日を{days_overdue}日過ぎています（予定: {project.work_end_date}）'
                existing_notification.is_read = False  # 未読に戻す
                existing_notification.save()
                updated_count += 1

    # 完工済みになった案件の通知を削除（アーカイブされていないもののみ）
    completed_notifications = Notification.objects.filter(
        notification_type='work_completion_overdue',
        related_project__work_end_completed=True,
        is_archived=False
    )
    deleted_count = completed_notifications.count()
    completed_notifications.delete()

    # 完工予定日が未設定または将来の日付の案件の通知を削除
    invalid_notifications = Notification.objects.filter(
        notification_type='work_completion_overdue',
        is_archived=False
    ).exclude(
        related_project__work_end_date__lt=today  # 今日より前（昨日以前）
    )
    deleted_count += invalid_notifications.count()
    invalid_notifications.delete()

    return (created_count, updated_count, deleted_count)
