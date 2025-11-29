from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


@login_required
def mention_users_api(request):
    """メンション候補のユーザー一覧を返すAPI"""
    query = request.GET.get('q', '').strip()

    # ユーザー一覧を取得（アクティブユーザーのみ）
    users = User.objects.filter(is_active=True)

    # 検索クエリがある場合はフィルタリング
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

    # 最大20件まで
    users = users[:20]

    # レスポンスデータを生成
    user_list = []
    for user in users:
        # 表示名を生成
        display_name = user.username
        if user.first_name or user.last_name:
            display_name = f"{user.last_name} {user.first_name}".strip() or user.username

        user_list.append({
            'key': user.username,
            'value': display_name,
            'email': user.email or ''
        })

    return JsonResponse(user_list, safe=False)
