from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse


class HeadquartersLoginView(View):
    """本部システム専用ログイン画面"""
    template_name = 'order_management/login.html'

    def get(self, request):
        # 既にログイン済みの場合の処理
        if request.user.is_authenticated:
            # 本部スタッフの場合は本部ダッシュボードへ
            if request.user.is_staff or request.user.is_superuser:
                return redirect('order_management:dashboard')
            else:
                # 権限がない場合はログアウト
                logout(request)
                messages.warning(request, 'アクセス権限がありません。')

        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'ユーザー名とパスワードを入力してください。')
            return render(request, self.template_name)

        # 認証を試行
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 本部スタッフまたはsuperuserの場合は本部システムへ（Surveyorプロファイルがあっても優先）
            if (user.is_staff or user.is_superuser) and user.is_active:
                login(request, user)

                # セッションに本部スタッフ情報を保存
                request.session['is_headquarters_staff'] = True
                request.session['staff_name'] = f"{user.first_name} {user.last_name}".strip() or user.username

                messages.success(request, f'{request.session["staff_name"]}さん、ログインしました。')

                # リダイレクト先の決定
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url and next_url.startswith('/'):
                    redirect_url = next_url
                else:
                    redirect_url = reverse('order_management:dashboard')

                # AJAX リクエストの場合
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': redirect_url
                    })

                return redirect(redirect_url)
            else:
                # スタッフ権限がない場合はエラー
                messages.error(request, 'このアカウントは本部システムへのアクセス権限がありません。')
        else:
            messages.error(request, 'ユーザー名またはパスワードが正しくありません。')

        # AJAX エラーレスポンス
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'ログインに失敗しました。'
            })

        return render(request, self.template_name)


class HeadquartersLogoutView(View):
    """本部システム専用ログアウト"""

    def get(self, request):
        return self.post(request)

    def post(self, request):
        if request.user.is_authenticated:
            staff_name = request.session.get('staff_name', '')
            logout(request)
            if staff_name:
                messages.success(request, f'{staff_name}さん、ログアウトしました。')
            else:
                messages.success(request, 'ログアウトしました。')

        return redirect('order_management:landing')