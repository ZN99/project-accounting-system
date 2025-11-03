"""
ユーザーロールと権限管理
"""
from django.contrib.auth.decorators import user_passes_test
from functools import wraps


# ロール定義
class UserRole:
    """ユーザーロールの定義"""
    SALES = '営業'  # 案件受注・顧客対応
    WORKER_DISPATCH = '職人発注'  # 職人手配・工事管理
    ACCOUNTING = '経理'  # 財務管理・入出金管理
    EXECUTIVE = '役員'  # 経営管理

    CHOICES = [
        (SALES, '営業ロール'),
        (WORKER_DISPATCH, '職人発注ロール'),
        (ACCOUNTING, '経理ロール'),
        (EXECUTIVE, '役員ロール'),
    ]

    ALL_ROLES = [SALES, WORKER_DISPATCH, ACCOUNTING, EXECUTIVE]


# 権限チェック関数
def has_role(user, role):
    """ユーザーが指定されたロールを持っているかチェック"""
    if not user.is_authenticated:
        return False

    # スーパーユーザーは全ての権限を持つ
    if user.is_superuser:
        return True

    # UserProfileからロールを取得
    try:
        profile = user.userprofile
        return role in profile.roles
    except:
        return False


def has_any_role(user, roles):
    """ユーザーが指定されたロールのいずれかを持っているかチェック"""
    return any(has_role(user, role) for role in roles)


def has_all_roles(user, roles):
    """ユーザーが指定されたロール全てを持っているかチェック"""
    return all(has_role(user, role) for role in roles)


# デコレータ
def role_required(*roles):
    """
    指定されたロールのいずれかを持つユーザーのみアクセスを許可するデコレータ

    使用例:
    @role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
    def accounting_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            if has_any_role(request.user, roles):
                return view_func(request, *args, **kwargs)

            # 権限がない場合は403エラー
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("この機能にアクセスする権限がありません。")

        return wrapper
    return decorator


def executive_required(view_func):
    """役員ロール必須のデコレータ"""
    return role_required(UserRole.EXECUTIVE)(view_func)


def accounting_required(view_func):
    """経理ロール必須のデコレータ（役員も許可）"""
    return role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)(view_func)


def worker_dispatch_required(view_func):
    """職人発注ロール必須のデコレータ"""
    return role_required(UserRole.WORKER_DISPATCH, UserRole.EXECUTIVE)(view_func)


def sales_required(view_func):
    """営業ロール必須のデコレータ"""
    return role_required(UserRole.SALES, UserRole.EXECUTIVE)(view_func)


# 権限チェックヘルパー関数
class PermissionHelper:
    """権限チェックのヘルパークラス"""

    @staticmethod
    def can_view_profit(user):
        """純利益を閲覧できるか（役員のみ）"""
        return has_role(user, UserRole.EXECUTIVE)

    @staticmethod
    def can_view_fixed_costs(user):
        """固定費を閲覧できるか（役員のみ）"""
        return has_role(user, UserRole.EXECUTIVE)

    @staticmethod
    def can_change_payment_status(user):
        """出金状況を変更できるか（経理・役員のみ）"""
        return has_any_role(user, [UserRole.ACCOUNTING, UserRole.EXECUTIVE])

    @staticmethod
    def can_input_payment_due_date(user):
        """出金予定日を入力できるか（職人発注・役員のみ）"""
        return has_any_role(user, [UserRole.WORKER_DISPATCH, UserRole.EXECUTIVE])

    @staticmethod
    def can_issue_invoice(user):
        """請求書を発行できるか（経理・役員のみ）"""
        return has_any_role(user, [UserRole.ACCOUNTING, UserRole.EXECUTIVE])

    @staticmethod
    def can_view_all_member_performance(user):
        """全メンバーの営業成績を閲覧できるか（役員のみ）"""
        return has_role(user, UserRole.EXECUTIVE)

    @staticmethod
    def can_manage_project(user):
        """案件を管理できるか（営業・役員のみ）"""
        return has_any_role(user, [UserRole.SALES, UserRole.EXECUTIVE])

    @staticmethod
    def can_dispatch_workers(user):
        """職人を手配できるか（職人発注・役員のみ）"""
        return has_any_role(user, [UserRole.WORKER_DISPATCH, UserRole.EXECUTIVE])
