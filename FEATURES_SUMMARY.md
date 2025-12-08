# Django Construction Management System - Complete Feature Catalog

## System Overview
This is a comprehensive construction project management system built with Django, designed to manage all aspects of construction projects from bidding through completion, including financial tracking, contractor management, and approval workflows.

**Version**: Phase 8+ | **Status**: Production-ready with active development

---

## CORE FEATURES BY CATEGORY

### 1. PROJECT MANAGEMENT (Core 7 Features)

#### 1.1 Project CRUD Operations
- **Create**: Form-based project creation with auto-generated management numbers
- **Read**: Detailed project view with timeline, costs, and progress
- **Update**: Field-by-field updates with validation
- **Delete**: Soft-delete with archive capability
- **List**: Paginated view (50 per page) with search and filtering
- **Draft Management**: Save incomplete projects for later completion
  - Draft list view
  - Draft deletion
  - Convert draft to final project
- **Key Fields**:
  - management_no (auto-generated: P{YY}{0000})
  - site_name, site_address
  - client_name, project_manager
  - order_amount, billing_amount (auto-calculated)
  - work_type, project_status
  - notes, payment_due_date

#### 1.2 Project Status Management
- **Statuses**: ネタ → A → B → 受注確定 → [NG]
  - ネタ: Lead/prospect stage
  - A: High probability
  - B: Medium probability
  - 受注確定: Confirmed order
  - NG: Rejected (blocks further progress)
- **Sub-Statuses**:
  - Estimate Status: not_issued, issued, under_review, approved, cancelled
  - Construction Status: waiting, in_progress, completed, cancelled
  - Invoice Status: not_issued, issued
  - Incoming Payment Status: pending, received, partial, overdue

#### 1.3 Dynamic Progress Step Tracking
The system uses flexible, project-customizable progress tracking steps:

**Available Steps** (10 standard types):
1. **attendance (立ち会い)** - Site witness/attendance
2. **survey (現調)** - Site survey/investigation
3. **estimate (見積書発行)** - Estimate issuance
4. **construction_start (着工)** - Construction commencement
5. **completion (完工)** - Project completion
6. **contract (契約)** - Contract signing
7. **invoice (請求書発行)** - Invoice issuance
8. **permit_application (許可申請)** - Permit application
9. **material_order (資材発注)** - Material ordering
10. **inspection (検査)** - Quality inspection

**Features per Step**:
- Scheduled date vs actual date tracking
- Completion checkbox
- Assignee list (internal/external)
- File attachments per step
- Auto-completion when scheduled date passes
- Color-coded status (verified/success/warning/secondary)

#### 1.4 Approval Workflow
- **Threshold-based**: Approval required above client company amount
- **Status Tracking**:
  - not_required: Below threshold
  - pending: Awaiting approval
  - approved: Approved by authority
  - rejected: Rejected (blocks project)
- **Audit Trail**: ApprovalLog model stores all approval actions
- **Approver Tracking**: Tracks who approved and when

#### 1.5 NG (Rejected) Project Handling
- Mark projects as NG status
- Auto-cancel all associated progress steps
- Prevent further action
- Preserves historical data

#### 1.6 Schedule Management
- Payment due date (入金予定日)
- ASAP requested flag
- Work date specification (施工日指定あり)
- Contract date (契約日)
- Completion date (完工日)
- Works with priority scoring

#### 1.7 Next Action Calculation
- Automatically determines next required action
- Provides "Next Step" guidance
- Uses complex state machine logic
- Considers step type, dates, and completion status

---

### 2. FINANCIAL & ACCOUNTING (9 Features)

#### 2.1 Payment Management Dashboard
**Modern 2-Tab System** (replaced legacy cashflow views):
- **Tab 1: Outgoing Payments (出金)**
  - Paid (出金済み): Already paid to contractors
  - Scheduled (出金予定): Due to be paid
  - Unfilled (未伝票): No invoice yet
- **Tab 2: Incoming Payments (入金)**
  - Received (入金済み): Already received from clients
  - Scheduled (入金予定): Expected to receive

**Features**:
- Month navigation (previous/current/next)
- Monthly balance calculation: (Incoming - Outgoing)
- Payment status tracking
- Contractor/Client aggregation views
- Real-time totals display

#### 2.2 Payment Status Updates
- Bulk update multiple payment records
- Status options: pending → processing → paid
- Overdue detection and flagging
- Payment date tracking

#### 2.3 Purchase Order & Invoice PDF Generation
- Auto-generate PDF purchase orders
- Auto-generate PDF invoices for suppliers
- Preview before generation
- Save generated documents to project
- Customizable templates

