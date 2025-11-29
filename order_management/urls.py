from django.urls import path
from . import views
from .views_auth import HeadquartersLoginView, HeadquartersLogoutView
from .views_permission import PermissionDeniedView
from .views_landing import LandingView
from .views_contractor import ContractorDashboardView, ContractorProjectsView, ContractorEditView
from .views_ordering import OrderingDashboardView, ExternalContractorManagementView, SupplierManagementView
from .views_contractor_create import ContractorCreateView
from .views_payment import PaymentDashboardView
from .views_receipt import ReceiptDashboardView
from .views_accounting import AccountingDashboardView
from .views_cost import (
    FixedCostListView, FixedCostCreateView, FixedCostUpdateView, FixedCostDeleteView,
    VariableCostListView, VariableCostCreateView, VariableCostUpdateView, VariableCostDeleteView,
    cost_dashboard
)
from .views_ultimate import UltimateDashboardView
from . import views_material
from . import views_comment
from .views_notification import NotificationListView, mark_as_read_and_archive
from .views_profile import profile_settings
from .views_cashflow import (
    CashFlowDashboardView,
    AccrualVsCashComparisonView,
    ReceivablesDetailView,
    PayablesDetailView,
    cashflow_monthly_api,
    cashflow_daily_api,
    cashflow_forecast_api,
    receivables_api,
    payables_api
)
from .views_forecast import (
    ForecastDashboardView,
    ScenarioListView,
    ScenarioCreateView,
    ScenarioUpdateView,
    ScenarioDeleteView,
    ScenarioCompareView,
    scenario_calculate_api,
    forecast_preview_api,
    scenario_compare_api,
    pipeline_analysis_api,
    historical_analysis_api,
    SeasonalityEditView,
    seasonality_calculate_api
)
from .views_user_management import (
    UserManagementDashboardView,
    UserRoleEditView,
    UserRoleQuickEditView
)
from .views_report import (
    ReportDashboardView,
    ReportListView,
    ReportDetailView,
    ReportDeleteView,
    ReportGenerateView,
    report_download_pdf,
    report_regenerate_pdf,
    report_preview_api
)
from .views_calendar import (
    ConstructionCalendarView,
    PerformanceMonthlyView,
    GanttChartView,
    WorkerResourceCalendarView,
    calendar_events_api,
    performance_monthly_api,
    gantt_data_api,
    worker_resource_data_api
)
from .views_mention import mention_users_api
from .views_client_company import (
    ClientCompanyListView,
    ClientCompanyDetailView,
    ClientCompanyCreateView,
    ClientCompanyUpdateView,
    ClientCompanyDeleteView,
    client_company_api,
    client_company_list_ajax,
    client_company_create_ajax,
    contact_person_create_ajax,
    contact_person_update_ajax,
    contact_person_delete_ajax
)
from .views_work_type import (
    work_type_list_ajax,
    work_type_create_ajax,
    work_type_update_ajax,
    work_type_delete_ajax,
    work_type_reorder_ajax
)
from .views_rating_criteria import (
    rating_criteria_view,
    rating_criteria_update_ajax
)
from .views_approval import (
    ApprovalListView,
    ApprovalDetailView,
    ApprovalRequestView,
    approval_action
)
from .views_review import ContractorReviewCreateView
from .views_checklist import (
    ChecklistTemplateListView,
    ChecklistTemplateCreateView,
    ChecklistTemplateUpdateView,
    ChecklistTemplateDeleteView,
    ProjectChecklistCreateView,
    ProjectChecklistDetailView,
    project_checklist_update_item,
    project_checklist_delete
)
from .views_file import (
    project_file_upload,
    project_file_download,
    project_file_delete,
    step_file_upload_ajax,
    step_file_delete_ajax
)
from .views_backup import (
    export_data,
    import_data_view
)

app_name = 'order_management'

