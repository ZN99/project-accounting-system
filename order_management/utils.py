"""
共通ユーティリティ関数
"""


def safe_int(value, default=0):
    """
    文字列を整数に安全に変換（カンマを削除）
    THOUSAND_SEPARATOR設定の影響を受けないようにする

    Args:
        value: 変換する値（int, str, その他）
        default: 変換できない場合のデフォルト値

    Returns:
        int: 変換された整数値

    Examples:
        >>> safe_int('2025')
        2025
        >>> safe_int('2,025')
        2025
        >>> safe_int(2025)
        2025
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value.replace(',', ''))
    return default
