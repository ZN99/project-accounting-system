from django.contrib import admin
from .models import InternalWorker, Contractor, Subcontract, ProjectProfitAnalysis


@admin.register(InternalWorker)
class InternalWorkerAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'employee_id',
        'department',
        'position',
        'hourly_rate',
        'is_active',
        'get_current_assignments',
        'created_at'
    ]

    list_filter = [
        'department',
        'is_active',
        'hire_date',
        'created_at'
    ]

    search_fields = [
        'name',
        'employee_id',
        'email',
        'specialties',
        'skills'
    ]

    list_editable = ['is_active', 'hourly_rate']

    fieldsets = (
        ('基本情報', {
            'fields': (
                'name',
                'employee_id',
                'department',
                'position',
                'email',
                'phone'
            )
        }),
        ('作業情報', {
            'fields': (
                'hourly_rate',
                'specialties',
                'skills'
            )
        }),
        ('雇用情報', {
            'fields': (
                'is_active',
                'hire_date'
            )
        })
    )

    def get_current_assignments(self, obj):
        return obj.get_current_assignments()
    get_current_assignments.short_description = '現在の担当案件数'


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'contractor_type',
        'contact_person',
        'phone',
        'specialties',
        'hourly_rate',
        'is_active',
        'created_at'
    ]

    list_filter = [
        'contractor_type',
        'is_active',
        'created_at'
    ]

    search_fields = [
        'name',
        'contact_person',
        'phone',
        'specialties'
    ]

    list_editable = ['is_active']

    fieldsets = (
        ('基本情報', {
            'fields': (
                'name',
                'contractor_type',
                'address',
                'contact_person',
                'phone',
                'email'
            )
        }),
        ('業務情報', {
            'fields': (
                'specialties',
                'hourly_rate',
                'is_active'
            )
        })
    )


@admin.register(Subcontract)
class SubcontractAdmin(admin.ModelAdmin):
    list_display = [
        'management_no',
        'contractor',
        'contract_amount',
        'billed_amount',
        'payment_status',
        'payment_due_date',
        'purchase_order_issued',
        'created_at'
    ]

    list_filter = [
        'payment_status',
        'purchase_order_issued',
        'contractor',
        'created_at'
    ]

    search_fields = [
        'management_no',
        'site_name',
        'contractor__name'
    ]

    readonly_fields = [
        'management_no',
        'site_name',
        'site_address',
        'total_material_cost'
    ]

    list_editable = [
        'payment_status',
        'purchase_order_issued'
    ]

    fieldsets = (
        ('案件情報', {
            'fields': (
                'project',
                'management_no',
                'site_name',
                'site_address'
            )
        }),
        ('外注先情報', {
            'fields': (
                'contractor',
                'work_description'
            )
        }),
        ('金額管理', {
            'fields': (
                'contract_amount',
                'billed_amount'
            )
        }),
        ('支払い管理', {
            'fields': (
                'payment_status',
                'payment_due_date',
                'payment_date',
                'purchase_order_issued'
            )
        }),
        ('部材費管理', {
            'fields': (
                'material_item_1',
                'material_cost_1',
                'material_item_2',
                'material_cost_2',
                'material_item_3',
                'material_cost_3',
                'total_material_cost'
            )
        }),
        ('その他', {
            'fields': (
                'notes',
            )
        })
    )


@admin.register(ProjectProfitAnalysis)
class ProjectProfitAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'project',
        'total_revenue',
        'total_expense',
        'gross_profit',
        'profit_rate',
        'updated_at'
    ]

    list_filter = [
        'updated_at'
    ]

    search_fields = [
        'project__management_no',
        'project__site_name'
    ]

    readonly_fields = [
        'total_revenue',
        'total_subcontract_cost',
        'total_material_cost',
        'total_expense',
        'gross_profit',
        'profit_rate',
        'updated_at'
    ]

    def has_add_permission(self, request):
        return False  # 手動追加を無効化
