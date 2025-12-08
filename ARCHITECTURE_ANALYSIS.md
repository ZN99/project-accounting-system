# Construction Dispatch Project - Comprehensive Architecture Analysis

**Analysis Date:** December 8, 2025
**Django Version:** 5.2.6
**Python:** 3.11+
**Database:** SQLite (Development) / PostgreSQL or MySQL (Production)
**Frontend:** Bootstrap 5, jQuery 3.7.0, Font Awesome 6.4.0

---

## 1. PROJECT STRUCTURE & MAIN APPS

### Directory Layout
```
project-accounting-system/
├── construction_dispatch/           # Django project configuration
│   ├── settings.py                 # Project settings (Django 5.2)
│   ├── urls.py                     # Root URL configuration
│   ├── wsgi.py                     # WSGI application
│   └── asgi.py                     # ASGI configuration
│
├── order_management/                # PRIMARY APP - Project & Accounting Management
│   ├── models.py (3,846 lines)     # 30+ model classes
│   ├── views.py (2,674 lines)      # Main view functions
│   ├── views_*.py (20+ files)      # Specialized view modules
│   ├── forms.py (609 lines)        # 13+ Django forms
│   ├── urls.py                     # URL routing
│   ├── admin.py                    # Django admin configuration
│   ├── apps.py                     # App configuration with signals
│   ├── signals.py                  # Django signal handlers
│   ├── user_roles.py               # Role-based access control (RBAC)
│   ├── utils.py (30 lines)         # Utility functions
│   ├── services/                   # Service layer (SSOT pattern)
│   │   ├── progress_step_service.py # Progress step management
│   │   ├── cashflow_service.py     # Cashflow calculations
│   │   └── __init__.py
│   ├── templatetags/               # Custom template filters & tags
│   │   ├── custom_filters.py
│   │   ├── role_tags.py
│   │   └── __init__.py
│   ├── templates/                  # 78 HTML templates
│   │   └── order_management/
│   │       ├── base.html           # Base template (500+ lines)
│   │       ├── dashboard.html
│   │       ├── project_list.html
│   │       ├── project_detail.html
│   │       ├── project_form.html
│   │       ├── project_draft_list.html
│   │       ├── includes/           # Template includes & modals
│   │       ├── partials/           # Partial templates
│   │       ├── cost/               # Cost management templates
│   │       ├── client_company/     # Client company templates
│   │       ├── approval/           # Approval workflow templates
│   │       ├── checklist/          # Checklist templates
│   │       ├── file/               # File management templates
│   │       ├── material/           # Material order templates
│   │       ├── rating_criteria/    # Rating templates
│   │       └── review/             # Review templates
│   ├── migrations/ (60 files)      # Database migrations
│   ├── management/                 # Django management commands
│   ├── archived/                   # Archived code modules
│   └── pdf_utils.py, report_utils.py, notification_utils.py
│
├── subcontract_management/          # SECONDARY APP - Subcontractor Management
│   ├── models.py (690 lines)       # Subcontract, Contractor, InternalWorker
│   ├── views.py
│   ├── views_skills.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/                 # Database migrations
│   └── templates/                  # Subcontract templates
│
├── static/                          # Static assets
│   └── images/
├── media/                           # User-uploaded files
│   ├── avatars/
│   ├── invoices/
│   ├── project_files/
│   └── purchase_orders/
├── staticfiles/                     # Collected static files (production)
│
├── manage.py                        # Django CLI
├── requirements.txt                 # Python dependencies (8 packages)
├── db.sqlite3                       # Development database
└── Documentation files (.md)
```

### Key Django Apps (Registered in settings.py)
1. **django.contrib.admin** - Django Admin Interface
2. **django.contrib.auth** - User authentication
3. **django.contrib.contenttypes** - Content type framework
4. **django.contrib.sessions** - Session management
5. **django.contrib.messages** - Message framework
6. **django.contrib.staticfiles** - Static files handling
7. **django.contrib.humanize** - Number formatting (3-digit separators)
8. **bootstrap4** - Bootstrap integration
9. **order_management** - PRIMARY APP (案件管理・経理管理)
10. **subcontract_management** - Subcontractor management (下請け管理)

---

## 2. KEY ARCHITECTURAL PATTERNS

### 2.1 SSOT (Single Source of Truth) Pattern

The project implements SSOT in several areas:

