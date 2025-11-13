from django import template

register = template.Library()

@register.filter(name='split')
def split(value, separator):
    """文字列を指定されたセパレータで分割する"""
    if not value:
        return []
    return value.split(separator)

@register.filter(name='format_next_action')
def format_next_action(value):
    """Next Actionをバッジ形式にフォーマットする
    例: '見積書発行：発行日を入力してください'
    → '<span class="badge bg-white border text-dark me-1">見積書発行</span>発行日を入力してください'
    """
    if not value or '：' not in value:
        return value

    parts = value.split('：', 1)  # 最初の「：」のみで分割
    step_name = parts[0]
    action = parts[1] if len(parts) > 1 else ''

    return f'<span class="badge bg-white border text-dark me-1" style="font-size: 0.65rem;">{step_name}</span>{action}'
