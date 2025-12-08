# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**案件管理・経理管理システム (Construction Dispatch & Accounting Management System)**

A Django 5.2.6 application for construction project management, accounting, and subcontractor coordination. Built for Japanese construction companies with complete Japanese localization.

**Tech Stack:** Django 5.2.6, Python 3.11+, Bootstrap 5, jQuery 3.7.0, SQLite (dev) / PostgreSQL (prod)

---

## Essential Commands

### 🚀 Quick Start with Utility Scripts

**Recommended:** Use the utility scripts in `scripts/` directory for streamlined workflow:

```bash
# First time setup
./scripts/init.sh           # Install deps, run migrations, setup environment

# Daily workflow
./scripts/status.sh         # Check system status
./scripts/start.sh          # Start development server
./scripts/test.sh           # Run test suite
./scripts/lint.sh           # Run code quality checks

# Troubleshooting
./scripts/reset.sh          # Reset environment to clean state
```

**Benefits:**
- ✅ Prevents repeated work when continuing from fresh context
- ✅ Gracefully handles errors and edge cases
- ✅ Provides colored output and clear status messages
- ✅ Includes health checks and validations

**See:** `scripts/README.md` for detailed documentation.

---

### Development Server
```bash
# Start development server (port 8000)
python manage.py runserver

# Start on specific port
python manage.py runserver 8000

# Kill existing server and restart
lsof -ti:8000 | xargs kill -9 2>/dev/null; python manage.py runserver 8000 &
```

### Database Operations
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Apply specific app migrations
python manage.py migrate order_management
python manage.py migrate subcontract_management

# Show migration status
python manage.py showmigrations

# Create superuser
python manage.py createsuperuser
```

### Static Files
```bash
# Collect static files for production
python manage.py collectstatic --no-input

# Clear and recollect
rm -rf staticfiles/
python manage.py collectstatic --no-input
```

### Django Shell
```bash
# Access Django shell
python manage.py shell

# Common shell operations:
from order_management.models import Project, Customer
from subcontract_management.models import Contractor
from django.contrib.auth.models import User
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test order_management
python manage.py test subcontract_management

# Run specific test class
python manage.py test order_management.tests.TestProjectModel

# Run with verbosity
python manage.py test --verbosity=2
```

---

## Architecture Patterns

### 1. Single Source of Truth (SSOT) Pattern

**Critical:** The project uses SSOT architecture for progress steps and cashflow data. Always use the service layer, never access raw data directly.

**Progress Steps:**
```python
# ALWAYS USE:
from order_management.services.progress_step_service import (
    get_step,
    set_step_scheduled_date,
    complete_step,
    is_step_completed
)

# Get step data
attendance_step = get_step(project, 'attendance')
scheduled_date = get_step_scheduled_date(project, 'survey')

# Update step
set_step_scheduled_date(project, 'estimate', '2025-12-10')
complete_step(project, 'construction_start', completed=True)

# NEVER ACCESS DIRECTLY:
# project.attendance_date  # ❌ DEPRECATED
# project.survey_date      # ❌ DEPRECATED
```

**Cashflow Calculations:**
```python
# ALWAYS USE:
from order_management.services.cashflow_service import calculate_cashflow_entries

# Calculate cashflow
entries = calculate_cashflow_entries(project)
# Returns: List of {date, type, amount, description, cumulative_balance}

# NEVER calculate manually
```

**Step Keys:** `'attendance'`, `'survey'`, `'estimate'`, `'construction_start'`, `'completion'`, `'contract'`, `'invoice'`, `'permit_application'`, `'material_order'`, `'inspection'`

### 2. View Organization Pattern

Views are organized by **domain/feature**, not by HTTP method:

```
order_management/
├── views.py              # Core project CRUD
├── views_accounting.py   # Accounting dashboard, passbook, receipts
├── views_approval.py     # Approval workflow
├── views_contractor.py   # Contractor management
├── views_cost.py         # Cost management
├── views_client.py       # Client company management
├── views_checklist.py    # Checklist management
├── views_file.py         # File upload/management
├── views_material.py     # Material orders
├── views_payment_management.py  # Payment tracking
├── views_search.py       # Search functionality
└── views_*.py            # 20+ specialized modules
```

**Pattern:** Each domain gets its own view module. New features should follow this pattern.

### 3. Role-Based Access Control (RBAC)

Four user roles with distinct permissions:

```python
from order_management.user_roles import UserRole, require_role