#### Progress Step Management (Service Layer)
- **File:** `order_management/services/progress_step_service.py`
- **Purpose:** Centralized management of project progress steps
- **Key Function:** `ensure_step_templates()` - Creates/manages step templates in DB
- **Central Data Structure:** `STEP_TEMPLATES` dictionary defines:
  - Default Steps: attendance, survey, estimate, construction_start, completion
  - Optional Steps: contract, invoice, permit_application, material_order, inspection
  - Each with: name, icon, order, field_type, default status
- **Impact:** Model methods reference this service to calculate progress
- **Database Models:**
  - `ProgressStepTemplate` - Defines available step templates
  - `ProjectProgressStep` - Stores actual project progress steps (foreign key to Project)

#### Cashflow Calculations (Service Layer)
- **File:** `order_management/services/cashflow_service.py`
- **Purpose:** Calculate incoming/outgoing payments from Project and Subcontract models
- **Key Functions:**
  - `get_month_range()` - Date range calculations
  - `calculate_payment_due_date()` - Payment scheduling
  - `get_outgoing_paid_sites()` - Paid contractor amounts
  - `get_incoming_received_api()` - Received client payments
- **Architecture:** Derives data directly from Project and Subcontract models (NOT from CashFlowTransaction)
- **Note:** CashFlowTransaction model deprecated but retained for legacy

### 2.2 Service Layer Pattern

**Location:** `order_management/services/`

Three specialized service modules provide business logic separation:

1. **progress_step_service.py** (~200 lines)
   - Manages project progress step templates and instances
   - Handles JSON serialization/deserialization of step data
   - Ensures DB consistency for step templates

2. **cashflow_service.py** (~300 lines)
   - Calculates payment flows for accounting
   - Implements payment date calculation logic
   - Aggregates data from multiple models

### 2.3 Role-Based Access Control (RBAC)

**File:** `order_management/user_roles.py`

```python
# Role Definitions
UserRole.SALES = '営業'              # Sales & Customer Relations
UserRole.WORKER_DISPATCH = '職人発注' # Worker Dispatch & Construction Management
UserRole.ACCOUNTING = '経理'          # Financial Management & Payments
UserRole.EXECUTIVE = '役員'           # Executive Management
```

**Implementation:**
- `has_role(user, role)` - Check single role
- `has_any_role(user, roles)` - Check multiple roles (OR)
- `has_all_roles(user, roles)` - Check multiple roles (AND)
- Decorators: `@role_required()`, `@sales_required()`, `@accounting_required()`, etc.
- Integration: `UserProfile.roles` (JSONField) stores user roles
- Superusers bypass all checks

### 2.4 Model-View-Template (MVT) Architecture

**View Organization Strategy:** Files by Domain (Not by Type)

Main Views Structure:
- `views.py` (2,674 lines) - Core project management views
- `views_auth.py` - Authentication views
- `views_contractor.py` - Contractor management
- `views_contractor_create.py` - Contractor creation workflow
- `views_payment_management.py` - Payment/cashflow views
- `views_ordering.py` - Order and supplier management
- `views_cost.py` - Cost analysis (fixed & variable)
- `views_calendar.py` - Calendar and timeline views
- `views_report.py` - Report generation
- `views_client_company.py` - Client company management
- `views_approval.py` - Approval workflow
- `views_checklist.py` - Checklist management
- ... and 15+ more specialized view modules

**Pattern Benefits:**
- Domain-focused organization
- Reduces cognitive load per file
- Clear separation of concerns
- Easy to locate related functionality

### 2.5 Template Hierarchy & Includes

**Base Template:** `order_management/templates/order_management/base.html`
- Navigation bar with role-based menu items
- Bootstrap 5 CSS/JS
- jQuery 3.7.0
- Font Awesome 6.4.0
- Toastr notifications
- Custom CSS variables for theming

**Template Organization:**
```
templates/order_management/
├── base.html                    # Master layout
├── includes/                    # Reusable components
│   ├── contractor_*.html
│   ├── contractor_management_panel.html
│   ├── contractor_management_panel_script.html
│   ├── improved_implementation_modal.html
│   └── improved_implementation_modal_script.html
├── partials/                    # Fragment templates
├── cost/                        # Cost management domain
├── client_company/              # Client management domain
├── approval/                    # Approval workflow domain
└── [other domains]/
```

### 2.6 API Pattern (JSON Response)

