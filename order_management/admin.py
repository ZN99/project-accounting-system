from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from . import models
from .models import (
    Project, CashFlowTransaction, ForecastScenario,
    ProjectProgress, Report, SeasonalityIndex, UserProfile,
    Comment, Notification, CommentAttachment, ClientCompany, ContractorReview,
    ApprovalLog, ChecklistTemplate, ProjectChecklist, ProjectFile, WorkType
)
from .user_roles import UserRole


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'management_no',
        'site_name',
        'work_type',
        'project_status',      # 旧: order_status
        'client_name',         # 旧: contractor_name
        'project_manager',
        'order_amount',        # 旧: estimate_amount
        'billing_amount',
        'amount_difference',
        'work_start_date',
        'work_end_date',
        'invoice_issued',
        'created_at'
    ]

    list_filter = [
        'project_status',  # 旧: order_status
        'work_type',
        'invoice_issued',
        'project_manager',
        'work_start_date',
        'created_at'
    ]

    search_fields = [
        'management_no',
        'site_name',
        'site_address',
        'client_name',     # 旧: contractor_name
        'project_manager',
        'notes'
    ]

    readonly_fields = [
        'management_no',
        'billing_amount',
        'amount_difference',
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('基本情報', {
            'fields': (
                'management_no',
                'site_name',
                'site_address',
                'work_type'
            )
        }),
        ('受注・見積情報', {
            'fields': (
                'project_status',        # 旧: order_status
                'estimate_issued_date',
                'order_amount',          # 旧: estimate_amount
                'parking_fee'
            )
        }),
        ('元請・担当情報', {  # 旧: 業者・担当情報
            'fields': (
                'client_name',           # 旧: contractor_name
                'client_address',        # 旧: contractor_address
                'project_manager'
            )
        }),
        ('スケジュール', {
            'fields': (
                'work_start_date',
                'work_end_date',
                'contract_date',
                'completion_date'  # Phase 1 追加
            )
        }),
        ('請求・経費管理', {
            'fields': (
                'invoice_issued',
                'invoice_issue_datetime',  # Phase 1 追加
                'expense_item_1',
                'expense_amount_1',
                'expense_item_2',
                'expense_amount_2',
                'billing_amount',
                'amount_difference'
            )
        }),
        ('入金管理', {  # Phase 1 追加
            'fields': (
                'payment_due_date',
                'payment_received_date',
                'payment_received_amount'
            )
        }),
        ('支払管理', {  # Phase 1 追加
            'fields': (
                'payment_scheduled_date',
                'payment_executed_date',
                'payment_amount',
                'payment_status',
                'payment_memo'
            )
        }),
        ('その他', {
            'fields': (
                'notes',
                'created_at',
                'updated_at'
            )
        })
    )

    list_editable = [
        'project_status',  # 旧: order_status
        'invoice_issued'
    ]

    list_per_page = 20

    date_hierarchy = 'created_at'

    def get_list_display_links(self, request, list_display):
        return ['management_no', 'site_name']

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            extra_context['status_color'] = obj.get_status_color()
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(CashFlowTransaction)
class CashFlowTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_date',
        'project',
        'transaction_type',
        'amount',
        'is_planned',
        'description',
        'created_at'
    ]

    list_filter = [
        'transaction_type',
        'is_planned',
        'transaction_date',
        'created_at'
    ]

    search_fields = [
        'project__management_no',
        'project__site_name',
        'description'
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本情報', {
            'fields': (
                'project',
                'transaction_type',
                'transaction_date',
                'amount',
                'is_planned'
            )
        }),
        ('詳細情報', {
            'fields': (
                'description',
                'related_subcontract'
            )
        }),
        ('システム情報', {
            'fields': (
                'created_at',
                'updated_at'
            )
        })
    )

    date_hierarchy = 'transaction_date'
    list_per_page = 50


@admin.register(ForecastScenario)
class ForecastScenarioAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'scenario_type',
        'conversion_rate_neta',
        'conversion_rate_waiting',
        'cost_rate',
        'forecast_months',
        'is_active',
        'is_default',
        'created_by',
        'created_at'
    ]

    list_filter = [
        'scenario_type',
        'is_active',
        'is_default',
        'seasonality_enabled',
        'created_at'
    ]

    search_fields = [
        'name',
        'description'
    ]

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('基本情報', {
            'fields': (
                'name',
                'description',
                'scenario_type',
                'is_active',
                'is_default'
            )
        }),
        ('成約率設定', {
            'fields': (
                'conversion_rate_neta',
                'conversion_rate_waiting'
            )
        }),
        ('コスト設定', {
            'fields': (
                'cost_rate',
                'fixed_cost_multiplier',
                'variable_cost_multiplier'
            )
        }),
        ('予測設定', {
            'fields': (
                'forecast_months',
                'seasonality_enabled'
            )
        }),
        ('予測結果', {
            'fields': (
                'forecast_results',
            ),
            'classes': ('collapse',)
        }),
        ('システム情報', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at'
            )
        })
    )

    list_editable = ['is_active', 'is_default']
    list_per_page = 20
    date_hierarchy = 'created_at'

    def save_model(self, request, obj, form, change):
        if not change:  # 新規作成時
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# Phase 3: 進捗管理・レポート機能
# =============================================================================