# Roles (defined in user.user_role field):
UserRole.SALES       = 'sales'        # 営業: Create projects, manage customers
UserRole.DISPATCH    = 'dispatch'     # 配車: Assign contractors, manage schedule
UserRole.ACCOUNTING  = 'accounting'   # 経理: Financial operations
UserRole.EXECUTIVE   = 'executive'    # 役員: Full access + approvals

# View protection:
@require_role([UserRole.ACCOUNTING, UserRole.EXECUTIVE])
def accounting_dashboard(request):
    # Only accounting & executive can access
    pass

# Template usage:
{% load role_tags %}
{% if user|has_role:'accounting' %}
    <a href="{% url 'accounting_dashboard' %}">経理ダッシュボード</a>
{% endif %}
```

### 4. Service Layer Pattern

**When to use:** For complex calculations, data transformations, or multi-model operations.

```python
# order_management/services/
├── progress_step_service.py  # Progress step SSOT
├── cashflow_service.py       # Cashflow calculations
└── (add new services here)

# Example service structure:
def calculate_complex_business_logic(project):
    """
    Service function for complex calculations.

    Args:
        project: Project instance

    Returns:
        dict: Calculation results
    """
    # Logic here
    return results
```

### 5. Signal-Based Automation

Signals are used for automatic notifications and data updates:

```python
# order_management/signals.py
@receiver(post_save, sender=Project)
def auto_create_overdue_notifications(sender, instance, **kwargs):
    """Auto-generate notifications when work_end_date is overdue"""
    # Triggered automatically on Project save
    pass
```

**Registered in:** `order_management/apps.py` → `ready()` method

### 6. Template Architecture

**Base Template:** `order_management/templates/order_management/base.html` (500+ lines)
- Bootstrap 5 navigation
- Role-based menu rendering
- Common JavaScript libraries (jQuery 3.7.0, Bootstrap 5.3.0, Font Awesome 6.4.0)

**Template Structure:**
```
templates/order_management/
├── base.html                    # Base layout with nav
├── dashboard.html               # Main dashboard
├── project_list.html            # Project listing
├── project_detail.html          # Project details (8000+ lines)
├── project_form.html            # Project create/edit
├── includes/                    # Reusable components
│   ├── contractor_management_panel.html
│   ├── improved_implementation_modal.html
│   └── *.html
└── partials/                    # Partial templates
```

**Pattern:** Large forms use includes for maintainability.

---

## Data Model Architecture

### Core Models

**Project Model** (`order_management/models.py`):
```python
class Project(models.Model):
    # Basic Info
    management_no       # 管理番号 (e.g., "A-2024-001")
    site_name          # 案件名
    order_date         # 受注日

    # Customer
    customer           # FK to Customer

    # Status
    status             # 'active', 'completed', 'on_hold', 'cancelled', 'ng'
    is_draft          # Draft projects (not fully created)

    # Financial
    order_amount       # 受注金額
    cost_amount        # 原価金額
    profit_amount      # 粗利額 (calculated)

    # Progress Steps (DEPRECATED - use ProjectProgressStep)
    # attendance_date, survey_date, etc. → Use service layer

    # Approval
    approval_status    # 'pending', 'approved', 'rejected'
    approved_by        # FK to User

    # Relations
    projectprogressstep_set  # Progress steps (SSOT)
    subcontract_set         # Subcontracts
    payment_set             # Payments
```

**ProjectProgressStep Model** (SSOT for progress):
```python
class ProjectProgressStep(models.Model):
    project            # FK to Project
    template           # FK to ProgressStepTemplate
    order              # Display order
    is_active         # Active/archived
    is_completed      # Completion status
    completed_date    # When completed
    value             # JSONField: {scheduled_date, actual_date, assignees}
```

**Subcontract Model** (`subcontract_management/models.py`):
```python
class Subcontract(models.Model):
    project            # FK to Project
    contractor         # FK to Contractor
    internal_worker    # FK to InternalWorker
    contract_amount    # Contract amount
    invoice_amount     # Invoice amount
    payment_status     # 'unpaid', 'partially_paid', 'paid'
    work_type         # 'attendance', 'survey', 'construction_start', etc.
