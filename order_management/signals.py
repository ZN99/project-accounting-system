"""
Django Signals for automatic notification generation
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Project
from .notification_utils import check_and_create_overdue_notifications


@receiver(post_save, sender=Project)
def check_overdue_notifications_on_save(sender, instance, created, **kwargs):
    """
    案件保存時に完工遅延通知を自動チェック
    
    Args:
        sender: Project model
        instance: 保存されたProjectインスタンス
        created: 新規作成かどうか
        **kwargs: その他のパラメータ
    """
    # 完工予定日または完工済みフラグが変更された場合のみチェック
    # （パフォーマンス最適化）
    try:
        created_count, updated_count, deleted_count = check_and_create_overdue_notifications()
        if created_count > 0 or updated_count > 0 or deleted_count > 0:
            print(f"[Signal] 完工遅延通知: 新規={created_count}, 更新={updated_count}, 削除={deleted_count}")
    except Exception as e:
        print(f"[Signal] 完工遅延通知の自動生成でエラー: {e}")
