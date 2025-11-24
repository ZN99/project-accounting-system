"""
完工遅延通知を自動生成・更新するManagementコマンド
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from order_management.models import Project, Notification

User = get_user_model()


class Command(BaseCommand):
    help = '完工予定日を過ぎた案件の通知を生成・更新します'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('完工遅延通知の更新を開始します...'))

        # 1. 完工予定日を1日以上過ぎて、かつ完工済みでない案件を取得
        today = timezone.now().date()
        overdue_threshold = today - timedelta(days=1)

        overdue_projects = Project.objects.filter(
            work_end_date__lt=overdue_threshold,
            work_end_completed=False
        )

        created_count = 0
        deleted_count = 0

        # 2. スタッフユーザーを取得（通知の送信先）
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        if not staff_users.exists():
            self.stdout.write(self.style.WARNING('スタッフユーザーが見つかりません'))
            return

        # 3. 遅延している案件に対して通知を生成
        for project in overdue_projects:
            days_overdue = (today - project.work_end_date).days

            # 各スタッフユーザーに通知を送る
            for user in staff_users:
                # 既に同じ案件の完工遅延通知が存在するかチェック
                existing_notification = Notification.objects.filter(
                    recipient=user,
                    notification_type='work_completion_overdue',
                    related_project=project
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

        # 4. 完工済みになった案件の通知を削除
        completed_notifications = Notification.objects.filter(
            notification_type='work_completion_overdue',
            related_project__work_end_completed=True
        )
        deleted_count = completed_notifications.count()
        completed_notifications.delete()

        # 5. 完工予定日が未設定または将来の日付の案件の通知を削除
        invalid_notifications = Notification.objects.filter(
            notification_type='work_completion_overdue'
        ).exclude(
            related_project__work_end_date__lt=overdue_threshold
        )
        deleted_count += invalid_notifications.count()
        invalid_notifications.delete()

        self.stdout.write(self.style.SUCCESS(
            f'完工遅延通知の更新完了: 作成 {created_count}件、削除 {deleted_count}件'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'現在の遅延案件数: {overdue_projects.count()}件'
        ))
