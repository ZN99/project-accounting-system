# Pagination Per-Page Controls Implementation Status

**Date:** 2025-12-22
**Task:** Add per-page item count selection toggle near all pagination elements across all pages

---

## ✅ Completed Work

### 1. Reusable Pagination Component Created
**File:** `order_management/templates/order_management/includes/pagination_controls.html`

**Features:**
- Per-page selector (10, 25, 50, 100, 200 options)
- Item count display ("全XX件中 YY〜ZZ件を表示")
- Full pagination controls with first/prev/next/last buttons
- Page numbers with ellipsis for large page counts
- JavaScript handler for changing per-page count
- Preserves all URL parameters when changing page/per-page

**Usage:**
```django
{% include 'order_management/includes/pagination_controls.html' with page_obj=page_obj per_page=per_page %}
```

### 2. Per-Page Mixin Created
**File:** `order_management/mixins.py`

**Class:** `PerPageMixin`

**Features:**
- Overrides `get_paginate_by()` to support `per_page` GET parameter
- Validates per_page against allowed values (10, 25, 50, 100, 200)
- Falls back to default if invalid value provided
- Adds `per_page` to context for template use

**Usage:**
```python
from order_management.mixins import PerPageMixin

class MyListView(LoginRequiredMixin, PerPageMixin, ListView):
    paginate_by = 20  # Default
    model = MyModel
```

### 3. Backend Views Updated (3 views)

#### ✅ `order_management/views_client_company.py`
- **ClientCompanyListView**: Added PerPageMixin
- Default: 20 items/page
- Template: `client_company/client_company_list.html`

#### ✅ `order_management/views_cost.py`
- **FixedCostListView**: Added PerPageMixin
- **VariableCostListView**: Added PerPageMixin
- Default: 20 items/page each
- Templates: `cost/fixed_cost_list.html`, `cost/variable_cost_list.html`

### 4. Templates Updated (1 template)

#### ✅ `order_management/templates/order_management/contractor_detail.html`
- Replaced old pagination (simple prev/next only) with new reusable component
- Page object: `subcontracts_page`
- Backend already supported per_page parameter

---

## ⏳ Remaining Work

### Backend Views to Update

#### 1. `order_management/views_checklist.py`
```python
# Line 17-22
class ChecklistTemplateListView(LoginRequiredMixin, ListView):
    # TODO: Add PerPageMixin
    paginate_by = 20
```

**Action needed:**
1. Import: `from .mixins import PerPageMixin`
2. Change: `class ChecklistTemplateListView(LoginRequiredMixin, PerPageMixin, ListView):`

#### 2. `order_management/views_user_management.py`
```python
# Line 25-30
class UserManagementDashboardView(LoginRequiredMixin, ListView):
    # TODO: Add PerPageMixin
    paginate_by = 20
```

**Action needed:**
1. Import: `from .mixins import PerPageMixin`
2. Change: `class UserManagementDashboardView(LoginRequiredMixin, PerPageMixin, ListView):`

#### 3. `order_management/views_notification.py`
```python
# Line 13-18
class NotificationListView(LoginRequiredMixin, ListView):
    # TODO: Add PerPageMixin
    paginate_by = 50
```

**Action needed:**
1. Import: `from .mixins import PerPageMixin`
2. Change: `class NotificationListView(LoginRequiredMixin, PerPageMixin, ListView):`

#### 4. `subcontract_management/views.py`
```python
# Line 473-480
@login_required
def contractor_list(request):
    # TODO: Add per_page handling
    # Currently uses manual Paginator with hardcoded 20 items
    paginator = Paginator(contractors, 20)
```

**Action needed:**
```python
per_page = request.GET.get('per_page', 20)
try:
    per_page = int(per_page)
    if per_page not in [10, 25, 50, 100, 200]:
        per_page = 20
except (ValueError, TypeError):
    per_page = 20

paginator = Paginator(contractors, per_page)

# In context:
context = {
    'page_obj': page,
    'per_page': per_page,
    # ... other context
}
```

#### 5. `subcontract_management/views_skills.py`
```python
# Line 10-20
class ContractorSkillsDashboardView(LoginRequiredMixin, ListView):
    # TODO: Add PerPageMixin
    paginate_by = 20
```

**Action needed:**
1. Create: `subcontract_management/mixins.py` (copy from order_management/mixins.py)
2. Import: `from .mixins import PerPageMixin`
3. Change: `class ContractorSkillsDashboardView(LoginRequiredMixin, PerPageMixin, ListView):`

### Templates to Update

All templates need to replace existing pagination with:
```django
{% include 'order_management/includes/pagination_controls.html' with page_obj=page_obj per_page=per_page %}
```

#### 6. `order_management/templates/order_management/client_company/client_company_list.html`
- Find existing pagination block
- Replace with include statement

#### 7. `order_management/templates/order_management/cost/fixed_cost_list.html`
- Find existing pagination block
- Replace with include statement

#### 8. `order_management/templates/order_management/cost/variable_cost_list.html`
- Find existing pagination block
- Replace with include statement

#### 9. `order_management/templates/order_management/checklist/template_list.html`
- Find existing pagination block
- Replace with include statement