```

### Model Relationships

```
Customer (1) ──── (N) Project
Project (1) ──── (N) ProjectProgressStep
Project (1) ──── (N) Subcontract
Project (1) ──── (N) Payment
Project (1) ──── (N) MaterialOrder
Project (1) ──── (N) ProjectFile

ProgressStepTemplate (1) ──── (N) ProjectProgressStep

Contractor (1) ──── (N) Subcontract
InternalWorker (1) ──── (N) Subcontract

User (1) ──── (N) Project (via approved_by, sales_rep)
```

---

## Frontend Patterns

### JavaScript Structure

**Large inline scripts in templates** (e.g., `project_detail.html` has 8000+ lines including JavaScript)

**Key JavaScript Patterns:**

1. **Form Field Syncing:**
```javascript
// Sync form fields to progress step display
function syncFormFieldsToSteps() {
    // Updates step UI based on form inputs
}

// Update overall progress
function updateProgressTimeline() {
    // Recalculates completion percentage
}
```

2. **Complex Step Management:**
```javascript
// Get step status (attendance, survey, construction_start, completion)
function getComplexStepStatus(stepData, stepElement) {
    // Returns {completed, statusText, status}
}

// Field naming convention:
// dynamic_field_{step_key}_{field_name}
// Example: dynamic_field_step_attendance_scheduled_date
```

3. **Badge Display Pattern:**
```javascript
// ALL steps use badge style for consistency:
'<span class="badge bg-warning">立ち会い待ち</span> 12/8'
'<span class="badge bg-success">完了</span> 12/8'
'<span class="badge bg-secondary">未完了</span>'

// NOT icon style:
// '<i class="fas fa-calendar me-1"></i>予定: 12/8'  // ❌ OLD STYLE
```

### UI Coding Rules

**CRITICAL - NO BROWSER POPUPS:**
```javascript
// ❌ NEVER USE:
alert('message');
confirm('Are you sure?');
prompt('Enter value:');

// ✅ ALWAYS USE:
// - Bootstrap modals
// - Inline messages
// - Toast notifications
// - Console logging for debugging
```

---

## Common Development Tasks

### Adding a New Progress Step

1. **Define step in service:**
```python
# order_management/services/progress_step_service.py
STEP_TEMPLATES = {
    'new_step': {
        'name': '新しいステップ',
        'icon': 'fas fa-star',
        'order': 11,
        'is_default': False,
        'field_type': 'date'
    }
}
```

2. **Add to frontend:**
```javascript
// In project_detail.html or project_form.html
// Add to available steps section
```

3. **Test the service layer:**
```python
from order_management.services.progress_step_service import set_step_scheduled_date
set_step_scheduled_date(project, 'new_step', '2025-12-15')
```

### Adding a New View Module

1. **Create view module:**
```python
# order_management/views_new_feature.py
from django.shortcuts import render
from order_management.user_roles import require_role, UserRole

@require_role([UserRole.DISPATCH])
def new_feature_view(request):
    return render(request, 'order_management/new_feature.html')
```

2. **Register URL:**
```python
# order_management/urls.py
from order_management import views_new_feature

urlpatterns = [
    path('new-feature/', views_new_feature.new_feature_view, name='new_feature'),
]
```

3. **Create template:**
```html
{% extends 'order_management/base.html' %}
{% block content %}
    <!-- Feature content -->
{% endblock %}
```

### Working with Draft Projects

Draft projects allow partial saves:

```python
# Create draft
project = Project.objects.create(
    management_no=generate_management_no(),
    site_name='未確定',
    is_draft=True,
    status='active'
)

# Convert to full project
project.is_draft = False
project.site_name = '実際の案件名'
project.save()

# List drafts
drafts = Project.objects.filter(is_draft=True)
```

**URL:** `/orders/drafts/` → Lists all draft projects

### Adding Custom Template Filters

```python
# order_management/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def your_filter(value, arg):
    """Your filter description"""
    return processed_value
```

**Usage:**
```html
{% load custom_filters %}
{{ value|your_filter:"argument" }}
```

---

## Database Considerations

### Migration Workflow

**60 existing migrations** - Always create new migrations, never edit old ones:

```bash
# 1. Make model changes
# 2. Create migration
python manage.py makemigrations order_management --name descriptive_name

# 3. Review migration file
# 4. Test locally
python manage.py migrate

