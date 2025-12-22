"""
View mixins for order_management app
"""


class PerPageMixin:
    """
    Mixin for ListView that adds per-page pagination control.

    Usage:
        class MyListView(PerPageMixin, ListView):
            paginate_by = 20  # Default per-page count
            model = MyModel

    The mixin will:
    - Check for 'per_page' in GET parameters
    - Validate it's an allowed value (10, 25, 50, 100, 200)
    - Override get_paginate_by() to return the requested per_page
    - Add 'per_page' to context for template use
    """

    allowed_per_page_values = [10, 25, 50, 100, 200]
    default_per_page = 20

    def get_paginate_by(self, queryset):
        """
        Override Django's get_paginate_by to support per_page parameter.

        Returns:
            int: Number of items per page
        """
        per_page = self.request.GET.get('per_page', self.paginate_by or self.default_per_page)
        try:
            per_page = int(per_page)
            if per_page not in self.allowed_per_page_values:
                # If not in allowed values, use default
                per_page = self.paginate_by or self.default_per_page
        except (ValueError, TypeError):
            per_page = self.paginate_by or self.default_per_page

        return per_page

    def get_context_data(self, **kwargs):
        """
        Add per_page to context for template use.
        """
        context = super().get_context_data(**kwargs)
        context['per_page'] = self.get_paginate_by(None)
        return context
