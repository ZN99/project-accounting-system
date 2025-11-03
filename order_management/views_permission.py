from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.urls import reverse


class PermissionDeniedView(TemplateView):
    """権限不足時の親切なガイダンスページ"""
    template_name = 'order_management/permission_denied.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # アクセスしようとしたページの情報を取得
        requested_path = self.request.GET.get('next', '/')
        context['requested_path'] = requested_path

        # パスに基づいて必要な権限とアカウント種別を判定
        if '/surveys/' in requested_path and '/field/' not in requested_path:
            # 本部システムの調査管理機能
            context['required_permission'] = 'headquarters_staff'
            context['page_type'] = 'headquarters'
            context['page_description'] = '本部システム（調査管理）'
            context['required_account'] = '本部スタッフアカウント'
            context['login_url'] = reverse('order_management:login')
            context['example_accounts'] = [
                {'username': 'headquarters', 'description': '本部管理者'}
            ]
        elif '/admin/' in requested_path:
            # Django管理画面
            context['required_permission'] = 'superuser'
            context['page_type'] = 'admin'
            context['page_description'] = 'Django管理画面'
            context['required_account'] = 'システム管理者アカウント'
            context['login_url'] = '/admin/login/'
            context['example_accounts'] = [
                {'username': 'admin', 'description': 'システム管理者'}
            ]
        elif '/orders/' in requested_path:
            # 本部システム
            context['required_permission'] = 'headquarters_staff'
            context['page_type'] = 'headquarters'
            context['page_description'] = '本部システム（案件・発注管理）'
            context['required_account'] = '本部スタッフアカウント'
            context['login_url'] = reverse('order_management:login')
            context['example_accounts'] = [
                {'username': 'headquarters', 'description': '本部管理者'}
            ]
        else:
            # その他
            context['required_permission'] = 'unknown'
            context['page_type'] = 'unknown'
            context['page_description'] = '不明なページ'
            context['required_account'] = '適切なアカウント'
            context['login_url'] = reverse('order_management:login')
            context['example_accounts'] = []

        # 現在のユーザー情報
        if self.request.user.is_authenticated:
            context['current_user'] = self.request.user
            context['is_field_surveyor'] = False

        return context


def permission_denied_handler(request, exception=None):
    """403エラーのカスタムハンドラー"""
    view = PermissionDeniedView()
    view.request = request
    return view.get(request)