# 5. Commit migration file with code changes
```

### JSONField Usage

Several models use `JSONField` for flexible data storage:

```python
# ProjectProgressStep.value
{
    "scheduled_date": "2025-12-10",
    "actual_date": "2025-12-11",
    "assignees": ["田中", "鈴木"]
}

# Project.custom_fields (if added)
# Use JSONField for dynamic form fields
```

**Query JSONFields:**
```python
# Filter by JSON key
steps = ProjectProgressStep.objects.filter(
    value__scheduled_date='2025-12-10'
)

# Be careful: JSON queries vary by database (SQLite vs PostgreSQL)
```

---

## Important File Locations

### Key Configuration Files
- `construction_dispatch/settings.py` - Django settings
- `construction_dispatch/urls.py` - Root URL config
- `requirements.txt` - Dependencies (8 packages)

### Service Layer (SSOT)
- `order_management/services/progress_step_service.py` - **Use this for all progress step operations**
- `order_management/services/cashflow_service.py` - **Use this for cashflow calculations**

### View Modules (20+ files)
- `order_management/views.py` - Core project CRUD
- `order_management/views_accounting.py` - Financial views
- `order_management/views_contractor.py` - Contractor management
- `order_management/views_payment_management.py` - Payment tracking

### Utility Modules
- `order_management/user_roles.py` - RBAC definitions
- `order_management/notification_utils.py` - Notification generation
- `order_management/report_utils.py` - Report generation
- `order_management/pdf_utils.py` - PDF export

### Large Templates
- `order_management/templates/order_management/base.html` (500+ lines)
- `order_management/templates/order_management/project_detail.html` (8000+ lines)
- `order_management/templates/order_management/project_form.html` (1500+ lines)

---

## Testing Strategy

### Manual Testing Checklist

When modifying progress steps or cashflow:

1. **Test SSOT service layer:**
   - Create project
   - Set scheduled dates via service
   - Complete steps via service
   - Verify data in `ProjectProgressStep` table

2. **Test UI updates:**
   - Hard refresh (Cmd+Shift+R) to clear cache
   - Verify badge display consistency
   - Check that all steps show correct status

3. **Test role permissions:**
   - Login as each role (sales, dispatch, accounting, executive)
   - Verify menu visibility
   - Test access restrictions

4. **Test draft workflow:**
   - Create draft project
   - Verify appears in `/orders/drafts/`
   - Convert to full project
   - Verify removed from drafts

### Browser Caching

**Always hard refresh after changes:**
```
Chrome/Edge: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)
Firefox: Ctrl+F5 / Cmd+Shift+R
Safari: Cmd+Option+R
```

Static files are cached. Run `collectstatic` after JS/CSS changes:
```bash
python manage.py collectstatic --no-input
```

---

## Code Style Guidelines

### Python Style

- **Follow PEP 8** for Python code
- **Use Japanese comments** for business logic (業務ロジック)
- **Use English** for technical comments
- **Docstrings:** Write in English for reusable functions

```python
def calculate_profit(order_amount, cost_amount):
    """
    Calculate profit amount.

    Args:
        order_amount: 受注金額
        cost_amount: 原価金額

    Returns:
        Decimal: 粗利額
    """
    # 粗利 = 受注金額 - 原価金額
    return order_amount - cost_amount
```

### JavaScript Style

- **Console logging:** Use for debugging (no alerts!)
- **Consistent naming:** Use camelCase for JS, snake_case for Python
- **Field naming pattern:** `dynamic_field_{step_key}_{field_name}`

```javascript
// Good: Console logging
console.log('🔍 Debug info:', data);

// Bad: Browser popups
alert('Debug info');  // ❌ NEVER USE
```

### Template Style

- **Use includes** for reusable components
- **Load templatetags** at top of file
- **Role checks** via `{% if user|has_role:'role_name' %}`

```html
{% load role_tags %}
{% load custom_filters %}
{% load humanize %}

{% if user|has_role:'accounting' %}
    <!-- Accounting-only content -->
{% endif %}
```

---

## Troubleshooting

### Common Issues

**"Field not found" errors in progress steps:**
```
Solution: Check field naming convention
- Use: dynamic_field_step_survey_scheduled_date
- Not: dynamic_field_survey_scheduled_date (missing step_ prefix)
```

**Progress steps not showing correct status:**
```
Solution:
1. Check switch statement in getComplexStepStatus() has both:
   case 'step_key':
   case 'key':  // Legacy support