#### 2.4 Client Invoice Management
- Per-project invoice generation
- Bulk invoice generation by client
- Invoice customization (JSON storage for custom data)
- Invoice status tracking
- Invoice file storage and retrieval

#### 2.5 Cost Management
**Fixed Costs** (overhead):
- Monthly amount
- Categories (rent, utilities, insurance, etc.)
- Recurring expense tracking
- Active/inactive toggle

**Variable Costs** (project-dependent):
- Rate-based calculation
- Types: percentage of revenue, fixed per project, per unit
- Category organization
- Dynamic pricing models

**Dashboard**: Aggregates all costs

#### 2.6 Profit Analysis
**Per-Project Metrics**:
- Total Revenue: from Project.billing_amount
- Total Subcontract Cost: sum of external + internal labor
- Total Material Cost: sum of all materials
- Total Expense: all costs combined
- Gross Profit: Revenue - Expenses
- Profit Rate %: (Profit / Revenue) × 100

**Features**:
- Auto-calculation when subcontracts change
- Color coding: success (30%+), warning (15%+), info (0%+), danger (<0%)
- Per-project profitability view
- Used for priority scoring

#### 2.7-2.9 Archived Financial Features (INACTIVE)
- **Phase 1 Archived**: Cashflow Dashboard, Accrual vs Cash Comparison
- **Phase 2 Archived**: Forecast Dashboard, Scenarios, Pipeline Analysis
- **Phase 3 Archived**: Financial Reports, Seasonality Management
- Status: Code preserved, endpoints disabled

---

### 3. SUBCONTRACTOR & INTERNAL WORKER MANAGEMENT (11 Features)

#### 3.1 Contractor CRUD & Management
**Contractor Types**:
- individual (個人職人): Independent craftsmen
- company (協力会社): Subcontracting companies
- material (資材): Material suppliers

**CRUD Operations**:
- Create: AJAX-based and form-based creation
- Read: Contractor dashboard and detail views
- Update: Edit contractor information
- Delete: AJAX soft-delete

**Key Fields**:
- name, contractor_type
- address, contact_person
- phone, email
- specialties (text)
- hourly_rate
- is_active flag

#### 3.2 Contractor Skills & Capabilities
**Skill Tracking**:
- skill_categories (JSON list: e.g., ["電気工事", "空調工事"])
- skill_level: beginner/intermediate/advanced/expert
- service_areas (JSON geographic coverage)
- certifications (list of certifications held)
- trust_level (1-5 scale; 4+ = direct assignment by client)

#### 3.3 Contractor Performance Metrics
**Tracked Metrics**:
- total_projects: Total contract count
- success_rate: % of successful completions
- average_rating: 1-5 stars from reviews
- last_project_date: Most recent project

**Used for**:
- Contractor ranking
- Future assignment decisions

#### 3.4 Contractor Payment Terms
**Bank Information**:
- bank_name, branch_name
- account_type (ordinary/current/savings)
- account_number, account_holder

**Payment Schedule**:
- closing_day (1-31: payment cutoff)
- payment_offset_months (0/1/2/3: delay)
- payment_day (1-31: payment date)
- payment_cycle (monthly/bimonthly/quarterly/custom)

#### 3.5 Internal Worker Management
**Employee Departments**:
- construction (施工部)
- sales (営業部)
- design (設計部)
- management (管理部)
- quality (品質管理)
- safety (安全管理)
- other (その他)

**Tracking**:
- Employee ID, hire date
- Position, department
- Contact info (email, phone)
- Hourly rate
- Skills and specialties
- Employment status (active/inactive)

#### 3.6 Subcontract Creation & Tracking
**Linked to Projects**:
- Link to specific Project
- Associate with specific progress step
- Internal or external worker

**Contract Fields**:
- contract_amount, billed_amount
- payment_status, payment_due_date, payment_date
- worker_type (external/internal)
- purchase_order_issued, purchase_order_file

#### 3.7 Material Cost Management
**Fixed Material Items**:
- material_item_1/2/3 names
- material_cost_1/2/3 amounts
- Auto-calculated total_material_cost

**Dynamic Materials**:
- JSONField for flexible item list
- Per-item cost tracking
- Flexible quantity of items

#### 3.8 Dynamic Cost Items
**Hourly-Based Costs**:
- Multiplied by estimated_hours
- Combined with base contract amount

**Project-Unit Costs**:
- Fixed cost per project
- Multiple line items

**JSON Storage**: Flexible dynamic_cost_items field

#### 3.9 Payment Status Tracking
**Status Values**:
- pending (未払い): Not yet paid
- processing (処理中): Being processed
- paid (支払済): Already paid

