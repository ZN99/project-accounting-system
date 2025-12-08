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
    # 🔧 FIX: work_end_date と work_end_completed は @property なので ORM フィルタで使えない
    # ProjectProgressStep を直接クエリして該当する案件を取得
    from .models import ProjectProgressStep, ProgressStepTemplate

    today = timezone.now().date()

    try:
        # '完工日' テンプレートを取得
        completion_template = ProgressStepTemplate.objects.get(name='完工日')

        # 完工予定日が過ぎて、かつ完工済みでない ProjectProgressStep を取得
        overdue_steps = ProjectProgressStep.objects.filter(
            template=completion_template,
            is_completed=False,
            is_active=True
        ).select_related('project')

        # scheduled_date でフィルタ（JSONField なので Python で処理）
        # (project, scheduled_date) のタプルのリストとして格納
        overdue_projects = []
        for step in overdue_steps:
            if step.value and isinstance(step.value, dict):
                scheduled_date_str = step.value.get('scheduled_date')
                if scheduled_date_str:
                    from datetime import datetime
                    try:
                        scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
                        if scheduled_date < today:
                            overdue_projects.append((step.project, scheduled_date))
                    except (ValueError, TypeError):
                        pass

    except ProgressStepTemplate.DoesNotExist:
        print("[Signal] 完工日テンプレートが見つかりません")
        overdue_projects = []
    except Exception as e:
        print(f"[Signal] 完工遅延通知の自動生成でエラー: {e}")
        overdue_projects = []

    created_count = 0
    updated_count = 0
    deleted_count = 0

    # スタッフユーザーを取得（通知の送信先）
    staff_users = User.objects.filter(is_staff=True, is_active=True)

    if not staff_users.exists():
        return (0, 0, 0)

    # 遅延している案件に対して通知を生成または更新
    for project, scheduled_date in overdue_projects:
        days_overdue = (today - scheduled_date).days

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
                    message=f'完工予定日を{days_overdue}日過ぎています（予定: {scheduled_date}）',
                    link=f'/orders/{project.id}/',
                    related_project=project
                )
                created_count += 1
            else:
                # 既存の通知のメッセージを更新（日数が変わるため）
                existing_notification.message = f'完工予定日を{days_overdue}日過ぎています（予定: {scheduled_date}）'
                existing_notification.is_read = False  # 未読に戻す
                existing_notification.save()
                updated_count += 1

    # 完工済みになった案件の通知を削除（アーカイブされていないもののみ）
    # 🔧 FIX: work_end_completed は @property なので ORM フィルタで使えない
    # ProjectProgressStep を直接クエリして完工済み案件を取得
    try:
        completion_template = ProgressStepTemplate.objects.get(name='完工日')
        completed_steps = ProjectProgressStep.objects.filter(
            template=completion_template,
            is_completed=True,
            is_active=True
        ).values_list('project_id', flat=True)

        completed_notifications = Notification.objects.filter(
            notification_type='work_completion_overdue',
            related_project_id__in=completed_steps,
            is_archived=False
        )
        deleted_count = completed_notifications.count()
        completed_notifications.delete()
    except ProgressStepTemplate.DoesNotExist:
        deleted_count = 0
    except Exception as e:
        print(f"[Signal] 完工済み通知削除でエラー: {e}")
        deleted_count = 0

    # 完工予定日が未設定または将来の日付の案件の通知を削除
    # 🔧 FIX: work_end_date は @property なので ORM フィルタで使えない
    # 遅延していない案件（overdue_projects に含まれない案件）の通知を削除
    overdue_project_ids = [p.id for p, _ in overdue_projects]
    invalid_notifications = Notification.objects.filter(
        notification_type='work_completion_overdue',
        is_archived=False
    ).exclude(
        related_project_id__in=overdue_project_ids
    )
    deleted_count += invalid_notifications.count()
    invalid_notifications.delete()

    return (created_count, updated_count, deleted_count)