**Design:** Traditional Django view functions returning JsonResponse
- **Not REST API** (no DRF)
- **Convention:** Functions ending in `_api` return JsonResponse
- **Examples:**
  - `staff_api()` - GET staff/employee list
  - `contractor_api()` - GET contractor list
  - `project_api_list()` - GET projects with filters
  - `mention_users_api()` - GET users for mentions
  - `calendar_events_api()` - GET calendar events
  - `performance_monthly_api()` - GET performance data
  - `bulk_update_payment_status_api()` - Update payment statuses

**Error Handling:**
- Returns JSON with `success: bool`, `message: str`
- HTTP status codes: 200, 400, 404, 500
- CSRF protection on POST endpoints

### 2.7 Signal-Based Automation

**File:** `order_management/signals.py`

**Implemented:**
- `@receiver(post_save, sender=Project)`
- Automatically checks and creates overdue completion notifications
- Triggered on project save
- Used for maintaining data consistency without direct view coupling

---

## 3. DATABASE MODELS & RELATIONSHIPS

### Core Project Model Structure (30+ Models)

#### Project (Central Model)
- **Lines:** 900+
- **Key Fields:**
  - `management_no` (auto-numbered: P251001, P251002, etc.)
  - `site_name`, `site_address`
  - `work_type` (FK to WorkType)
  - `project_status` (choices: ネタ, A, B, 受注確定, NG)
  - `order_amount` (受注金額)
  - `billing_amount` (自動計算: order_amount + parking_fee + expenses)
  - Dates: `contract_date`, `completion_date`, `payment_due_date`
  - `client_company` (FK to ClientCompany) - Phase 8
  - `approval_status` - Approval workflow
  - `is_draft` (Boolean) - Draft projects excluded from queries
  - **Progress Step FK:** `progress_steps` (reverse relation to ProjectProgressStep)
- **Key Methods:**
  - `generate_management_no()` - Auto-numbering
  - `get_work_progress_percentage()` - Calculate progress from steps
  - `get_work_phase()` - Determine current phase
  - `get_progress_status()` - Return phase + color + percentage
  - `get_progress_details()` - Detailed step breakdown

#### ProgressStepTemplate (System-wide)
- Defines available progress step types
- Fields: `name`, `icon`, `order`, `is_default`, `field_type`
- Examples: '立ち会い日', '現調日', '見積書発行日', '着工日', '完工日'

#### ProjectProgressStep (Per-Project)
- FK to Project
- FK to ProgressStepTemplate
- `order` (step sequence)
- `is_active` (included in this project)
- `is_completed` (manual checkbox)
- `value` (JSONField: {scheduled_date, actual_date, ...})

#### Contractor (Subcontract Partner)
- **Type Choices:** individual(個人職人), company(協力会社), material(資材)
- **Skills:** skill_categories (JSONField), skill_level, specialties
- **Trust Level:** 1-5 scale
- **Performance:** total_projects, success_rate, average_rating
- **Coverage:** service_areas (JSONField)
- Relations: Many projects via Subcontract

#### InternalWorker (Internal Staff)
- **Departments:** construction, sales, design, management, quality, safety
- **Roles:** name, position, email, phone
- **Capabilities:** hourly_rate, specialties, skills, certifications
- **Status:** is_active, hire_date

#### ClientCompany (Primary Customer)
- **Business Info:** company_name, representative, phone, email
- **Finance:** payment_cycle, closing_day, payment_offset_months, payment_day
- **Defaults:** default_key_handover_location
- **Templates:** completion_report_notes (template for projects)
- **Approval:** approval_threshold (金額)
- Relations: Many projects via FK

#### FixedCost & VariableCost (Expense Management)
- **FixedCost:** monthly expenses (rent, utilities, etc.)
  - Fields: cost_type, monthly_amount, start_date, end_date
- **VariableCost:** per-project costs
  - Fields: monthly_amount, related to Project

#### MaterialOrder (Supply Chain)
- FK to Project
- status choices: pending, ordered, received, cancelled
- supplier info, quantities, costs
- Relations: MaterialOrderItem (line items)

#### Invoice & InvoiceItem (Billing)
- FK to Project
- **Fields:** invoice_number, invoice_date, due_date, total_amount, paid_date
- **Status:** draft, issued, paid, cancelled
- Relations: InvoiceItem (line items with descriptions, amounts)

