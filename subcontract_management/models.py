from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from order_management.models import Project


class InternalWorker(models.Model):
    """社内担当者管理"""
    DEPARTMENT_CHOICES = [
        ('construction', '施工部'),
        ('sales', '営業部'),
        ('design', '設計部'),
        ('management', '管理部'),
        ('quality', '品質管理'),
        ('safety', '安全管理'),
        ('other', 'その他')
    ]

    name = models.CharField(max_length=100, verbose_name='氏名')
    employee_id = models.CharField(max_length=20, unique=True, verbose_name='社員番号')
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        verbose_name='所属部署'
    )
    position = models.CharField(max_length=50, blank=True, verbose_name='役職')
    email = models.EmailField(blank=True, verbose_name='メールアドレス')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話番号')

    # 作業関連情報
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='標準時給'
    )
    specialties = models.TextField(blank=True, verbose_name='専門分野')
    skills = models.TextField(blank=True, verbose_name='スキル・資格')

    # ステータス
    is_active = models.BooleanField(default=True, verbose_name='在職中')
    hire_date = models.DateField(null=True, blank=True, verbose_name='入社日')

    # システム情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '社内担当者'
        verbose_name_plural = '社内担当者一覧'
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_department_display()})"

    def get_total_assignments(self):
        """総担当件数を取得"""
        return self.subcontract_set.filter(worker_type='internal').count()

    def get_current_assignments(self):
        """現在の担当案件数を取得"""
        from datetime import date
        return self.subcontract_set.filter(
            worker_type='internal',
            project__work_end_date__gte=date.today()
        ).count()

    def get_total_amount(self):
        """総作業金額を取得"""
        return self.subcontract_set.filter(
            worker_type='internal'
        ).aggregate(
            total=models.Sum('contract_amount')
        )['total'] or 0


class Contractor(models.Model):
    CONTRACTOR_TYPE_CHOICES = [
        ('individual', '個人職人'),
        ('company', '協力会社')
    ]

    name = models.CharField(max_length=100, verbose_name='工事業者名')
    address = models.TextField(verbose_name='工事業者住所')
    contact_person = models.CharField(max_length=50, blank=True, verbose_name='担当者名')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話番号')
    email = models.EmailField(blank=True, verbose_name='メールアドレス')
    contractor_type = models.CharField(
        max_length=20,
        choices=CONTRACTOR_TYPE_CHOICES,
        default='company',
        verbose_name='業者種別'
    )
    specialties = models.TextField(blank=True, verbose_name='得意分野')
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=0, null=True, blank=True, verbose_name='時給単価'
    )
    is_active = models.BooleanField(default=True, verbose_name='有効')

    # スキル・評価管理 - Phase 8 追加
    skill_categories = models.JSONField(
        default=list,
        blank=True,
        verbose_name='スキルカテゴリ',
        help_text='例: ["電気工事", "空調工事", "給排水工事"]'
    )
    skill_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', '初級'),
            ('intermediate', '中級'),
            ('advanced', '上級'),
            ('expert', 'エキスパート'),
        ],
        default='intermediate',
        verbose_name='スキルレベル'
    )
    service_areas = models.JSONField(
        default=list,
        blank=True,
        verbose_name='対応可能地域',
        help_text='例: ["東京23区", "神奈川県全域"]'
    )
    trust_level = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='信頼度',
        help_text='1-5の5段階評価。4以上はCLが直接アサイン可能'
    )
    certifications = models.TextField(
        blank=True,
        verbose_name='保有資格',
        help_text='改行区切りで複数入力可能'
    )

    # 実績管理 - Phase 8 追加
    total_projects = models.IntegerField(
        default=0,
        verbose_name='総案件数'
    )
    success_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        verbose_name='成功率(%)',
        help_text='問題なく完了した案件の割合'
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name='平均評価',
        help_text='ContractorReviewからの平均評価（1-5）'
    )
    last_project_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='最終案件日'
    )

    # 銀行口座情報
    bank_name = models.CharField(max_length=100, blank=True, verbose_name='銀行名')
    branch_name = models.CharField(max_length=100, blank=True, verbose_name='支店名')
    account_type = models.CharField(
        max_length=10,
        choices=[
            ('ordinary', '普通'),
            ('current', '当座'),
            ('savings', '貯蓄'),
        ],
        default='ordinary',
        blank=True,
        verbose_name='口座種別'
    )
    account_number = models.CharField(max_length=20, blank=True, verbose_name='口座番号')
    account_holder = models.CharField(max_length=100, blank=True, verbose_name='口座名義')

    # 支払い条件
    payment_day = models.IntegerField(
        null=True, blank=True,
        verbose_name='支払日',
        help_text='毎月の支払日（1-31）。例：25日払いの場合は25'
    )
    payment_cycle = models.CharField(
        max_length=10,
        choices=[
            ('monthly', '月払い'),
            ('bimonthly', '隔月払い'),
            ('quarterly', '四半期払い'),
            ('custom', 'その他'),
        ],
        default='monthly',
        blank=True,
        verbose_name='支払サイクル'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '発注先'
        verbose_name_plural = '発注先一覧'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_contractor_type_display()})"

    def get_total_subcontracts(self):
        """総外注件数を取得"""
        return self.subcontract_set.count()

    def get_total_amount(self):
        """総外注金額を取得"""
        return self.subcontract_set.aggregate(
            total=models.Sum('contract_amount')
        )['total'] or 0

    def get_unpaid_amount(self):
        """未払い金額を取得"""
        return self.subcontract_set.filter(
            payment_status='pending'
        ).aggregate(
            total=models.Sum('billed_amount')
        )['total'] or 0


