"""
コメント・通知システムのシグナルハンドラ
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Comment, Notification


@receiver(post_save, sender=Comment)
def handle_comment_posted(sender, instance, created, **kwargs):
    """
    コメント投稿時の処理
    - メンション抽出
    - メンションされたユーザーへの通知作成
    """
    if not created:
        return

    # メンションユーザーを抽出して保存
    mentioned_users = instance.extract_mentions()
    instance.mentioned_users.set(mentioned_users)

    # メンションされたユーザーに通知を作成
    for user in mentioned_users:
        Notification.objects.create(
            recipient=user,
            notification_type='mention',
            title=f'{instance.author.username}さんがあなたをメンションしました',
            message=f'案件「{instance.project.site_name}」のコメントであなたがメンションされました。',
            link=reverse('order_management:project_detail', kwargs={'pk': instance.project.pk}),
            related_comment=instance,
            related_project=instance.project
        )