#### Report (Financial Reporting)
- Report templates and instances
- Fields: report_type, date_range, status, file
- Custom data stored in JSONField

#### UserProfile (Extended User Info)
- FK to Django User
- **Fields:** roles (JSONField list), avatar, permissions
- **Relations:** Many to many project assignments

#### Comment & CommentAttachment (Collaboration)
- FK to Project
- Stores discussion threads
- Supports file attachments
- Notification integration

#### Additional Models:
- **Notification** - User notifications with read status
- **ApprovalLog** - Approval workflow history
- **ChecklistTemplate & ProjectChecklist** - Project checklists
- **ProjectFile** - Project document storage
- **ContractorReview** - Contractor performance reviews
- **RatingCriteria** - Performance rating scales
- **ContactPerson** - Individual contacts at companies
- **WorkType** - Project type classifications
- **CompanySettings** - System-wide configuration

### Model Relationships Summary

```
Project (central)
├── FK: client_company → ClientCompany
├── FK: client_name (CharField, also stores raw text)
├── FK: approved_by → User
├── Reverse: progress_steps ← ProjectProgressStep
├── Reverse: comments ← Comment
├── Reverse: notifications ← Notification
├── Reverse: material_orders ← MaterialOrder
├── Reverse: invoices ← Invoice
├── Reverse: files ← ProjectFile
├── Reverse: checklists ← ProjectChecklist
└── Reverse: reviews ← ContractorReview

Subcontract (implicit via foreign keys)
├── FK: project → Project
├── FK: contractor → Contractor
└── FK: internal_worker → InternalWorker

ClientCompany
├── Reverse: projects ← Project
└── Reverse: contacts ← ContactPerson
```

---

## 4. FRONTEND TECHNOLOGY STACK

### CSS Framework
- **Bootstrap 5.3.0** (CDN)
- **Custom CSS** - 500+ lines in base.html with CSS variables
- **Theme Colors:**
  - Primary: #667eea (blue)
  - Secondary: #764ba2 (purple)
  - Navigation: #2c3e50 (dark blue)

### JavaScript Libraries
1. **jQuery 3.7.0** - DOM manipulation, AJAX
2. **Bootstrap JS 5.3.0** - Modal, dropdown, tooltip components
3. **Toastr.js** - Toast notifications
4. **Chart.js** - Data visualization (likely, based on dashboard templates)
5. **Custom Scripts** - Embedded in templates for project-specific logic

### Frontend Components
- Modal dialogs (Bootstrap modals)
- Form validation
- AJAX form submission
- Dynamic form fields
- Drag-and-drop (assumed for step reordering)
- Real-time progress calculation
- Color-coded status badges

### Template Features
- **Responsive Design** - Mobile-first Bootstrap
- **Form Handling** - Django CSRF protection + HTML5 validation
- **Dynamic Content** - jQuery for inline updates
- **Accessibility** - Bootstrap semantic HTML

---

## 5. KEY CONFIGURATION FILES

### Django Settings (settings.py)
```python
# Database
DATABASE = 'sqlite3' (dev) / 'postgresql' (prod)

# Middleware (Custom Stack)
- SecurityMiddleware
- WhiteNoiseMiddleware (static file serving)
- SessionMiddleware
- CommonMiddleware
- CsrfViewMiddleware
- AuthenticationMiddleware
- MessageMiddleware
- ClickjackingXFrameOptionsMiddleware

# Internationalization
LANGUAGE_CODE = 'ja' (Japanese)
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
NUMBER_GROUPING = 3 (3-digit separators: 1,000,000)
THOUSAND_SEPARATOR = ','
DECIMAL_SEPARATOR = '.'

# File Uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Authentication
LOGIN_URL = '/orders/login/'
LOGIN_REDIRECT_URL = '/'

# Security (Development)
DEBUG = True
SECRET_KEY = [insecure default - change in production]
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver', 'onrender.com']
```

### URL Configuration (urls.py)
```python
# Root URLs
admin/                          → Django Admin
orders/                         → order_management app (namespace: order_management)
subcontracts/                   → subcontract_management app (namespace: subcontract_management)
/                               → order_management root URLs (no namespace)
```

### App Configuration (apps.py)
```python
# Auto-loads signals on app startup
class OrderManagementConfig(AppConfig):
    def ready(self):
        import order_management.signals
```