#### 10. `order_management/templates/order_management/user_management_dashboard.html`
- Find existing pagination block
- Replace with include statement

#### 11. `order_management/templates/order_management/notifications.html`
- Find existing pagination block
- Replace with include statement

#### 12. `order_management/templates/order_management/ordering_dashboard.html`
- Function-based view (line 2338-2345 in views.py)
- Needs manual per_page handling like contractor_list

#### 13. `order_management/templates/order_management/contractor_projects.html`
- Function-based view (ContractorProjectsView, line 162-178 in views_contractor.py)
- Check if pagination exists, add if missing

#### 14. `subcontract_management/templates/subcontract_management/contractor_list.html`
- Replace pagination with include

#### 15. `subcontract_management/templates/subcontract_management/contractor_skills_dashboard.html`
- Replace pagination with include

---

## Testing Checklist

Once all updates are complete, test each paginated page:

- [ ] Client Company List (`/client-companies/`)
- [ ] Contractor Detail (subcontracts tab)
- [ ] Fixed Cost List (`/costs/fixed/`)
- [ ] Variable Cost List (`/costs/variable/`)
- [ ] Checklist Templates (`/checklists/templates/`)
- [ ] User Management Dashboard (`/users/`)
- [ ] Notifications (`/notifications/`)
- [ ] Contractor List (subcontract_management)
- [ ] Contractor Skills Dashboard
- [ ] Ordering Dashboard
- [ ] Contractor Projects

**Test Plan for each page:**
1. Verify per-page selector appears
2. Change per-page count (e.g., 10 → 50)
3. Verify correct number of items displayed
4. Navigate between pages
5. Verify URL parameters preserved (filters, search, etc.)
6. Hard refresh browser (Cmd+Shift+R) to clear cache

---

## Implementation Notes

### Why This Approach?

1. **Reusable Component:** Single pagination template used across all pages ensures consistency
2. **Mixin Pattern:** Django best practice for adding pagination behavior to class-based views
3. **URL Parameter Preservation:** Pagination controls preserve all existing GET parameters
4. **Validation:** Per-page values are validated to prevent abuse
5. **Graceful Fallback:** Invalid per-page values fall back to default

### Design Decisions

**Per-Page Options:** 10, 25, 50, 100, 200
- Covers typical use cases from small lists to bulk operations
- Default varies by view (typically 20 or 50)

**Default Per-Page:**
- Most lists: 20 items
- Notifications: 50 items (higher default for inbox-style view)
- Project list: 50 items (already implemented this way)

**Component Features:**
- Item count display: "全293件中 1〜20件を表示"
- First/Last page buttons (⏮ ⏭)
- Prev/Next buttons with labels
- Page numbers with ellipsis for long ranges
- Font Awesome icons for better UX

### JavaScript Handler

The `changePerPage()` function:
```javascript
function changePerPage(perPage) {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('per_page', perPage);
    urlParams.delete('page');  // Reset to page 1 when changing per-page
    window.location.search = urlParams.toString();
}
```

This ensures:
- New per-page value is set
- Page resets to 1 (avoid showing page 5 when only 2 pages exist)
- All other URL parameters (filters, search) are preserved

---

## File References

### Created Files
- `order_management/mixins.py` (52 lines)
- `order_management/templates/order_management/includes/pagination_controls.html` (115 lines)
- `PAGINATION_IMPLEMENTATION_STATUS.md` (this file)

### Modified Files
- `order_management/views_client_company.py` (+1 import, +1 mixin)
- `order_management/views_cost.py` (+1 import, +2 mixins)
- `order_management/templates/order_management/contractor_detail.html` (pagination replaced)

### Remaining Files to Modify
- 5 backend view files
- 10 template files

---

## Quick Start Guide

**To continue the implementation:**

1. **Update Remaining Backend Views:**
   ```bash
   # For class-based views:
   # Add import: from .mixins import PerPageMixin
   # Add mixin to class: class MyView(LoginRequiredMixin, PerPageMixin, ListView)

   # For function-based views:
   # Add per_page logic (see contractor_list example above)
   # Add per_page to context
   ```

2. **Update Templates:**
   ```bash
   # Find existing pagination block (search for "pagination" or "page_obj")
   # Replace entire block with:
   {% include 'order_management/includes/pagination_controls.html' with page_obj=page_obj per_page=per_page %}
   ```

3. **Test:**
   ```bash
   python manage.py runserver
   # Visit each paginated page
   # Test per-page selector
   # Verify correct item counts
   ```

4. **Commit:**
   ```bash
   git add .
   git commit -m "Complete pagination per-page controls implementation"
   ```

---

## Commit History

```
da8c2db - Add pagination per-page controls (Phase 1: Mixin + 3 views + component)
```

**Next commit should include:**
- Remaining 5 backend views
- All 10 template updates
- Testing verification

---

## Estimated Completion Time

**Remaining work:** ~45 minutes
- Backend views: ~15 minutes (5 files × 3 min each)
- Templates: ~20 minutes (10 files × 2 min each)
- Testing: ~10 minutes (15 pages × <1 min each)

---

Last updated: 2025-12-22 15:00 JST
