# Construction Dispatch - Quick Reference Guide

## Quick Facts

| Aspect | Details |
|--------|---------|
| **Framework** | Django 5.2.6 |
| **Python** | 3.11+ |
| **Database** | SQLite (dev), PostgreSQL/MySQL (prod) |
| **Frontend** | Bootstrap 5, jQuery 3.7.0 |
| **Code Size** | 15,000+ lines Python, 78 HTML templates |
| **Primary App** | order_management (3,846 lines models.py) |
| **Secondary App** | subcontract_management (690 lines models.py) |
| **Models** | 30+ data models |
| **Views** | 40+ view functions across 20+ files |
| **Forms** | 13+ form classes |
| **Migrations** | 60 database migrations |

---

## File Navigation Reference

### Critical Files
| File | Purpose | Lines |
|------|---------|-------|
| `order_management/models.py` | Data models | 3,846 |
| `order_management/views.py` | Core views | 2,674 |
| `order_management/forms.py` | Form definitions | 609 |
| `order_management/urls.py` | URL routing | ~200 |
| `order_management/admin.py` | Admin config | ~200 |
| `order_management/user_roles.py` | RBAC system | ~100 |
| `construction_dispatch/settings.py` | Django config | ~150 |

### Service Layer
| File | Purpose |
|------|---------|
| `order_management/services/progress_step_service.py` | Progress step SSOT |
| `order_management/services/cashflow_service.py` | Payment calculations |

### Specialized View Modules
```
views_auth.py                    # Login, logout, auth
views_contractor.py              # Contractor CRUD
views_contractor_create.py       # Contractor creation
views_payment_management.py      # Payments, cashflow
views_ordering.py                # Orders, suppliers
views_cost.py                    # Cost analysis
views_calendar.py                # Timelines, schedules
views_report.py                  # Report generation
views_client_company.py          # Client management
views_approval.py                # Approval workflow
views_checklist.py               # Project checklists
views_work_type.py               # Work type management
views_rating_criteria.py         # Rating system
views_file.py                    # File management
views_material.py                # Material orders
views_comment.py                 # Comments & notes
views_mention.py                 # User mentions
views_notification.py            # Notifications
views_profile.py                 # User profiles
views_user_management.py         # User admin
views_permission.py              # Permission checks
views_landing.py                 # Landing page
```

---

## Key Architectural Patterns

### 1. SSOT (Single Source of Truth)
- **Progress Steps:** Defined in `STEP_TEMPLATES` dict in service layer
  - Models reference this for consistency
  - Database stores templates and instances
- **Cashflow:** Calculated from Project + Subcontract models
  - No redundant CashFlowTransaction calculations

### 2. Service Layer
```python
# Services encapsulate business logic
from order_management.services.progress_step_service import ensure_step_templates
from order_management.services.cashflow_service import calculate_payment_due_date
```

### 3. Role-Based Access Control (RBAC)
```python
from order_management.user_roles import UserRole, has_role, role_required

# Roles: 営業, 職人発注, 経理, 役員
# Decorator usage:
@role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
def accounting_view(request): ...
```

### 4. Model-View Organization
- **By Domain** (not by type)
- Each view module focuses on one feature area
- Makes navigation and maintenance easier

### 5. API Pattern
- Functions ending in `_api` return `JsonResponse`
- No REST framework (traditional Django views)
- Convention-based, not framework-enforced

### 6. Signals
```python
# Auto-triggered on model save
@receiver(post_save, sender=Project)
def check_overdue_notifications_on_save(sender, instance, created, **kwargs):
    # Automatic notification generation
```

---

## Database Schema Quick Reference

### Project (Central Model)
```
Project
├── management_no (auto: P251001)
├── site_name, site_address
├── work_type (FK → WorkType)
├── project_status (ネタ, A, B, 受注確定, NG)
├── order_amount, billing_amount (auto-calculated)
├── client_company (FK → ClientCompany)
├── approval_status (not_required, pending, approved, rejected)
├── is_draft (exclude from statistics)
├── progress_steps (Reverse FK ← ProjectProgressStep)
├── comments (Reverse FK ← Comment)
├── material_orders (Reverse FK ← MaterialOrder)
├── invoices (Reverse FK ← Invoice)
└── files (Reverse FK ← ProjectFile)
```

### Progress Management
```
ProgressStepTemplate (System-wide)
├── name (e.g., "立ち会い日")
├── icon, order, field_type
└── is_default

ProjectProgressStep (Per-Project)
├── project (FK → Project)
├── template (FK → ProgressStepTemplate)
├── order (sequence in this project)
├── is_active (included/excluded)
├── is_completed (checkbox)
└── value (JSONField: {scheduled_date, actual_date})
```

### Contractors & Workers
```
Contractor
├── contractor_type (individual, company, material)
├── skill_categories (JSONField)
├── skill_level, trust_level (1-5)
├── service_areas (JSONField)
└── success_rate, average_rating

InternalWorker
├── department (construction, sales, design, etc.)
├── position, email, phone
├── hourly_rate, specialties, certifications
└── is_active
```

### Clients & Payments
```
ClientCompany
├── company_name, representative
├── payment_cycle (monthly, bimonthly, weekly)
├── closing_day, payment_day, payment_offset_months
├── approval_threshold
├── default_key_handover_location
├── completion_report_notes (template)
└── projects (Reverse FK)

Invoice
├── project (FK → Project)
├── invoice_number, invoice_date, due_date
├── total_amount, paid_date
├── status (draft, issued, paid, cancelled)
└── items (Reverse FK ← InvoiceItem)
```