**Features**:
- Overdue detection (is_payment_overdue())
- Color coding for UI display
- Batch status updates

#### 3.10 Profit Analysis & CSV Export
- Per-project subcontract profitability
- Revenue/expense aggregation
- CSV export for external analysis
- Payment tracking reports

---

### 4. CUSTOMER & CLIENT COMPANY MANAGEMENT (4 Features)

#### 4.1 Client Company Management
**CRUD Operations**:
- Create, Read, Update, Delete
- AJAX-based list and creation
- Bulk assignment to projects

**Company Information**:
- name, address
- phone, email
- representative
- industry classification
- is_active status

#### 4.2 Client Company Settings & Defaults
**Default Settings**:
- default_key_handover_location (鍵受け渡し場所)
- completion_report_notes (完了報告テンプレート)
- approval_threshold (金額: approval requirement amount)
- payment_cycle (default for projects)
- closing_day, payment_offset_months, payment_day (defaults)

#### 4.3 Contact Person Management
**Per-Company Contacts**:
- name, title/position
- email, phone
- Primary contact flag
- Notes field

**AJAX Operations**:
- Create, Update, Delete via AJAX

#### 4.4 Work Type Management
**Custom Work Types**:
- Create work types per client/system
- Reorder display priority
- AJAX CRUD operations
- Associated with projects

---

### 5. PROGRESS STEP TRACKING & SCHEDULING (5 Features)

#### 5.1 Standard Progress Steps (See Section 1.3)
10 pre-defined step types with customizable behavior

#### 5.2 Step Customization
- Enable/disable steps per project
- Reorder execution sequence
- Define step-specific requirements
- Add custom steps

#### 5.3 Step Assignees
**Assignment Options**:
- Internal staff (employees)
- External contractors
- Multiple assignees per step
- Stores as JSON array

#### 5.4 Step File Attachments
**File Management**:
- Upload files per step
- Download files
- Delete files
- Organize by project and step

#### 5.5 Progress Calculation & Project Stage
**Auto-Calculated Metrics**:
- Completion %: (completed_steps / total_steps) × 100
- Current Stage: One of 9 stages
- Color Status: verified/success/warning/secondary

**9 Possible Stages**:
1. 未開始 (Not started)
2. 立ち会い待ち (Waiting for witness)
3. 立ち会い済み (Witnessed)
4. 現調待ち (Waiting for survey)
5. 現調済み (Survey done)
6. 見積もり審査中 (Estimate under review)
7. 着工日待ち (Waiting for start date)
8. 工事中 (Under construction)
9. 完工 (Completed)

---

### 6. ADDITIONAL FEATURES (10 Features)

#### 6.1 Material Order Management
**For Project Materials**:
- Create material orders
- Track order status
- Line item management
- Cost totalization

#### 6.2 File Management
**Project Files**:
- Upload project documents
- Download files
- Organize by project
- Delete old files

#### 6.3 Checklist Management
**Templates & Usage**:
- Create reusable templates
- Apply to projects
- Mark items complete
- Track progress
- Multiple template support

#### 6.4 Comments & Notes
**Comment System**:
- Post comments on projects
- Edit/delete comments
- File attachments
- Comment history tracking

#### 6.5 Notifications
**User Alerts**:
- Create on project updates
- Mark as read
- Archive old notifications
- Real-time updates

#### 6.6 User Mentions
- Mention users with @symbol
- Send targeted notifications
- Populate from user list

#### 6.7 Contractor Review & Rating
**Post-Project Reviews**:
- 1-5 star rating
- Quality/punctuality/communication ratings
- Text review
- Updates contractor average_rating

#### 6.8 Search Functionality
**Search Across**:
- management_no (project ID)
- site_name (project location)
- client_name (client company)
- project_manager (assignee)
- Advanced filtering

#### 6.9 Data Export/Import
**Backup Operations**:
- Export project data
- Export financial data
- Import from backup
- Support data migration

---

### 7. USER MANAGEMENT & ROLES (4 Features)

#### 7.1 Authentication
- User login/logout
- Session management
- Permission-based access control

#### 7.2 Role-Based Access Control
**User Roles** (5 types):
1. **Executive (経営者)**
   - View all financial data
   - Approve high-value projects
   - Manage user roles
   - Access company settings

2. **Accounting (経理)**
   - Manage payments
   - Track finances
   - View financial reports
   - Change payment status
   - Input payment due dates

3. **Sales (営業)**
   - Create projects
   - Manage client companies
   - Generate invoices
   - View project pipeline

4. **Project Manager (現場管理)**
   - Update project status
   - Track progress
   - Manage subcontracts
   - Assign workers

