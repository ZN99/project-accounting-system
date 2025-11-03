from django.urls import path
from . import views
from .views_skills import ContractorSkillsDashboardView, ContractorSkillsDetailView

app_name = 'subcontract_management'

urlpatterns = [
    # ダッシュボード
    path('', views.subcontract_dashboard, name='dashboard'),

    # 案件別発注管理
    path('project/<int:project_id>/', views.project_subcontract_list, name='project_subcontract_list'),
    path('project/<int:project_id>/create/', views.subcontract_create, name='subcontract_create'),
    path('subcontract/<int:pk>/update/', views.subcontract_update, name='subcontract_update'),
    path('<int:pk>/delete/', views.subcontract_delete, name='subcontract_delete'),

    # 発注先マスター管理
    path('contractors/', views.contractor_list, name='contractor_list'),
    path('contractors/create/', views.contractor_create, name='contractor_create'),

    # 職人スキル管理 - Phase 8
    path('contractor-skills/', ContractorSkillsDashboardView.as_view(), name='contractor_skills_dashboard'),
    path('contractor-skills/<int:pk>/', ContractorSkillsDetailView.as_view(), name='contractor_skills_detail'),

    # 利益分析
    path('profit-analysis/', views.profit_analysis_list, name='profit_analysis_list'),

    # 支払い追跡
    path('payment-tracking/', views.payment_tracking, name='payment_tracking'),

    # エクスポート
    path('export/csv/', views.export_subcontracts_csv, name='export_csv'),
]