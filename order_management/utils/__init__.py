"""
Common utility functions
"""


def safe_int(value, default=0):
    """
    Safely convert a string to integer (removes commas)
    Avoids issues with THOUSAND_SEPARATOR settings

    Args:
        value: Value to convert (int, str, or other)
        default: Default value if conversion fails

    Returns:
        int: Converted integer value

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