class Subcontract(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', '未払い'),
        ('processing', '処理中'),
        ('paid', '支払済')
    ]

    WORKER_TYPE_CHOICES = [
        ('external', '外注'),
        ('internal', '社内リソース')
    ]

    # 案件情報（受注フォーマットから連携）
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name='関連案件'
    )
    management_no = models.CharField(max_length=20, verbose_name='管理No')
    site_name = models.CharField(max_length=200, verbose_name='現場名')
    site_address = models.TextField(verbose_name='現場住所')

    # 作業者タイプ
    worker_type = models.CharField(
        max_length=20,
        choices=WORKER_TYPE_CHOICES,
        default='external',
        verbose_name='作業者タイプ'
    )

    # 発注先情報（外注の場合のみ使用）
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='発注先'
    )

    # 社内リソース情報（社内の場合のみ使用）
    internal_worker = models.ForeignKey(
        InternalWorker,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='社内担当者'
    )
    internal_worker_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='担当者名（手動入力）'
    )
    internal_department = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='所属部署'
    )

    # 社内リソースの料金体系
    INTERNAL_PRICING_CHOICES = [
        ('hourly', '時給ベース'),
        ('project', '案件単位')
    ]
    internal_pricing_type = models.CharField(
        max_length=20,
        choices=INTERNAL_PRICING_CHOICES,
        default='hourly',
        verbose_name='料金体系'
    )

    # 税込/税抜選択
    TAX_TYPE_CHOICES = [
        ('include', '税込'),
        ('exclude', '税抜')
    ]
    tax_type = models.CharField(
        max_length=10,
        choices=TAX_TYPE_CHOICES,
        default='include',
        verbose_name='税込/税抜'
    )

    internal_hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='時給単価'
    )
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='見積工数（時間）'
    )

    # 金額管理
    contract_amount = models.DecimalField(
        max_digits=10, decimal_places=0, verbose_name='依頼金額'
    )
    billed_amount = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name='被請求額'
    )

    # スケジュール・支払い
    payment_due_date = models.DateField(
        null=True, blank=True, verbose_name='出金予定日'
    )
    payment_date = models.DateField(
        null=True, blank=True, verbose_name='出金日'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='出金状況'
    )

    # 部材費管理
    material_item_1 = models.CharField(
        max_length=100, blank=True, verbose_name='部材費項目①'
    )
    material_cost_1 = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='部材費代①'
    )
    material_item_2 = models.CharField(
        max_length=100, blank=True, verbose_name='部材費項目②'
    )
    material_cost_2 = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='部材費代②'
    )
    material_item_3 = models.CharField(
        max_length=100, blank=True, verbose_name='部材費項目③'
    )
    material_cost_3 = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='部材費代③'
    )

    # 自動計算項目
    total_material_cost = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name='部材費合計'
    )

    # 動的部材費管理
    dynamic_material_costs = models.JSONField(
        default=list, blank=True, verbose_name='動的部材費情報'
    )

    # 動的費用項目（時給ベースの追加費用、案件単位の費用項目）
    dynamic_cost_items = models.JSONField(
        default=list, blank=True, verbose_name='動的費用項目'
    )

    # その他
    purchase_order_issued = models.BooleanField(default=False, verbose_name='発注書発行')
    work_description = models.TextField(blank=True, verbose_name='作業内容')
    notes = models.TextField(blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '発注管理'
        verbose_name_plural = '発注管理一覧'
        ordering = ['-created_at']

    def __str__(self):
        if self.worker_type == 'external' and self.contractor:
            return f"{self.management_no} - {self.contractor.name}"
        elif self.worker_type == 'internal':
            if self.internal_worker:
                return f"{self.management_no} - {self.internal_worker.name}（社内）"
            elif self.internal_worker_name:
                return f"{self.management_no} - {self.internal_worker_name}（社内）"
            else:
                return f"{self.management_no} - 社内担当者未設定"
        else:
            return f"{self.management_no} - 作業者未設定"

    def save(self, *args, **kwargs):
        # プロジェクト情報を自動取得
        if self.project:
            self.management_no = self.project.management_no
            self.site_name = self.project.site_name
            self.site_address = self.project.site_address

        # 部材費合計を自動計算（既存の固定フィールド + 動的フィールド）
        fixed_total = (
            Decimal(str(self.material_cost_1)) +
            Decimal(str(self.material_cost_2)) +
            Decimal(str(self.material_cost_3))
        )

        # 動的部材費も計算に含める
        dynamic_total = Decimal('0')
        if self.dynamic_material_costs:
            for item in self.dynamic_material_costs:
                if 'cost' in item:
                    dynamic_total += Decimal(str(item['cost']))

        self.total_material_cost = fixed_total + dynamic_total

        # 社内リソースの場合、動的費用項目に基づいてcontract_amountを再計算
        if (self.worker_type == 'internal' and
            self.internal_pricing_type in ['hourly', 'project'] and
            self.dynamic_cost_items):

            dynamic_cost_total = Decimal('0')
            for item in self.dynamic_cost_items:
                if 'cost' in item:
                    dynamic_cost_total += Decimal(str(item['cost']))

            # 時給ベースの場合は基本料金に追加
            if self.internal_pricing_type == 'hourly':
                base_amount = Decimal('0')
                if self.internal_hourly_rate and self.estimated_hours:
                    base_amount = Decimal(str(self.internal_hourly_rate)) * Decimal(str(self.estimated_hours))
                self.contract_amount = base_amount + dynamic_cost_total
            # 案件単位の場合は動的項目の合計
            elif self.internal_pricing_type == 'project':
                self.contract_amount = dynamic_cost_total

        super().save(*args, **kwargs)

        # 案件の利益分析を更新
        self.update_project_profit_analysis()

    def update_project_profit_analysis(self):
        """案件の利益分析を更新"""
        try:
            analysis, created = ProjectProfitAnalysis.objects.get_or_create(
                project=self.project
            )
            analysis.calculate_profit()
        except Exception:
            pass  # エラーハンドリング

    def get_total_cost(self):
        """総コスト（外注費+部材費+追加費用）を計算"""
        # 基本コスト
        base_cost = self.billed_amount + self.total_material_cost

        # 追加費用を計算
        additional_cost = 0
        if self.dynamic_cost_items:
            for item in self.dynamic_cost_items:
                if 'cost' in item:
                    additional_cost += float(item['cost'])

        return base_cost + additional_cost

    def get_payment_status_color(self):
        """支払いステータスの色を返す"""
        color_map = {
            'pending': 'warning',
            'processing': 'info',
            'paid': 'success'
        }
        return color_map.get(self.payment_status, 'secondary')

    def is_payment_overdue(self):
        """支払いが遅延しているかチェック"""
        if not self.payment_due_date or self.payment_status == 'paid':
            return False
        return timezone.now().date() > self.payment_due_date


class ProjectProfitAnalysis(models.Model):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        verbose_name='対象案件'
    )

    # 収入
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, verbose_name='総売上'
    )

    # 支出
    total_subcontract_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, verbose_name='外注費合計'
    )
    total_material_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, verbose_name='部材費合計'
    )
    total_expense = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, verbose_name='総支出'
    )

    # 利益
    gross_profit = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, verbose_name='粗利益'
    )
    profit_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name='利益率(%)'
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '案件別利益分析'
        verbose_name_plural = '案件別利益分析一覧'

    def __str__(self):
        return f"{self.project.management_no} - 利益率{self.profit_rate}%"

    def calculate_profit(self):
        """利益を再計算"""
        # 売上（受注額）
        self.total_revenue = self.project.billing_amount

        # 外注費合計
        subcontracts = self.project.subcontract_set.all()
        self.total_subcontract_cost = sum(
            sub.billed_amount for sub in subcontracts
        )

        # 部材費合計
        self.total_material_cost = sum(
            sub.total_material_cost for sub in subcontracts
        )

        # 総支出
        self.total_expense = self.total_subcontract_cost + self.total_material_cost

        # 粗利益
        self.gross_profit = self.total_revenue - self.total_expense

        # 利益率
        if self.total_revenue > 0:
            self.profit_rate = (self.gross_profit / self.total_revenue) * 100
        else:
            self.profit_rate = 0

        self.save()

    def get_profit_rate_color(self):
        """利益率に応じた色を返す"""
        if self.profit_rate >= 30:
            return 'success'  # 緑
        elif self.profit_rate >= 15:
            return 'warning'  # 黄
        elif self.profit_rate >= 0:
            return 'info'     # 青
        else:
            return 'danger'   # 赤