---

## Common Development Tasks

### Add a New Progress Step Type
```python
# 1. Update STEP_TEMPLATES in services/progress_step_service.py
STEP_TEMPLATES = {
    'new_step': {
        'name': '新しいステップ',
        'icon': 'fas fa-icon',
        'order': 11,
        'is_default': False,
        'field_type': 'date'
    }
}

# 2. Service auto-creates DB templates
from order_management.services.progress_step_service import ensure_step_templates
ensure_step_templates()
```

### Add a New Project Status
```python
# In models.py, update Project.project_status choices
PROJECT_STATUS_CHOICES = [
    ('ネタ', 'ネタ'),
    ('A', 'A'),
    ('B', 'B'),
    ('受注確定', '受注確定'),
    ('NG', 'NG'),
    ('新しいステータス', '新しいステータス'),  # Add here
]
```

### Create a New View
```python
# 1. Create views_feature.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .user_roles import role_required, UserRole

@login_required
@role_required(UserRole.SALES)
def feature_list(request):
    # Implementation
    return render(request, 'order_management/feature_list.html', context)

# 2. Add to urls.py
from .views_feature import feature_list
urlpatterns += [
    path('feature/', feature_list, name='feature_list'),
]

# 3. Create template
# order_management/templates/order_management/feature_list.html
```

### Add a New Form Field
```python
# In forms.py, ProjectForm
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['field1', 'field2', 'new_field']  # Add field
        widgets = {
            'new_field': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter value'
            })
        }
```

---

## URL Routing Structure

```
/orders/login/                              → HeadquartersLoginView
/orders/logout/                             → HeadquartersLogoutView
/orders/dashboard/                          → dashboard()
/orders/list/                               → project_list()
/orders/create/                             → project_create()
/orders/<id>/                               → project_detail()
/orders/<id>/edit/                          → project_update()
/orders/<id>/delete/                        → project_delete()
/orders/<id>/progress/                      → update_progress()

/orders/contractor/                         → ContractorDashboardView
/orders/contractor/create/                  → ContractorCreateView
/orders/contractor/external/                → ExternalContractorManagementView

/orders/payment/                            → PaymentManagementView
/orders/cost/                               → cost_dashboard()
/orders/calendar/                           → ConstructionCalendarView
/orders/report/                             → ReportDashboardView

/admin/                                     → Django Admin

/subcontracts/                              → Subcontract management
```

---

## Testing & Development

### Run Development Server
```bash
python manage.py runserver
# Access: http://localhost:8000/
```

### Database Operations
```bash
python manage.py migrate                    # Apply migrations
python manage.py makemigrations             # Create new migrations
python manage.py createsuperuser            # Create admin user
python manage.py shell                      # Django shell
python manage.py collectstatic              # Collect static files
```

### Load Test Data
```bash
python create_test_contractors.py           # Load contractor test data
```

### Run Tests
```bash
python manage.py test                       # Run unit tests
pytest                                      # Run pytest (if configured)
```

---

## Key Dependencies

### Required Packages
```
Django==5.2.6              # Web framework
django-bootstrap4==23.2    # Bootstrap integration
gunicorn==21.2.0          # Production server
whitenoise==6.11.0        # Static file serving
python-dateutil==2.9.0    # Date utilities
Pillow==11.3.0            # Image processing
requests==2.32.5          # HTTP requests
reportlab==4.2.5          # PDF generation
```

### Frontend Libraries (CDN)
```
Bootstrap 5.3.0            # CSS framework
jQuery 3.7.0              # DOM manipulation
Font Awesome 6.4.0        # Icons
Toastr.js                 # Notifications
Chart.js                  # Data visualization
```

---

## Configuration Quick Checks

### settings.py
- `DEBUG = True` (development only!)
- `LANGUAGE_CODE = 'ja'` (Japanese)
- `TIME_ZONE = 'Asia/Tokyo'`
- `NUMBER_GROUPING = 3` (1,000,000 format)
- `DATABASE = sqlite3` (dev) or postgresql (prod)

### Security Checklist
- [ ] Change SECRET_KEY in production
- [ ] Set DEBUG=False in production
- [ ] Configure ALLOWED_HOSTS for domain
- [ ] Use environment variables for secrets
- [ ] Configure HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure email for notifications
- [ ] Review user permissions
- [ ] Enable CSRF middleware (default)
- [ ] Enable security headers

---

## Common Issues & Solutions

### Draft Projects Excluded from Stats
- `is_draft=False` filter is required in most queries
- Check `views.py` dashboard() for example filtering

### Progress Calculation Issues
- Check `get_progress_status()` method in Project model
- Verify ProjectProgressStep instances exist
- Use `ensure_step_templates()` to reset templates

### Payment Date Calculation
- Review `calculate_payment_due_date()` in cashflow_service.py
- Check closing_day, payment_day, payment_offset_months

### Role-Based Access
- Verify UserProfile.roles contains user role
- Superusers bypass all checks
- Check decorator on view function

---

## Resources

| Document | Purpose |
|----------|---------|
| `/ARCHITECTURE_ANALYSIS.md` | Complete architecture deep-dive |
| `/README.md` | Project overview & setup |
| `/プロジェクト仕様書.md` | Detailed specifications |
| `/ISSUES_FIX_SUMMARY.md` | Known issues & fixes |
| `/CLAUDE.md` | Development constraints |

---

**Last Updated:** December 8, 2025
**Analysis Version:** 1.0
