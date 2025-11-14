"""
ロールベースのテンプレートタグとフィルター
"""
from django import template
from order_management.user_roles import has_role, has_any_role, PermissionHelper

register = template.Library()


@register.filter(name='has_role')
def has_role_filter(user, role):
    """
    ユーザーが指定されたロールを持っているかチェック

    使用例:
    {% if user|has_role:'役員' %}
        <p>役員専用コンテンツ</p>
    {% endif %}
    """
    return has_role(user, role)


@register.filter(name='has_any_role')
def has_any_role_filter(user, roles_str):
    """
    ユーザーが指定されたロールのいずれかを持っているかチェック

    使用例:
    {% if user|has_any_role:'経理,役員' %}
        <p>経理または役員のコンテンツ</p>
    {% endif %}
    """
    roles = [r.strip() for r in roles_str.split(',')]
    return has_any_role(user, roles)


@register.filter(name='can_view_profit')
def can_view_profit_filter(user):
    """
    純利益を閲覧できるかチェック

    使用例:
    {% if user|can_view_profit %}
        <div class="profit">¥{{ profit|intcomma }}</div>
    {% endif %}
    """
    return PermissionHelper.can_view_profit(user)


@register.filter(name='can_view_fixed_costs')
def can_view_fixed_costs_filter(user):
    """
    固定費を閲覧できるかチェック

    使用例:
    {% if user|can_view_fixed_costs %}
        <div class="fixed-costs">固定費: ¥{{ fixed_costs|intcomma }}</div>
    {% endif %}
    """
    return PermissionHelper.can_view_fixed_costs(user)


@register.filter(name='can_change_payment_status')
def can_change_payment_status_filter(user):
    """
    出金状況を変更できるかチェック

    使用例:
    {% if user|can_change_payment_status %}
        <select name="payment_status">...</select>
    {% else %}
        <span>{{ payment_status }}</span>
    {% endif %}
    """
    return PermissionHelper.can_change_payment_status(user)


@register.filter(name='can_input_payment_due_date')
def can_input_payment_due_date_filter(user):
    """
    出金予定日を入力できるかチェック
    """
    return PermissionHelper.can_input_payment_due_date(user)


@register.filter(name='can_issue_invoice')
def can_issue_invoice_filter(user):
    """
    請求書を発行できるかチェック
    """
    return PermissionHelper.can_issue_invoice(user)


@register.filter(name='can_view_all_member_performance')
def can_view_all_member_performance_filter(user):
    """
    全メンバーの営業成績を閲覧できるかチェック
    """
    return PermissionHelper.can_view_all_member_performance(user)


@register.filter(name='can_manage_project')
def can_manage_project_filter(user):
    """
    案件を管理できるかチェック
    """
    return PermissionHelper.can_manage_project(user)


@register.filter(name='can_dispatch_workers')
def can_dispatch_workers_filter(user):
    """
    職人を手配できるかチェック
    """
    return PermissionHelper.can_dispatch_workers(user)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    辞書から指定されたキーの値を取得

    使用例:
    {{ role_counts|get_item:role_code }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def get_user_roles(user):
    """
    ユーザーのロール一覧を取得

    使用例:
    {% get_user_roles user as roles %}
    {% for role in roles %}
        <span class="badge">{{ role }}</span>
    {% endfor %}
    """
    try:
        return user.userprofile.get_roles_display()
    except:
        return []