### Requirements.txt
```
Django==5.2.6              # Web framework
django-bootstrap4==23.2    # Bootstrap integration
gunicorn==21.2.0          # Production server
whitenoise==6.11.0        # Static file middleware
python-dateutil==2.9.0    # Date utilities
Pillow==11.3.0            # Image processing
requests==2.32.5          # HTTP library
reportlab==4.2.5          # PDF generation
```

---

## 6. DEVELOPMENT WORKFLOWS

### Key Development Patterns

#### Creating a New Project
1. User submits ProjectForm (views.py:project_create)
2. Form validation + auto-generation of management_no
3. Save triggers:
   - Auto-calculation of billing_amount
   - Auto-setup of default progress steps (via service)
   - Signal fires to check notifications
4. Redirect to project detail

#### Managing Project Progress
1. Project detail page displays ProjectProgressStep list
2. User updates scheduled_date, actual_date, or is_completed
3. AJAX call to update_progress endpoint
4. Service layer recalculates progress percentage
5. Model method get_progress_status() returns updated phase
6. Frontend updates progress bar + status badge

#### Payment/Cashflow Management
1. User navigates to PaymentManagementView
2. View calls cashflow_service functions
3. Service aggregates Project + Subcontract payment data
4. Calculates payment_due_date from contract terms
5. Returns data to template for display
6. AJAX endpoints for bulk updates

#### Contractor Management
1. Browse/search contractors (views_contractor.py)
2. Create new contractor (views_contractor_create.py)
3. Assign to projects via Subcontract model
4. Track performance (success_rate, average_rating)

#### Reporting & Analysis
1. Generate reports (views_report.py)
2. PDF export via reportlab
3. Multiple report types (financial, performance, etc.)
4. Historical data aggregation

### Testing Approach
- Selenium tests for UI (test_selenium_features.py, test_key_handover_selenium.py)
- Unit tests for models and views
- Integration tests for workflows
- Test data scripts (create_test_contractors.py)

### Database Migration Strategy
- 60 migrations tracked
- Recent: Phases 5, 8, 11 migrations
- Draft project support (migration 0058)
- Deprecation pattern: Fields marked with DEPRECATED comments

---

## 7. EXISTING DOCUMENTATION

### Main Documentation Files

#### README.md
- Project name: 案件管理・経理管理システム (Construction Dispatch)
- Features overview (8 main feature areas)
- Tech stack summary
- Setup instructions (pip install, migrate, createsuper user, runserver)
- Main URL paths
- Production notes

#### プロジェクト仕様書.md (~200+ lines)
- System overview & target users
- Detailed feature descriptions (Phase numbering)
- Implementation status per feature
- Phase history (Phase 1-11)
- Client company integration details
- Progress step customization specs

#### ISSUES_FIX_SUMMARY.md
- 11 identified issues
- 7 issues resolved
- 4 issues pending
- Examples: auto-calculation bugs, status display logic, business rule implementation

#### ISSUES_TEST_RESULTS.md
- Test execution results
- Issue verification status
- Bug reproduction steps

#### NAVIGATION_CHECK.md
- URL routing verification
- Navigation bar testing
- Role-based menu items

#### CLAUDE.md
- Development constraints
- No browser popup restrictions (alert, confirm, prompt)
- Use modal components instead

### Git History
Recent commits show:
- Phase 5: Replace modal with 4-step structure
- Phase 4: Change labels from 元請名 to 業者名
- Fix contractor type badges
- Add row-click selection to contractor table
- Remove contractor selection method toggle

---

## 8. ARCHITECTURAL STRENGTHS & PATTERNS

### Strengths
1. **Clear Domain Separation** - order_management vs subcontract_management
2. **Service Layer** - Progress steps and cashflow logic centralized
3. **SSOT Implementation** - Templates define available steps
4. **Role-Based Access Control** - Fine-grained permissions
5. **Signal Integration** - Auto-notifications without view coupling
6. **Comprehensive Models** - 30+ models covering all business domains
7. **Auto-Calculation** - Management_no, billing_amount, progress percentage
8. **Multi-Phase Support** - Extensible phase system (Phases 1-11)
9. **Draft Project Support** - Work-in-progress without affecting statistics
10. **Internationalization** - Japanese UI with proper localization

