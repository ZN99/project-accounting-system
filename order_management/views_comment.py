"""
コメント・通知機能のビュー
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Project, Comment, Notification, CommentAttachment
import json


@login_required
@require_POST
def post_comment(request, project_id):
    """コメントを投稿（ファイル添付対応、スレッド対応）"""
    project = get_object_or_404(Project, pk=project_id)

    try:
        # FormDataの場合（ファイルあり）
        if request.content_type and 'multipart/form-data' in request.content_type:
            content = request.POST.get('content', '').strip()
            is_important = request.POST.get('is_important') == 'true'
            parent_comment_id = request.POST.get('parent_comment_id')
            files = request.FILES.getlist('files')
        # JSONの場合（ファイルなし）
        else:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            is_important = data.get('is_important', False)
            parent_comment_id = data.get('parent_comment_id')
            files = []

        if not content:
            return JsonResponse({'error': 'コメント内容を入力してください'}, status=400)

        # 親コメントの取得（返信の場合）
        parent_comment = None
        if parent_comment_id:
            try:
                parent_comment = Comment.objects.get(pk=parent_comment_id, project=project)
            except Comment.DoesNotExist:
                return JsonResponse({'error': '返信先のコメントが見つかりません'}, status=404)

        # コメントを作成
        comment = Comment.objects.create(
            project=project,
            author=request.user,
            content=content,
            is_important=is_important,
            parent_comment=parent_comment
        )

        # ファイルがある場合は添付ファイルを作成
        attachments_data = []
        for file in files:
            attachment = CommentAttachment.objects.create(
                comment=comment,
                file=file,
                file_name=file.name,
                file_size=file.size,
                file_type=file.content_type or 'application/octet-stream'
            )
            attachments_data.append({
                'id': attachment.id,
                'file_name': attachment.file_name,
                'file_size': attachment.get_file_size_display(),
                'file_type': attachment.file_type,
                'file_url': attachment.file.url if attachment.file else '',
                'is_image': attachment.is_image(),
                'is_pdf': attachment.is_pdf(),
            })

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': comment.author.username,
                'content': comment.content,
                'is_important': comment.is_important,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                'attachments': attachments_data,
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_comments(request, project_id):
    """案件のコメント一覧を取得（スレッド構造、添付ファイル情報含む）"""
    project = get_object_or_404(Project, pk=project_id)

    def format_comment(comment):
        """コメントをJSONフォーマットに変換"""
        # 添付ファイル情報を取得
        attachments_data = []
        for attachment in comment.attachments.all():
            attachments_data.append({
                'id': attachment.id,
                'file_name': attachment.file_name,
                'file_size': attachment.get_file_size_display(),
                'file_type': attachment.file_type,
                'file_url': attachment.file.url if attachment.file else '',
                'is_image': attachment.is_image(),
                'is_pdf': attachment.is_pdf(),
            })

        # 返信を取得（古い順に表示）
        replies_data = []
        for reply in comment.replies.select_related('author').prefetch_related('attachments').order_by('created_at'):
            replies_data.append(format_comment(reply))

        return {
            'id': comment.id,
            'author': comment.author.username,
            'content': comment.content,
            'is_important': comment.is_important,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            'attachments': attachments_data,
            'replies': replies_data,
            'reply_count': len(replies_data),
            'can_edit': comment.author == request.user,
            'can_delete': comment.author == request.user,
        }

    # 親コメントのみを取得（返信ではないコメント）- 古い順に表示
    parent_comments = project.comments.filter(parent_comment__isnull=True).select_related('author').prefetch_related('attachments').order_by('created_at')

    comments_data = []
    for comment in parent_comments:
        comments_data.append(format_comment(comment))

    return JsonResponse({
        'comments': comments_data
    })


@login_required
@require_GET
def get_notifications(request):
    """ユーザーの通知一覧を取得"""
    try:
        notifications = request.user.notifications.select_related(
            'related_project', 'related_comment'
        ).all()[:20]  # 最新20件

        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'link': notification.link,
                'is_read': notification.is_read,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        # 未読数も返す
        unread_count = request.user.notifications.filter(is_read=False).count()

        return JsonResponse({
            'notifications': notifications_data,
            'unread_count': unread_count
        })
    except AttributeError:
        # 通知機能が実装されていない場合は空の配列を返す
        return JsonResponse({
            'notifications': [],
            'unread_count': 0
        })


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """通知を既読にする"""
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user
    )
    notification.is_read = True
    notification.save()

    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read(request):
    """全ての通知を既読にする"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_POST
def edit_comment(request, comment_id):
    """コメントを編集"""
    comment = get_object_or_404(Comment, pk=comment_id)

    # 自分のコメントのみ編集可能
    if comment.author != request.user:
        return JsonResponse({'success': False, 'error': '編集権限がありません'}, status=403)

    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({'success': False, 'error': 'コメント内容を入力してください'}, status=400)

        comment.content = content
        comment.save()

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'updated_at': comment.updated_at.strftime('%Y-%m-%d %H:%M'),
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def delete_comment(request, comment_id):
    """コメントを削除"""
    comment = get_object_or_404(Comment, pk=comment_id)

    # 自分のコメントのみ削除可能
    if comment.author != request.user:
        return JsonResponse({'success': False, 'error': '削除権限がありません'}, status=403)

    try:
        comment.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