5. **Worker Dispatch (作業員派遣)**
   - View project schedules
   - Manage worker assignments
   - Track attendance

#### 7.3 Permission System
**Helper Functions**:
- has_role(user, role)
- has_any_role(user, roles)
- has_all_roles(user, roles)
- can_view_profit(user)
- can_view_fixed_costs(user)
- can_change_payment_status(user)
- can_input_payment_due_date(user)
- can_issue_invoice(user)
- can_view_all_member_performance(user)
- can_manage_project(user)
- can_dispatch_workers(user)

**Decorators**:
- @role_required(*roles)
- @executive_required
- @accounting_required
- @worker_dispatch_required
- @sales_required

#### 7.4 User Profile & Settings
- Personal information updates
- Password management
- Preference settings
- Role assignment

---

### 8. SYSTEM & ADMIN FEATURES (5 Features)

#### 8.1 Company Settings
**Global Configuration**:
- company_name, address, phone, email
- tax_id
- default_invoice_template
- financial_year_start
- currency settings

#### 8.2 Rating Criteria Management
**Contractor Evaluation**:
- Define rating categories
- Set rating weights
- Customize rating scale
- Used in performance tracking

#### 8.3 Dashboard Views (7 Types)
1. **Ultimate Dashboard**: Main project overview
2. **Contractor Dashboard**: Contractor-specific view
3. **Ordering Dashboard**: Order management view
4. **Construction Calendar**: Project schedule
5. **Performance Monthly**: Monthly metrics
6. **Gantt Chart**: Project timeline
7. **Worker Resource Calendar**: Worker scheduling

#### 8.4 Calendar & Schedule Management
**Visualization Tools**:
- Calendar view of projects
- Worker resource scheduling
- Gantt chart for timelines
- Monthly performance tracking

#### 8.5 System Pages
- Landing page (unauthenticated)
- Permission denied page (403 handler)
- Archived features reference
- Legacy dashboard (compatibility)

---

## API ENDPOINTS SUMMARY

### Project APIs
- `GET /api/list/` - List all projects
- `GET /api/staff/` - Get staff list
- `GET /api/contractor/` - Get contractors

### Payment APIs (15 endpoints)
- Outgoing: paid, paid-by-contractor, scheduled, scheduled-by-contractor, unfilled
- Incoming: received, received-by-client, scheduled-by-client
- Bulk updates and PDF generation

### Client Company APIs (3 endpoints)
- List, retrieve, create (AJAX)

### Contact Person APIs (3 endpoints)
- Create, update, delete (AJAX)

### Work Type APIs (5 endpoints)
- List, create, update, delete, reorder (AJAX)

---

## DATA MODELS REFERENCE

### Order Management App (27 models)
- Project
- ProgressStepTemplate
- ProjectProgressStep
- ClientCompany
- ContactPerson
- WorkType
- FixedCost
- VariableCost
- MaterialOrder, MaterialOrderItem
- Invoice, InvoiceItem
- CashFlowTransaction
- ForecastScenario (archived)
- Report (archived)
- SeasonalityIndex (archived)
- UserProfile
- Comment, CommentAttachment
- Notification
- ContractorReview
- ApprovalLog
- ChecklistTemplate
- ProjectChecklist
- ProjectFile
- RatingCriteria
- CompanySettings

### Subcontract Management App (4 models)
- Contractor
- InternalWorker
- Subcontract
- ProjectProfitAnalysis

---

## TECHNOLOGY STACK

- **Framework**: Django 3.2+
- **Frontend**: Bootstrap 5, jQuery, JavaScript
- **Database**: PostgreSQL/SQLite
- **PDF Generation**: ReportLab
- **Export Formats**: CSV, PDF, JSON
- **Authentication**: Django built-in
- **Forms**: Django ModelForms

---

## FEATURE ACTIVATION STATUS

### Active Features
- Project Management
- Payment Management
- Subcontractor Management
- Customer Management
- Approvals & Workflows
- Checklists
- File Management
- Comments & Notifications
- Calendar & Scheduling
- User Role Management
- Company Settings

### Archived Features (Code Preserved)
- **Phase 1**: Cashflow Management
- **Phase 2**: Forecast & Scenarios
- **Phase 3**: Financial Reports
- Endpoints disabled but models and code preserved for reference

---

## FILE LOCATIONS

**features.json**: `/Users/zainkhalid/Dev/project-accounting-system/features.json`
**This document**: `/Users/zainkhalid/Dev/project-accounting-system/FEATURES_SUMMARY.md`

---

**Generated**: 2024-12-08
**Last Updated**: Phase 8+
**Comprehensive Coverage**: YES - All 40+ features documented