### Areas for Enhancement
1. **API Pattern** - Could benefit from DRF for RESTful consistency
2. **Form Inheritance** - Some duplication across similar forms
3. **Template Organization** - 78 templates could use more subdirectory structure
4. **View File Sizes** - views.py (2,674 lines) could be split further
5. **Testing Coverage** - Mix of Selenium + unit tests, could use pytest-django
6. **Error Handling** - Varied approaches to exception handling
7. **Caching Strategy** - No apparent caching layer for expensive calculations
8. **Frontend State Management** - jQuery-based, no modern JS framework

---

## 9. DEVELOPMENT CONFIGURATION

### Local Development Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Create admin user
python manage.py createsuperuser

# 4. Load test data (optional)
python create_test_contractors.py

# 5. Start development server
python manage.py runserver

# Access at http://localhost:8000/
# Admin at http://localhost:8000/admin/
```

### Production Deployment
- Uses Gunicorn (configured in requirements.txt)
- WhiteNoise handles static file serving
- Environment variables for SECRET_KEY, DEBUG, ALLOWED_HOSTS
- Database: PostgreSQL or MySQL (configure in settings)
- File storage: media/ directory (configure for cloud storage in production)

---

## 10. UNIQUE FEATURES & CUSTOM IMPLEMENTATIONS

### Progress Step System
- **Flexible:** Supports default + custom steps per project
- **Dynamic:** Add/remove/reorder steps without code changes
- **Intelligent:** Auto-calculates completion based on scheduled vs actual dates
- **Template-Based:** Reusable step definitions

### Payment Cycle Management
- **Features:** Closing day, payment day, offset month configuration
- **Automatic:** Calculates payment_due_date from contract date + terms
- **Per-Project:** Can override client company defaults

### Approval Workflow
- **Threshold-Based:** Auto-triggers approval for orders exceeding amount
- **Tracking:** Stores approver, approval timestamp, approval log
- **Statuses:** not_required, pending, approved, rejected

### Completion Report System
- **Templates:** Inherited from ClientCompany
- **Statuses:** not_created, draft, submitted
- **File Support:** Upload PDF/Excel reports
- **Auto-Content:** Template auto-population possible

### Key Handover Management
- **Location Tracking:** Default from client company or custom per-project
- **DateTime:** Records exact handover moment
- **Notes:** Additional instructions per project

### Contractor Skill Management
- **Skill Categories** (JSONField) - e.g., ["電気工事", "空調工事"]
- **Skill Level** - 初級, 中級, 上級, エキスパート
- **Service Areas** (JSONField) - Geographic coverage
- **Trust Level** - 1-5 rating for direct assignment authorization
- **Certifications** - Stored as text with line breaks

---

## 11. SECURITY CONSIDERATIONS

### Implemented
- CSRF protection on all POST endpoints
- Django authentication required for most views
- Role-based permission checks (user_roles.py)
- SQL injection prevention (ORM usage)
- XSS protection via template escaping
- WhiteNoise secure static file serving

### To Review
- SECRET_KEY should be environment variable (currently has insecure default)
- DEBUG flag should be environment-controlled
- ALLOWED_HOSTS should match production domain
- Media file upload validation (accept types, size limits)
- API endpoint rate limiting (none apparent)
- Password reset flow security

---

## 12. KEY CODE METRICS

| Component | Lines | Purpose |
|-----------|-------|---------|
| models.py | 3,846 | Data models (30+ classes) |
| views.py | 2,674 | Core view functions |
| forms.py | 609 | Django forms (13+ classes) |
| urls.py | 200+ | URL routing |
| base.html | 500+ | Master template |
| services/ | 500+ | Business logic layer |
| admin.py | 200+ | Django admin config |
| Total Python | 15,000+ | Application code |
| Total Templates | 78 files | Frontend templates |
| Migrations | 60 files | Database schema history |

---

## CONCLUSION

The Construction Dispatch system is a **well-structured, domain-driven Django application** designed specifically for construction project management and accounting. Key architectural decisions prioritize:

1. **Domain Separation** - Clear app boundaries
2. **Centralized Logic** - Service layers for SSOT
3. **Extensibility** - Phase-based development, custom step templates
4. **User Experience** - Role-based access, notifications, progress visualization
5. **Financial Accuracy** - Careful calculation logic, multi-tier approval
6. **Maintainability** - Detailed documentation, signal-based automation

The codebase demonstrates strong fundamentals with room for modernization in frontend tooling (React/Vue) and API patterns (DRF).