2. Hard refresh browser
3. Run collectstatic
```

**"Unknown step key" errors:**
```
Solution: Ensure step is defined in STEP_TEMPLATES in progress_step_service.py
```

**Static files not loading:**
```bash
# Collect static files
python manage.py collectstatic --no-input

# Restart server
lsof -ti:8000 | xargs kill -9 2>/dev/null
python manage.py runserver 8000
```

**Migration conflicts:**
```bash
# Show migration status
python manage.py showmigrations

# If conflict, fake the migration
python manage.py migrate --fake order_management 0060

# Then apply new migrations
python manage.py migrate
```

---

## Security Notes

- **CSRF Protection:** Enabled by default, required for all POST requests
- **Role Checks:** Use `@require_role()` decorator on all views
- **File Uploads:** Currently stored in `media/`, validate file types in production
- **SECRET_KEY:** Change in production, store in environment variable
- **DEBUG:** Set to `False` in production

---

## 📝 Session Progress Tracking

**CRITICAL:** This project uses `progress.md` for session-by-session tracking. Git history = true memory.

### Before Starting Work

**1. Read progress.md FIRST:**
```bash
cat progress.md
# Check the latest session to understand current state
```

**2. Check git status:**
```bash
git status
./scripts/status.sh
```

**3. Review uncommitted changes:**
- Understand what work is in progress
- Decide whether to commit, stash, or continue

### During Work

**Track your changes mentally:**
- What features you're implementing
- What bugs you're fixing
- What files you're modifying
- What issues you discover

### After Completing Work

**1. Update progress.md:**
- Add new session entry
- Document what was done
- List what's still broken
- Set next tasks
- Add warnings/blockers

**2. Commit your work:**
```bash
# Commit feature changes
git add <files>
git commit -m "Session X: Brief description"

# Commit progress.md update
git add progress.md
git commit -m "Update progress.md for Session X"
```

### Session Entry Template

```markdown
## Session X: [Brief Description]
**Date:** YYYY-MM-DD
**Branch:** main

### 📋 What Was Worked On
- Feature/bug description
- Files modified

### ✅ Features Implemented
- Completed features

### ⚠️ What Is Missing/Broken
- Known issues

### 🎯 Next Tasks
1. Immediate next steps

### ⚡ Warnings & Blockers
- Critical issues
```

### Why This Matters

- ✅ **Context Continuity** - Next Claude instance knows exactly where you left off
- ✅ **No Repeated Work** - Clear record of what's already done
- ✅ **Git History = Memory** - Permanent record in version control
- ✅ **Team Coordination** - Human developers can also track progress

---

## Additional Documentation

For comprehensive details, see:
- `progress.md` - **Session tracking (READ THIS FIRST!)** ⭐
- `README.md` - Quick start guide (Japanese)
- `ARCHITECTURE_ANALYSIS.md` - Deep architectural analysis (742 lines)
- `QUICK_REFERENCE.md` - Common tasks reference (402 lines)
- `DOCUMENTATION_INDEX.md` - Documentation navigation
- `features.json` - Complete feature catalog (52 KB)
- `scripts/README.md` - Utility scripts guide

---

## Quick Reference URLs

**Development:**
- Dashboard: `http://localhost:8000/orders/dashboard/`
- Project List: `http://localhost:8000/orders/list/`
- Draft Projects: `http://localhost:8000/orders/drafts/`
- Accounting: `http://localhost:8000/orders/accounting/`
- Passbook: `http://localhost:8000/orders/passbook/`
- Admin: `http://localhost:8000/admin/`

**API-like Endpoints:**
- Update progress: `POST /orders/<id>/update-progress/`
- Approve project: `POST /orders/<id>/approve/`
- Upload file: `POST /orders/<id>/upload-file/`
- Generate report: `GET /orders/reports/financial/?format=pdf`

---

## Contact & Support

For questions about architecture or development patterns, refer to:
1. This CLAUDE.md file first
2. ARCHITECTURE_ANALYSIS.md for deep dives
3. QUICK_REFERENCE.md for code examples
4. Existing code patterns in the codebase

**Last Updated:** December 8, 2025
- Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Therefore, do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully, even if the end of your budget is approaching. Never artificially stop any task early regardless of the context remaining.