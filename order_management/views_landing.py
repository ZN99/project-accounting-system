from django.shortcuts import render, redirect
from django.views.generic import TemplateView


class LandingView(TemplateView):
    """システム選択ランディングページ"""
    template_name = 'order_management/landing.html'

    def get(self, request):
        # 既にログイン済みの場合はダッシュボードにリダイレクト
        if request.user.is_authenticated:
            # 本部スタッフの場合
            if request.user.is_staff or request.user.is_superuser:
                return redirect('order_management:dashboard')
            else:
                # 権限が不明な場合はログアウト
                from django.contrib.auth import logout
                logout(request)

        return render(request, self.template_name)