urlpatterns = [
    # ランディング・認証・権限
    path('landing/', LandingView.as_view(), name='landing'),
    path('login/', HeadquartersLoginView.as_view(), name='login'),
    path('logout/', HeadquartersLogoutView.as_view(), name='logout'),
    path('permission-denied/', PermissionDeniedView.as_view(), name='permission_denied'),

    # 通知管理
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/archive/', mark_as_read_and_archive, name='notification_archive'),

    # ユーザー・ロール管理
    path('users/', UserManagementDashboardView.as_view(), name='user_management'),
    path('users/<int:user_id>/role-edit/', UserRoleEditView.as_view(), name='user_role_edit'),
    path('users/<int:pk>/role-quick-edit/', UserRoleQuickEditView.as_view(), name='user_role_quick_edit'),

    # ダッシュボード・案件管理
    path('', UltimateDashboardView.as_view(), name='dashboard'),
    path('legacy/', views.dashboard, name='legacy_dashboard'),
    path('contractor-dashboard/', ContractorDashboardView.as_view(), name='contractor_dashboard'),
    path('ordering-dashboard/', OrderingDashboardView.as_view(), name='ordering_dashboard'),
    path('external-contractors/', ExternalContractorManagementView.as_view(), name='external_contractor_management'),
    path('suppliers/', SupplierManagementView.as_view(), name='supplier_management'),
    path('accounting/', AccountingDashboardView.as_view(), name='accounting_dashboard'),
    path('ultimate/', UltimateDashboardView.as_view(), name='ultimate_dashboard'),
    path('payment/', PaymentDashboardView.as_view(), name='payment_dashboard'),
    path('receipt/', ReceiptDashboardView.as_view(), name='receipt_dashboard'),
    path('contractor/<int:contractor_id>/projects/', ContractorProjectsView.as_view(), name='contractor_projects'),
    path('contractors/<int:pk>/edit/', ContractorEditView.as_view(), name='contractor_edit'),
    path('contractors/new/', ContractorCreateView.as_view(), name='contractor_create'),
    path('list/', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/update/', views.project_update, name='project_update'),
    path('<int:pk>/update-field/', views.update_project_field, name='update_project_field'),
    path('<int:pk>/update-progress/', views.update_progress, name='update_progress'),
    path('<int:pk>/update-forecast/', views.update_forecast, name='update_forecast'),
    path('<int:pk>/update-stage/', views.update_project_stage, name='update_project_stage'),
    path('<int:pk>/add-subcontract/', views.add_subcontract, name='add_subcontract'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('api/list/', views.project_api_list, name='project_api_list'),
    path('api/staff/', views.staff_api, name='staff_api'),
    path('api/staff/<int:staff_id>/', views.staff_api, name='staff_api_detail'),
    path('api/contractor/', views.contractor_api, name='contractor_api'),
    path('api/contractor/<int:contractor_id>/', views.contractor_api, name='contractor_api_detail'),

    # 請求書API
    path('api/invoice/generate/', views.generate_client_invoice_api, name='generate_client_invoice_api'),
    path('api/invoice/preview/<int:project_id>/', views.get_invoice_preview_api, name='get_invoice_preview_api'),
    path('api/invoice/preview/client/', views.get_client_invoice_preview_api, name='client_invoice_preview_api'),
    path('api/generate-invoices-by-client/', views.generate_invoices_by_client_api, name='generate_invoices_by_client_api'),

    # キャッシュフロー管理 - Phase 1
    path('cashflow/', CashFlowDashboardView.as_view(), name='cashflow_dashboard'),
    path('cashflow/comparison/', AccrualVsCashComparisonView.as_view(), name='cashflow_comparison'),
    path('cashflow/receivables/', ReceivablesDetailView.as_view(), name='receivables_detail'),
    path('cashflow/payables/', PayablesDetailView.as_view(), name='payables_detail'),

    # キャッシュフローAPI - Phase 1
    path('api/cashflow/monthly/', cashflow_monthly_api, name='cashflow_monthly_api'),
    path('api/cashflow/daily/', cashflow_daily_api, name='cashflow_daily_api'),
    path('api/cashflow/forecast/', cashflow_forecast_api, name='cashflow_forecast_api'),
    path('api/cashflow/receivables/', receivables_api, name='cashflow_receivables_api'),
    path('api/cashflow/payables/', payables_api, name='cashflow_payables_api'),

    # 売上予測・シミュレーション - Phase 2
    path('forecast/', ForecastDashboardView.as_view(), name='forecast_dashboard'),
    path('forecast/scenarios/', ScenarioListView.as_view(), name='scenario_list'),
    path('forecast/scenarios/create/', ScenarioCreateView.as_view(), name='scenario_create'),
    path('forecast/scenarios/<int:pk>/edit/', ScenarioUpdateView.as_view(), name='scenario_update'),
    path('forecast/scenarios/<int:pk>/delete/', ScenarioDeleteView.as_view(), name='scenario_delete'),
    path('forecast/compare/', ScenarioCompareView.as_view(), name='scenario_compare'),

    # 売上予測API - Phase 2
    path('api/forecast/scenario/<int:scenario_id>/calculate/', scenario_calculate_api, name='scenario_calculate_api'),
    path('api/forecast/preview/', forecast_preview_api, name='forecast_preview_api'),
    path('api/forecast/compare/', scenario_compare_api, name='scenario_compare_api'),
    path('api/forecast/pipeline/', pipeline_analysis_api, name='pipeline_analysis_api'),
    path('api/forecast/historical/', historical_analysis_api, name='historical_analysis_api'),

    # 季節性指数管理 - Phase 3
    path('forecast/scenarios/<int:pk>/seasonality/', SeasonalityEditView.as_view(), name='seasonality_edit'),
    path('api/forecast/scenario/<int:scenario_id>/seasonality/calculate/', seasonality_calculate_api, name='seasonality_calculate_api'),

    # レポート管理 - Phase 3
    path('reports/', ReportDashboardView.as_view(), name='report_dashboard'),
    path('reports/list/', ReportListView.as_view(), name='report_list'),
    path('reports/generate/', ReportGenerateView.as_view(), name='report_generate'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report_detail'),
    path('reports/<int:pk>/delete/', ReportDeleteView.as_view(), name='report_delete'),
    path('reports/<int:pk>/download/', report_download_pdf, name='report_download_pdf'),
    path('reports/<int:pk>/regenerate-pdf/', report_regenerate_pdf, name='report_regenerate_pdf'),
    path('api/reports/preview/', report_preview_api, name='report_preview_api'),

    # コスト管理
    path('cost/', cost_dashboard, name='cost_dashboard'),
    path('cost/fixed/', FixedCostListView.as_view(), name='fixed_cost_list'),
    path('cost/fixed/create/', FixedCostCreateView.as_view(), name='fixed_cost_create'),
    path('cost/fixed/<int:pk>/edit/', FixedCostUpdateView.as_view(), name='fixed_cost_update'),
    path('cost/fixed/<int:pk>/delete/', FixedCostDeleteView.as_view(), name='fixed_cost_delete'),
    path('cost/variable/', VariableCostListView.as_view(), name='variable_cost_list'),
    path('cost/variable/create/', VariableCostCreateView.as_view(), name='variable_cost_create'),
    path('cost/variable/<int:pk>/edit/', VariableCostUpdateView.as_view(), name='variable_cost_update'),
    path('cost/variable/<int:pk>/delete/', VariableCostDeleteView.as_view(), name='variable_cost_delete'),

    # 資材管理
    path('<int:project_id>/materials/', views_material.material_order_list, name='material_order_list'),
    path('<int:project_id>/materials/create/', views_material.material_order_create, name='material_order_create'),
    path('<int:project_id>/materials/<int:order_id>/', views_material.material_order_detail, name='material_order_detail'),
    path('<int:project_id>/materials/<int:order_id>/edit/', views_material.material_order_edit, name='material_order_edit'),
    path('<int:project_id>/materials/<int:order_id>/status/', views_material.material_order_status_update, name='material_order_status_update'),

    # コメント・通知機能 - Phase 6
    path('api/projects/<int:project_id>/comments/', views_comment.get_comments, name='api_get_comments'),
    path('api/projects/<int:project_id>/comments/post/', views_comment.post_comment, name='api_post_comment'),
    path('api/comments/<int:comment_id>/edit/', views_comment.edit_comment, name='api_edit_comment'),
    path('api/comments/<int:comment_id>/delete/', views_comment.delete_comment, name='api_delete_comment'),
    path('api/notifications/', views_comment.get_notifications, name='api_get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views_comment.mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/read-all/', views_comment.mark_all_notifications_read, name='api_mark_all_notifications_read'),

    # プロフィール設定
    path('profile/settings/', profile_settings, name='profile_settings'),

    # 詳細コメント機能
    path('api/projects/<int:pk>/comments/', views.project_comments, name='api_project_comments'),

    # カレンダー・業績管理 - Phase 7
    path('calendar/', ConstructionCalendarView.as_view(), name='construction_calendar'),
    path('calendar/worker-resources/', WorkerResourceCalendarView.as_view(), name='worker_resource_calendar'),
    path('api/calendar/events/', calendar_events_api, name='calendar_events_api'),
    path('api/calendar/worker-resources/', worker_resource_data_api, name='worker_resource_data_api'),
    path('api/mention/users/', mention_users_api, name='mention_users_api'),
    path('performance/monthly/', PerformanceMonthlyView.as_view(), name='performance_monthly'),
    path('api/performance/monthly/', performance_monthly_api, name='performance_monthly_api'),
    path('gantt/', GanttChartView.as_view(), name='gantt_chart'),
    path('api/gantt/data/', gantt_data_api, name='gantt_data_api'),

    # 元請会社管理 - Phase 8
    path('client-companies/', ClientCompanyListView.as_view(), name='client_company_list'),
    path('client-companies/create/', ClientCompanyCreateView.as_view(), name='client_company_create'),
    path('client-companies/<int:pk>/', ClientCompanyDetailView.as_view(), name='client_company_detail'),
    path('client-companies/<int:pk>/edit/', ClientCompanyUpdateView.as_view(), name='client_company_update'),
    path('client-companies/<int:pk>/delete/', ClientCompanyDeleteView.as_view(), name='client_company_delete'),
    path('api/client-companies/<int:company_id>/', client_company_api, name='client_company_api'),
    path('api/client-companies/list-ajax/', client_company_list_ajax, name='client_company_list_ajax'),
    path('api/client-companies/create-ajax/', client_company_create_ajax, name='client_company_create_ajax'),

    # 担当者管理 AJAX
    path('api/contact-persons/create-ajax/', contact_person_create_ajax, name='contact_person_create_ajax'),
    path('api/contact-persons/update-ajax/', contact_person_update_ajax, name='contact_person_update_ajax'),
    path('api/contact-persons/delete-ajax/', contact_person_delete_ajax, name='contact_person_delete_ajax'),

    # 工事種別管理 AJAX
    path('api/work-types/list-ajax/', work_type_list_ajax, name='work_type_list_ajax'),
    path('api/work-types/create-ajax/', work_type_create_ajax, name='work_type_create_ajax'),
    path('api/work-types/update-ajax/', work_type_update_ajax, name='work_type_update_ajax'),
    path('api/work-types/delete-ajax/', work_type_delete_ajax, name='work_type_delete_ajax'),
    path('api/work-types/reorder-ajax/', work_type_reorder_ajax, name='work_type_reorder_ajax'),

    # 評価基準マスター
    path('settings/rating-criteria/', rating_criteria_view, name='rating_criteria'),
    path('api/rating-criteria/update-ajax/', rating_criteria_update_ajax, name='rating_criteria_update_ajax'),

    # 承認フロー - Phase 8
    path('approvals/', ApprovalListView.as_view(), name='approval_list'),
    path('approvals/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
    path('projects/<int:project_pk>/request-approval/', ApprovalRequestView.as_view(), name='approval_request'),
    path('approvals/<int:pk>/action/', approval_action, name='approval_action'),

    # 職人評価 - Phase 8
    path('projects/<int:project_pk>/contractors/<int:contractor_pk>/review/',
         ContractorReviewCreateView.as_view(),
         name='contractor_review_create'),

    # チェックリスト管理 - Phase 8
    path('checklists/templates/', ChecklistTemplateListView.as_view(), name='checklist_template_list'),
    path('checklists/templates/create/', ChecklistTemplateCreateView.as_view(), name='checklist_template_create'),
    path('checklists/templates/<int:pk>/edit/', ChecklistTemplateUpdateView.as_view(), name='checklist_template_update'),
    path('checklists/templates/<int:pk>/delete/', ChecklistTemplateDeleteView.as_view(), name='checklist_template_delete'),
    path('projects/<int:project_pk>/checklists/create/', ProjectChecklistCreateView.as_view(), name='project_checklist_create'),
    path('projects/<int:project_pk>/checklists/<int:checklist_pk>/', ProjectChecklistDetailView.as_view(), name='project_checklist_detail'),
    path('projects/<int:project_pk>/checklists/<int:checklist_pk>/update-item/', project_checklist_update_item, name='project_checklist_update_item'),
    path('projects/<int:project_pk>/checklists/<int:checklist_pk>/delete/', project_checklist_delete, name='project_checklist_delete'),

    # ファイル管理 - Phase 5
    path('projects/<int:project_pk>/files/upload/', project_file_upload, name='project_file_upload'),
    path('projects/<int:project_pk>/files/<int:file_pk>/download/', project_file_download, name='project_file_download'),
    path('projects/<int:project_pk>/files/<int:file_pk>/delete/', project_file_delete, name='project_file_delete'),

    # ステップ固有のファイル管理（AJAX）
    path('api/projects/<int:project_pk>/step-files/upload/', step_file_upload_ajax, name='step_file_upload_ajax'),
    path('api/projects/<int:project_pk>/step-files/<int:file_pk>/delete/', step_file_delete_ajax, name='step_file_delete_ajax'),

    # データバックアップ・復元
    path('backup/export/', export_data, name='export_data'),
    path('backup/import/', import_data_view, name='import_data'),
]