@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    """プロジェクト進捗管理"""
    list_display = [
        'project', 'recorded_date', 'progress_rate', 'status',
        'milestone_name', 'has_risk', 'recorded_by'
    ]
    list_filter = ['status', 'has_risk', 'recorded_date', 'milestone_completed']
    search_fields = ['project__name', 'project__management_no', 'notes', 'risk_description']
    date_hierarchy = 'recorded_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'recorded_date', 'recorded_by')
        }),
        ('進捗情報', {
            'fields': ('progress_rate', 'status', 'notes')
        }),
        ('マイルストーン', {
            'fields': ('milestone_name', 'milestone_date', 'milestone_completed')
        }),
        ('リスク・課題', {
            'fields': ('has_risk', 'risk_level', 'risk_description')
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not change:  # 新規作成時
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """レポート管理"""
    list_display = [
        'title', 'report_type', 'period_start', 'period_end',
        'is_published', 'generated_by', 'generated_date'
    ]
    list_filter = ['report_type', 'is_published', 'generated_date']
    search_fields = ['title', 'description']
    date_hierarchy = 'generated_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('title', 'report_type', 'description')
        }),
        ('対象期間', {
            'fields': ('period_start', 'period_end')
        }),
        ('レポートデータ', {
            'fields': ('report_data',),
            'classes': ('collapse',)
        }),
        ('PDF', {
            'fields': ('pdf_file',)
        }),
        ('公開設定', {
            'fields': ('is_published',)
        }),
        ('システム情報', {
            'fields': ('generated_by', 'generated_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['generated_date', 'created_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        if not change:  # 新規作成時
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SeasonalityIndex)
class SeasonalityIndexAdmin(admin.ModelAdmin):
    """季節性指数管理"""
    list_display = [
        'forecast_scenario', 'use_auto_calculation',
        'january_index', 'february_index', 'march_index',
        'created_at'
    ]
    list_filter = ['use_auto_calculation']
    search_fields = ['forecast_scenario__name']

    fieldsets = (
        ('シナリオ', {
            'fields': ('forecast_scenario', 'use_auto_calculation')
        }),
        ('1月～3月', {
            'fields': ('january_index', 'february_index', 'march_index')
        }),
        ('4月～6月', {
            'fields': ('april_index', 'may_index', 'june_index')
        }),
        ('7月～9月', {
            'fields': ('july_index', 'august_index', 'september_index')
        }),
        ('10月～12月', {
            'fields': ('october_index', 'november_index', 'december_index')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    actions = ['recalculate_from_historical_data']

    def recalculate_from_historical_data(self, request, queryset):
        """過去データから再計算"""
        count = 0
        for obj in queryset:
            obj.calculate_from_historical_data()
            count += 1
        self.message_user(request, f'{count}件の季節性指数を再計算しました。')
    recalculate_from_historical_data.short_description = '過去データから再計算'



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """ユーザープロファイル管理"""
    list_display = ["user", "get_roles_display", "created_at", "updated_at"]
    list_filter = []
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    
    fieldsets = (
        ("基本情報", {
            "fields": ("user", "roles")
        }),
        ("タイムスタンプ", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    readonly_fields = ["created_at", "updated_at"]
    
    def get_roles_display(self, obj):
        """ロールの表示"""
        return ", ".join(obj.get_roles_display()) if obj.roles else "ロールなし"
    get_roles_display.short_description = "ロール"


class CommentAttachmentInline(admin.TabularInline):
    """コメント添付ファイルのインライン表示"""
    model = CommentAttachment
    extra = 0
    readonly_fields = ["file_name", "file_size", "file_type", "uploaded_at"]
    fields = ["file", "file_name", "file_size", "uploaded_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """コメント管理"""
    list_display = ["project", "author", "get_content_preview", "get_attachments_count", "is_important", "created_at"]
    list_filter = ["is_important", "created_at", "author"]
    search_fields = ["project__site_name", "project__management_no", "content", "author__username"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CommentAttachmentInline]

    fieldsets = (
        ("基本情報", {
            "fields": ("project", "author", "content", "is_important")
        }),
        ("メンション", {
            "fields": ("mentioned_users",)
        }),
        ("タイムスタンプ", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_content_preview(self, obj):
        """コメント内容のプレビュー"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = "コメント"

    def get_attachments_count(self, obj):
        """添付ファイル数"""
        count = obj.attachments.count()
        return f"{count}件" if count > 0 else "-"
    get_attachments_count.short_description = "添付"


@admin.register(CommentAttachment)
class CommentAttachmentAdmin(admin.ModelAdmin):
    """コメント添付ファイル管理"""
    list_display = ["comment", "file_name", "get_file_size_display", "file_type", "uploaded_at"]
    list_filter = ["uploaded_at", "file_type"]
    search_fields = ["comment__content", "file_name"]
    date_hierarchy = "uploaded_at"
    readonly_fields = ["file_size", "file_type", "uploaded_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知管理"""
    list_display = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__username", "title", "message"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]

    fieldsets = (
        ("基本情報", {
            "fields": ("recipient", "notification_type", "title", "message", "link", "is_read")
        }),
        ("関連情報", {
            "fields": ("related_comment", "related_project")
        }),
        ("タイムスタンプ", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )



# =============================================================================
# Phase 8: 業務フロー最適化
# =============================================================================

@admin.register(ClientCompany)
class ClientCompanyAdmin(admin.ModelAdmin):
    """元請会社管理"""
    list_display = [
        'company_name', 'contact_person', 'phone', 'email',
        'approval_threshold', 'is_active', 'get_total_projects',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['company_name', 'contact_person', 'email', 'phone']

    fieldsets = (
        ('基本情報', {
            'fields': ('company_name', 'contact_person', 'email', 'phone', 'address', 'is_active')
        }),
        ('鍵受け渡し設定', {
            'fields': ('default_key_handover_location', 'key_handover_notes')
        }),
        ('完了報告シート', {
            'fields': ('completion_report_template', 'completion_report_notes')
        }),
        ('承認設定', {
            'fields': ('approval_threshold',)
        }),
        ('運用ルール', {
            'fields': ('special_notes',)
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']

    def get_total_projects(self, obj):
        return obj.get_total_projects()
    get_total_projects.short_description = '総案件数'


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    """工事種別管理"""
    list_display = ['name', 'description', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['display_order', 'is_active']
    ordering = ['display_order', 'name']

    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'description', 'display_order', 'is_active')
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(ContractorReview)
class ContractorReviewAdmin(admin.ModelAdmin):
    """職人評価管理"""
    list_display = [
        'contractor', 'project', 'overall_rating', 'quality_score',
        'speed_score', 'communication_score', 'would_recommend',
        'reviewed_by', 'reviewed_at'
    ]
    list_filter = ['overall_rating', 'would_recommend', 'reviewed_at']
    search_fields = ['contractor__name', 'project__management_no', 'review_comment']
    date_hierarchy = 'reviewed_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('contractor', 'project')
        }),
        ('評価', {
            'fields': (
                'overall_rating', 'quality_score', 'speed_score',
                'communication_score', 'would_recommend'
            )
        }),
        ('コメント', {
            'fields': ('review_comment',)
        }),
        ('メタ情報', {
            'fields': ('reviewed_by', 'reviewed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['reviewed_at', 'updated_at']


@admin.register(ApprovalLog)
class ApprovalLogAdmin(admin.ModelAdmin):
    """承認履歴管理"""
    list_display = [
        'project', 'approval_type', 'status', 'requester',
        'approver', 'amount', 'requested_at', 'approved_at'
    ]
    list_filter = ['approval_type', 'status', 'requested_at']
    search_fields = [
        'project__management_no', 'project__site_name',
        'requester__username', 'approver__username'
    ]
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('案件情報', {
            'fields': ('project', 'approval_type', 'status', 'amount')
        }),
        ('申請情報', {
            'fields': ('requester', 'request_reason', 'requested_at')
        }),
        ('承認情報', {
            'fields': ('approver', 'approval_comment', 'rejection_reason', 'approved_at')
        }),
    )

    readonly_fields = ['requested_at', 'approved_at']


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    """チェックリストテンプレート管理"""
    list_display = ['name', 'work_type', 'is_active', 'created_at', 'updated_at']
    list_filter = ['work_type', 'is_active', 'created_at']
    search_fields = ['name', 'work_type', 'description']

    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'work_type', 'description', 'is_active')
        }),
        ('チェック項目', {
            'fields': ('items',)
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']


@admin.register(ProjectChecklist)
class ProjectChecklistAdmin(admin.ModelAdmin):
    """案件チェックリスト管理"""
    list_display = ['project', 'template', 'get_completion_rate', 'completed_at', 'created_at']
    list_filter = ['completed_at', 'created_at']
    search_fields = ['project__management_no', 'project__site_name', 'template__name']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'template')
        }),
        ('チェック項目', {
            'fields': ('items',)
        }),
        ('完了情報', {
            'fields': ('completed_at',)
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_completion_rate(self, obj):
        return f"{obj.get_completion_rate()}%"
    get_completion_rate.short_description = '完了率'


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    """案件ファイル管理 - Phase 5"""
    list_display = ['project', 'file_name', 'get_file_size', 'file_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at', 'uploaded_by']
    search_fields = ['project__management_no', 'project__site_name', 'file_name', 'description']
    date_hierarchy = 'uploaded_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'file', 'file_name', 'file_type')
        }),
        ('詳細', {
            'fields': ('description', 'file_size')
        }),
        ('アップロード情報', {
            'fields': ('uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['file_size', 'uploaded_at']

    def get_file_size(self, obj):
        return obj.get_file_size_display()
    get_file_size.short_description = 'ファイルサイズ'


# ================================================================================
# ユーザー管理 - カスタムUser Admin with UserProfile
# ================================================================================

class UserProfileInline(admin.StackedInline):
    """ユーザープロファイルをUser編集画面にインライン表示"""
    model = UserProfile
    can_delete = False
    verbose_name = 'ユーザープロファイル'
    verbose_name_plural = 'ユーザープロファイル'

    fieldsets = (
        ('アクセス権限 (ロール)', {
            'fields': ('roles',),
            'description': '''
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin-bottom: 15px;">
                    <h3 style="margin-top: 0;">📋 利用可能なロール</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>営業</strong> - 案件受注、顧客対応</li>
                        <li><strong>職人発注</strong> - 職人手配、工事管理</li>
                        <li><strong>経理</strong> - 財務管理、入出金管理</li>
                        <li><strong>役員</strong> - 経営管理（全権限）</li>
                    </ul>
                    <p style="margin-top: 10px; margin-bottom: 0;"><em>※ 複数のロールを割り当てることができます。例: ["営業", "経理"]</em></p>
                </div>
            '''
        }),
    )


# Django標準のUserAdminを拡張
class CustomUserAdmin(BaseUserAdmin):
    """カスタムユーザー管理 - UserProfileとロールを統合"""
    inlines = (UserProfileInline,)

    # ユーザー一覧に表示する項目
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'get_roles',
        'is_staff',
        'is_active',
        'last_login',
    )

    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups',
    )

    # ユーザー編集画面のフィールドセット
    fieldsets = (
        ('🔐 ログイン情報', {
            'fields': ('username', 'password')
        }),
        ('👤 個人情報', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('🔑 権限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': '''
                <div style="background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin-bottom: 10px;">
                    <strong>⚠️ 権限について</strong><br>
                    • <strong>有効</strong>: ログイン可能にする<br>
                    • <strong>スタッフ</strong>: Django管理画面にアクセス可能<br>
                    • <strong>スーパーユーザー</strong>: すべての権限を持つ（注意して使用）<br>
                    <br>
                    <strong>通常のユーザーには「有効」と「スタッフ」のみをチェックしてください。</strong>
                </div>
            '''
        }),
        ('📅 重要な日付', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    # 新規ユーザー作成時のフィールドセット
    add_fieldsets = (
        ('🆕 新規ユーザー作成', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
            'description': '''
                <div style="background-color: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin-bottom: 15px;">
                    <h3 style="margin-top: 0;">📝 ユーザー作成の手順</h3>
                    <ol>
                        <li>ユーザー名とパスワードを入力して「保存」</li>
                        <li>次の画面で個人情報とロールを設定</li>
                        <li>「有効」と「スタッフ」にチェックを入れる</li>
                        <li>下部の「ユーザープロファイル」セクションでロールを割り当て</li>
                    </ol>
                    <p style="margin-bottom: 0;"><strong>ヒント:</strong> 最初は最小限の権限で作成し、後から必要に応じて追加してください。</p>
                </div>
            '''
        }),
        ('👤 個人情報（オプション）', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('🔑 初期権限（オプション）', {
            'classes': ('wide', 'collapse'),
            'fields': ('is_active', 'is_staff'),
            'description': '<p><strong>推奨:</strong> 「有効」と「スタッフ」の両方にチェック</p>'
        }),
    )

    def get_roles(self, obj):
        """ユーザーのロールを表示"""
        try:
            profile = obj.userprofile
            if profile.roles:
                return ", ".join(profile.roles)
            return "ロールなし"
        except UserProfile.DoesNotExist:
            return "プロファイルなし"
    get_roles.short_description = "🏷️ ロール"

    def save_formset(self, request, form, formset, change):
        """インラインのUserProfileを保存時に自動作成"""
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

        # UserProfileが存在しない場合は自動作成
        if form.instance:
            UserProfile.objects.get_or_create(user=form.instance)


# Django標準のUser管理を上書き
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
