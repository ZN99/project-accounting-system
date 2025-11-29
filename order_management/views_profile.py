"""
ユーザープロフィール設定のビュー
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile


@login_required
def profile_settings(request):
    """プロフィール設定ページ"""
    # ユーザーのプロフィールを取得または作成
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # アバター画像のアップロード
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        # 背景色の変更
        if 'avatar_background_color' in request.POST:
            profile.avatar_background_color = request.POST['avatar_background_color']

        # アバター削除
        if request.POST.get('remove_avatar') == 'true':
            profile.avatar.delete()
            profile.avatar = None

        profile.save()
        messages.success(request, 'プロフィールを更新しました')

        # Ajaxリクエストの場合はJSON応答
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            avatar_data = profile.get_avatar_data()
            return JsonResponse({
                'success': True,
                'avatar': avatar_data,
                'message': 'プロフィールを更新しました'
            })

        return redirect('order_management:profile_settings')

    context = {
        'profile': profile,
        'color_choices': UserProfile.BACKGROUND_COLOR_CHOICES,
    }

    return render(request, 'order_management/profile_settings.html', context)
