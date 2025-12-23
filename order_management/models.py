from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime
from decimal import Decimal


class Project(models.Model):
    # 受注ヨミの選択肢（営業見込み度合い）
    PROJECT_STATUS_CHOICES = [
        ('ネタ', 'ネタ'),  # 見込み案件
        ('A', 'A'),  # 受注確度高
        ('B', 'B'),  # 受注確度中
        ('受注確定', '受注確定'),  # 受注決定
        ('NG', 'NG'),  # 受注できず
    ]

    # 基本情報
    management_no = models.CharField(max_length=20, unique=True, verbose_name='管理No')
    site_name = models.CharField(max_length=200, verbose_name='現場名')
    site_address = models.TextField(verbose_name='現場住所', blank=True)  # 任意に変更
    work_type = models.CharField(max_length=50, verbose_name='施工種別')  # 旧: 種別
    material_labor_type = models.CharField(
        max_length=20,
        choices=[
            ('material_labor', '材工'),
            ('labor_only', '手間'),
            ('', '-'),
        ],
        default='',
        blank=True,
        verbose_name='材工/手間区分',
        help_text='材工=資材発注含む、手間=材料支給のみ'
    )

    # 受注・見積情報
    project_status = models.CharField(  # 旧: order_status
        max_length=20,  # max_lengthを20に拡張（「施工日待ち」対応）
        choices=PROJECT_STATUS_CHOICES,
        default='ネタ',  # 旧: 検討中
        verbose_name='受注ヨミ'
    )
    # DEPRECATED: estimate_issued_date moved to ProjectProgressStep (SSOT)
    estimate_not_required = models.BooleanField(
        default=False, verbose_name='見積書不要'
    )
    order_amount = models.DecimalField(  # 旧: estimate_amount
        max_digits=10, decimal_places=0, default=0, verbose_name='受注金額(税込)'  # 旧: 見積金額
    )
    parking_fee = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='駐車場代(税込)'
    )

    # 元請・担当情報（旧: 業者・担当情報）
    client_name = models.CharField(max_length=100, verbose_name='元請名', blank=True)  # 旧: contractor_name (請負業者名)
    client_address = models.TextField(verbose_name='元請住所', blank=True)  # 旧: contractor_address (請負業者住所)、任意に変更
    project_manager = models.CharField(max_length=50, verbose_name='案件担当', blank=True)

    # スケジュール
    payment_due_date = models.DateField(
        null=True, blank=False, verbose_name='入金予定日'  # Phase 5: 必須化
    )

    # Phase 5: 施工日入力方法の改善
    asap_requested = models.BooleanField(
        default=False, verbose_name='最短希望',
        help_text='できるだけ早く施工を希望'
    )
    work_date_specified = models.BooleanField(
        default=False, verbose_name='施工日指定あり',
        help_text='施工日を具体的に指定する'
    )

    # DEPRECATED: work_start_date, work_end_date, and completion flags moved to ProjectProgressStep (SSOT)
    contract_date = models.DateField(
        null=True, blank=True, verbose_name='契約日'
    )

    # 請求・経費管理
    invoice_issued = models.BooleanField(default=False, verbose_name='請求書発行')

    # Phase 5: 請求書発行ステータス管理
    invoice_status = models.CharField(
        max_length=20,
        choices=[
            ('not_issued', '未発行'),
            ('issued', '発行済み'),
        ],
        default='not_issued',
        verbose_name='請求書発行ステータス'
    )
    expense_item_1 = models.CharField(
        max_length=100, blank=True, verbose_name='諸経費項目①'
    )
    expense_amount_1 = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='諸経費代(税込)①'
    )
    expense_item_2 = models.CharField(
        max_length=100, blank=True, verbose_name='諸経費項目②'
    )
    expense_amount_2 = models.DecimalField(
        max_digits=8, decimal_places=0, default=0, verbose_name='諸経費代(税込)②'
    )

    # 自動計算項目
    billing_amount = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name='請求額実請求'
    )
    amount_difference = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name='増減'
    )

    # 利益関連（自動計算・キャッシュ）
    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True,
        verbose_name='粗利額',
        help_text='売上 - 売上原価（自動計算・キャッシュ）'
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        blank=True,
        verbose_name='粗利率（%）',
        help_text='粗利額 / 売上 × 100（自動計算・キャッシュ）'
    )

    # 現地調査関連
    survey_required = models.BooleanField(default=False, verbose_name='現地調査必要')
    # DEPRECATED: survey_status was removed in migration 0059
    # Now computed via @property survey_status_computed from ProjectProgressStep (SSOT)
    # DEPRECATED: survey_date and survey_assignees moved to ProjectProgressStep (SSOT)

    # DEPRECATED: witness_date, witness_status, witness_assignees, witness_assignee_type moved to ProjectProgressStep (SSOT)

    # 見積もりステータス拡張 - Phase 11 追加
    estimate_status = models.CharField(
        max_length=20,
        choices=[
            ('not_issued', '未発行'),
            ('issued', '見積もり書発行'),
            ('under_review', '見積もり審査中'),
            ('approved', '承認'),
            ('cancelled', 'キャンセル'),
        ],
        default='not_issued',
        verbose_name='見積もりステータス'
    )
    estimate_notes = models.TextField(
        blank=True,
        verbose_name='見積もり備考',
        help_text='見積もりに関する備考・メモ'
    )
    contractor_estimate_amount = models.TextField(
        blank=True,
        verbose_name='下請業者見積金額',
        help_text='下請業者の見積金額（フリーテキスト）'
    )

    # 着工ステータス拡張 - Phase 11 追加
    construction_status = models.CharField(
        max_length=20,
        choices=[
            ('waiting', '着工日待ち'),
            ('in_progress', '工事中'),
            ('completed', '完工'),
            ('cancelled', 'キャンセル'),
        ],
        default='waiting',
        verbose_name='工事ステータス'
    )
    construction_assignees = models.JSONField(
        default=list, blank=True,
        verbose_name='施工担当者',
        help_text='施工の担当者リスト（職人）'
    )

    # 支払管理（業者への支払）
    payment_scheduled_date = models.DateField(
        null=True, blank=True,
        verbose_name='支払予定日',
        help_text='業者への支払予定日'
    )
    payment_executed_date = models.DateField(
        null=True, blank=True,
        verbose_name='支払実行日',
        help_text='実際に支払を行った日'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', '予定'),
            ('executed', '支払済み'),
            ('overdue', '遅延'),
            ('cancelled', 'キャンセル'),
        ],
        default='scheduled',
        verbose_name='支払状況'
    )
    payment_amount = models.DecimalField(
        max_digits=10, decimal_places=0,
        null=True, blank=True,
        verbose_name='支払金額',
        help_text='実際の支払金額（請求額と異なる場合に使用）'
    )
    payment_memo = models.TextField(
        blank=True,
        verbose_name='支払メモ',
        help_text='支払に関する特記事項'
    )

    # 入金管理（元請からの入金） - Phase 1 追加
    payment_received_date = models.DateField(
        null=True, blank=True,
        verbose_name='入金実行日',
        help_text='元請から実際に入金があった日'
    )
    payment_received_amount = models.DecimalField(
        max_digits=10, decimal_places=0,
        null=True, blank=True,
        verbose_name='入金金額',
        help_text='実際の入金金額（請求額と異なる場合に使用）'
    )
    incoming_payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '入金待ち'),
            ('received', '入金済み'),
            ('partial', '一部入金'),
            ('overdue', '遅延'),
        ],
        default='pending',
        verbose_name='入金ステータス',
        help_text='元請からの入金状況'
    )
    invoice_custom_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='請求書カスタムデータ',
        help_text='請求書のカスタマイズされたデータ（備考、工期、現場名など）'
    )
    invoice_issued = models.BooleanField(
        default=False,
        verbose_name='請求書発行済み'
    )
    invoice_file = models.FileField(
        upload_to='invoices/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='請求書PDFファイル'
    )

    # 完工・請求管理 - Phase 1 追加
    completion_date = models.DateField(
        null=True, blank=True,
        verbose_name='完工日',
        help_text='工事が完工した日（発生主義売上の基準日）'
    )

    # プロジェクト進捗状況（キャッシュ）- 自動計算結果を保存
    current_stage = models.CharField(
        max_length=20,
        default='未開始',
        verbose_name='現在の進捗状況',
        help_text='JavaScriptで計算された進捗状況を保存（完工、工事中、着工日待ちなど）'
    )
    current_stage_color = models.CharField(
        max_length=20,
        default='secondary',
        verbose_name='進捗状況の色',
        help_text='verified, success, warning, secondary'
    )
    invoice_issue_datetime = models.DateTimeField(
        null=True, blank=True,
        verbose_name='請求書発行日時',
        help_text='請求書を発行した日時'
    )

    # 元請会社連携 - Phase 8 追加
    client_company = models.ForeignKey(
        'ClientCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects',
        verbose_name='元請会社'
    )

    # 支払いサイクル情報（元請会社から自動入力、案件ごとに編集可能）
    payment_cycle = models.CharField(
        max_length=20,
        choices=[
            ('monthly', '月1回'),
            ('bimonthly', '月2回'),
            ('weekly', '週1回'),
            ('custom', 'その他'),
        ],
        blank=True,
        verbose_name='支払サイクル',
        help_text='元請会社選択時に自動入力されます。案件ごとに編集可能です。'
    )
    closing_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='締め日',
        help_text='月末締めの場合は31、20日締めの場合は20'
    )
    payment_offset_months = models.IntegerField(
        null=True,
        blank=True,
        choices=[
            (0, '当月'),
            (1, '翌月'),
            (2, '翌々月'),
            (3, '3ヶ月後'),
        ],
        verbose_name='支払月',
        help_text='締日から何ヶ月後に支払うか（0=当月、1=翌月、2=翌々月）'
    )
    payment_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='支払日',
        help_text='支払月の何日に支払うか（1-31）。例：25日払いの場合は25'
    )

    # 鍵受け渡し管理 - Phase 8 追加
    key_handover_location = models.TextField(
        blank=True,
        verbose_name='鍵受け渡し場所',
        help_text='案件ごとの鍵受け渡し場所'
    )
    key_handover_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name='鍵受け渡し日時'
    )
    key_handover_notes = models.TextField(
        blank=True,
        verbose_name='鍵受け渡しメモ'
    )

    # 承認フロー - Phase 8 追加
    requires_approval = models.BooleanField(
        default=False,
        verbose_name='承認必要',
        help_text='金額や条件により承認が必要な案件'
    )
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', '承認不要'),
            ('pending', '承認待ち'),
            ('approved', '承認済み'),
            ('rejected', '却下'),
        ],
        default='not_required',
        verbose_name='承認ステータス'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_projects',
        verbose_name='承認者'
    )
    approved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='承認日時'
    )

    # 優先度管理 - Phase 8 追加
    priority_score = models.IntegerField(
        default=0,
        verbose_name='優先度スコア',
        help_text='自動計算される優先度（高いほど優先）'
    )

    # 完了報告管理 - Phase 8 追加
    completion_report_content = models.TextField(
        blank=True,
        verbose_name='完了報告内容',
        help_text='完了報告の本文（元請会社のテンプレートから自動入力可能）'
    )
    completion_report_date = models.DateField(
        null=True, blank=True,
        verbose_name='完了報告日'
    )
    completion_report_status = models.CharField(
        max_length=20,
        choices=[
            ('not_created', '未作成'),
            ('draft', '下書き'),
            ('submitted', '提出済み'),
        ],
        default='not_created',
        verbose_name='完了報告ステータス'
    )
    completion_report_notes = models.TextField(
        blank=True,
        verbose_name='完了報告メモ',
        help_text='完了報告に関する特記事項'
    )
    completion_report_file = models.FileField(
        upload_to='completion_reports/',
        null=True,
        blank=True,
        verbose_name='完了報告ファイル',
        help_text='完了報告のPDF/Excelファイル（アップロード）'
    )
    completion_report_completed = models.BooleanField(
        default=False,
        verbose_name='完了報告完了',
        help_text='完了報告が完了したかどうか'
    )

    # その他
    progress_comment = models.TextField(blank=True, verbose_name='進捗コメント', help_text='案件の進捗に関する詳細なコメント')
    detailed_comments = models.JSONField(default=list, blank=True, verbose_name='詳細コメント履歴', help_text='複数の詳細コメントを時系列で保存')
    notes = models.TextField(blank=True, verbose_name='備考')
    additional_items = models.JSONField(default=dict, blank=True, verbose_name="追加項目")
    is_draft = models.BooleanField(default=False, verbose_name='下書き', help_text='下書き保存されたプロジェクト')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '案件'
        verbose_name_plural = '案件一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.management_no} - {self.site_name}"

    def save(self, *args, **kwargs):
        """
        プロジェクト保存時に、レガシーフィールド（work_start_date/work_end_date）を
        ProjectProgressStep（SSOT）に自動同期する。
        """
        # まず親のsave()を呼んでモデルを保存（pkが確定する）
        super().save(*args, **kwargs)

        # pkが確定した後、レガシーフィールドをSSOTに同期
        if self.pk:
            from order_management.services.progress_step_service import set_step_scheduled_date

            try:
                # work_start_date → construction_start ステップに同期
                if self.work_start_date:
                    set_step_scheduled_date(
                        self,
                        'construction_start',
                        self.work_start_date.strftime('%Y-%m-%d')
                    )

                # work_end_date → completion ステップに同期
                if self.work_end_date:
                    set_step_scheduled_date(
                        self,
                        'completion',
                        self.work_end_date.strftime('%Y-%m-%d')
                    )
            except Exception as e:
                # 同期エラーが発生しても保存処理は継続
                print(f"⚠ Warning: Failed to sync dates to ProjectProgressStep: {e}")

    def generate_management_no(self):
        """管理No自動採番（6桁）

        フォーマット: {年の下2桁}{6桁連番}
        例: 25000001, 25000002, ...

        Note: CSVインポート後も連番を継続するため、
        旧形式のプレフィックス（P, Mなど）付きの番号からも最大値を取得
        """
        current_year = timezone.now().year
        year_suffix = str(current_year)[-2:]  # 下2桁

        # 今年の全案件から最新番号を取得（旧形式・新形式両対応）
        # 旧形式: P2500299, M250298
        # 新形式: 25000299
        projects = Project.objects.filter(
            management_no__regex=r'^[A-Z]*' + year_suffix + r'\d+'
        ).values_list('management_no', flat=True)

        import re
        # 旧形式（プレフィックス有）と新形式（プレフィックス無）両対応
        pattern = r'^[A-Z]*' + year_suffix + r'(\d+)$'
        max_num = 0

        # 全プロジェクトから最大の連番を取得（文字列ソートではなく数値比較）
        for mgmt_no in projects:
            match = re.search(pattern, mgmt_no)
            if match:
                seq_num = int(match.group(1))
                max_num = max(max_num, seq_num)

        new_num = max_num + 1 if max_num > 0 else 1

        return f'{year_suffix}{new_num:06d}'

    def save(self, *args, **kwargs):
        # 管理No自動採番
        if not self.management_no:
            self.management_no = self.generate_management_no()

        # 自動計算処理
        self.billing_amount = (
            Decimal(str(self.order_amount)) +
            Decimal(str(self.parking_fee)) +
            Decimal(str(self.expense_amount_1)) +
            Decimal(str(self.expense_amount_2))
        )
        self.amount_difference = (
            Decimal(str(self.billing_amount)) -
            Decimal(str(self.order_amount))
        )

        # 利益計算（既存プロジェクトの場合のみ）
        # Note: 新規作成時はpkがないため、シグナルで後から計算
        if self.pk:
            self._update_profit_cache()

        # Phase 8: 元請会社連携処理
        if self.client_company:
            # 鍵受け渡し場所のデフォルト値設定
            if not self.key_handover_location and self.client_company.default_key_handover_location:
                self.key_handover_location = self.client_company.default_key_handover_location

            # 完了報告テンプレートのデフォルト値設定
            if not self.completion_report_content and self.client_company.completion_report_notes:
                self.completion_report_content = self.client_company.completion_report_notes

            # 承認必要チェック
            if self.order_amount >= self.client_company.approval_threshold:
                self.requires_approval = True
                if self.approval_status == 'not_required':
                    self.approval_status = 'pending'
            else:
                self.requires_approval = False
                if self.approval_status == 'pending':
                    self.approval_status = 'not_required'

        # Phase 8: 優先度スコア計算
        self.priority_score = self._calculate_priority_score()

        # NGステータス時の進捗自動キャンセル処理
        # NOTE: witness_status, survey_status, estimate_status, construction_status are @property fields
        # They cannot be assigned directly. Progress management is now handled by ProjectProgressStep model.
        # This legacy code is commented out to prevent AttributeError.
        # if self.project_status == 'NG':
        #     # 各進捗ステータスをキャンセル状態に設定
        #     if self.witness_status not in ['completed', 'cancelled']:
        #         self.witness_status = 'cancelled'
        #     if self.survey_status not in ['completed', 'cancelled', 'not_required']:
        #         self.survey_status = 'cancelled'
        #     if self.estimate_status not in ['approved', 'cancelled', 'not_issued']:
        #         self.estimate_status = 'cancelled'
        #     if self.construction_status not in ['completed', 'cancelled']:
        #         self.construction_status = 'cancelled'

        # 着工日待ち状態でAヨミに自動変更（NGでない場合のみ）
        # NOTE: construction_status is now a property, not a field. Commenting out this logic.
        # if self.pk and self.construction_status == 'waiting' and self.project_status not in ['ネタ', 'B', 'C', '受注確定', 'A', 'NG']:
        #     # 着工日待ち（職人が決まった状態）ならAヨミに自動変更
        #     self.project_status = 'A'

        super().save(*args, **kwargs)

    def _update_profit_cache(self):
        """利益額と利益率をキャッシュフィールドに更新"""
        try:
            revenue_breakdown = self.get_revenue_breakdown()
            self.gross_profit = revenue_breakdown.get('gross_profit', Decimal('0'))
            self.profit_margin = revenue_breakdown.get('profit_margin', Decimal('0'))
        except Exception as e:
            # エラー時はゼロに設定（新規作成時など）
            self.gross_profit = Decimal('0')
            self.profit_margin = Decimal('0')
            print(f"⚠ Warning: Failed to calculate profit for project {self.pk}: {e}")

    def _calculate_priority_score(self):
        """優先度スコアを計算（高いほど優先）"""
        score = 0

        # 金額ベース（100万円ごとに10ポイント）
        if self.order_amount:
            score += int(self.order_amount / 1000000) * 10

        # 工期の緊急度（開始日が近いほど高得点）
        if self.work_start_date:
            try:
                # work_start_dateがdateオブジェクトでない場合の処理
                from datetime import datetime
                if isinstance(self.work_start_date, str):
                    work_start = datetime.strptime(self.work_start_date, '%Y-%m-%d').date()
                else:
                    work_start = self.work_start_date

                days_until_start = (work_start - timezone.now().date()).days
                if days_until_start < 0:
                    # 既に開始日を過ぎている
                    score += 100
                elif days_until_start <= 3:
                    score += 50
                elif days_until_start <= 7:
                    score += 30
                elif days_until_start <= 14:
                    score += 10
            except (ValueError, TypeError, AttributeError):
                # 日付のパースに失敗した場合はスキップ
                pass

        # ステータスによる重み付け
        status_weights = {
            '施工日待ち': 40,  # 緊急度高
            '進行中': 30,
            'ネタ': 10,
            '完工': 0,
            'NG': 0,
        }
        score += status_weights.get(self.project_status, 0)

        # 承認待ちは優先度を上げる
        if self.approval_status == 'pending':
            score += 20

        return score

    def get_status_color(self):
        """ステータスに応じた背景色を返す"""
        color_map = {
            '完工': 'bg-success',     # 緑（旧: 受注）
            'NG': 'bg-secondary',     # グレー
            '施工日待ち': 'bg-danger', # ピンク/赤（旧: A）
            'ネタ': 'bg-warning',     # 黄色（旧: 検討中）
            '進行中': 'bg-info'       # 青（新規）
        }
        return color_map.get(self.project_status, '')

    def get_status_color_hex(self):
        """受注ヨミ（project_status）に応じた背景色（Hex）を返す

        サマリーモードのバッジ色を薄くした色を使用：
        - 受注確定: 緑系 (bg-success)
        - A: 赤系 (bg-danger)
        - B: 黄色系 (bg-warning)
        - NG: グレー系 (bg-secondary)
        - ネタ: 紫系 (カスタム)
        """
        color_map = {
            '受注確定': '#d4edda',   # 薄い緑 (success系)
            'A': '#f8d7da',          # 薄い赤 (danger系)
            'B': '#fff3cd',          # 薄い黄色 (warning系)
            'NG': '#e2e3e5',        # 薄いグレー (secondary系)
            'ネタ': '#f3e8ff',       # 薄い紫 (カスタム)
        }
        return color_map.get(self.project_status, '#ffffff')

    def get_work_progress_percentage(self):
        """工事進捗率を計算して返す（実際の進捗ステップベース）"""
        # 実際の進捗ステップから計算
        active_steps = self.progress_steps.filter(is_active=True)
        if not active_steps.exists():
            # 進捗ステップがない場合は日付ベースで計算
            return self._get_date_based_progress()

        total_steps = active_steps.count()
        completed_steps = active_steps.filter(is_completed=True).count()

        if total_steps == 0:
            return 0

        return int((completed_steps / total_steps) * 100)

    def _get_date_based_progress(self):
        """日付ベースの進捗計算（フォールバック）"""
        if not self.work_start_date or not self.work_end_date:
            return 0

        try:
            from datetime import datetime
            # 日付を安全に変換
            if isinstance(self.work_start_date, str):
                work_start = datetime.strptime(self.work_start_date, '%Y-%m-%d').date()
            else:
                work_start = self.work_start_date

            if isinstance(self.work_end_date, str):
                work_end = datetime.strptime(self.work_end_date, '%Y-%m-%d').date()
            else:
                work_end = self.work_end_date

            today = timezone.now().date()

            # 工事期間の計算
            total_days = (work_end - work_start).days
            if total_days <= 0:
                return 100

            # 経過日数の計算
            if today < work_start:
                return 0  # 開始前
            elif today > work_end:
                return 100  # 完了
            else:
                elapsed_days = (today - work_start).days
                return min(100, max(0, int((elapsed_days / total_days) * 100)))
        except (ValueError, TypeError, AttributeError):
            return 0

    def get_work_phase(self):
        """現在の工事フェーズを返す（実際の進捗ステップベース）"""
        # 実際の進捗ステップから判定
        active_steps = self.progress_steps.filter(is_active=True)
        if active_steps.exists():
            progress = self.get_work_progress_percentage()
            completed_steps_query = active_steps.filter(is_completed=True)
            completed_steps_count = completed_steps_query.count()

            # 完了したステップの内容に基づく判定
            if progress == 0:
                return '開始前'
            elif progress == 100:
                return '完了'
            else:
                # 完了したステップの種類を確認
                completed_step_names = list(completed_steps_query.values_list('template__name', flat=True))

                # 請求書発行が完了している場合
                if '請求書発行' in completed_step_names:
                    return '完了間近'
                # 工事終了が完了している場合
                elif '工事終了' in completed_step_names:
                    return '完了間近'
                # 工事開始が完了している場合
                elif '工事開始' in completed_step_names:
                    if progress >= 60:
                        return '施工中'
                    else:
                        return '着工'
                # 契約が完了している場合
                elif '契約' in completed_step_names:
                    return '契約済み'
                # 見積書発行のみ完了している場合
                elif '見積書発行' in completed_step_names:
                    return '見積済み'
                # その他の場合
                else:
                    if progress < 30:
                        return '初期段階'
                    elif progress < 80:
                        return '施工中'
                    else:
                        return '完了間近'

        # フォールバック：日付ベース
        if not self.work_start_date or not self.work_end_date:
            if self.project_status == '完工':  # 旧: 受注
                return '準備中'
            return '未定'

        try:
            from datetime import datetime
            # 日付を安全に変換
            if isinstance(self.work_start_date, str):
                work_start = datetime.strptime(self.work_start_date, '%Y-%m-%d').date()
            else:
                work_start = self.work_start_date

            if isinstance(self.work_end_date, str):
                work_end = datetime.strptime(self.work_end_date, '%Y-%m-%d').date()
            else:
                work_end = self.work_end_date

            today = timezone.now().date()

            if today < work_start:
                return '開始前'
            elif today > work_end:
                return '完了'
            else:
                progress = self._get_date_based_progress()
                if progress < 25:
                    return '着工'
                elif progress < 75:
                    return '施工中'
                else:
                    return '完了間近'
        except (ValueError, TypeError, AttributeError):
            return '未定'

    def get_progress_status(self):
        """進捗状況の総合判定を返す - 動的ステップシステムと同期"""
        # NGの場合のみ特別扱い（進捗表示不要）
        if self.project_status == 'NG':
            return {'phase': 'NG', 'color': 'secondary', 'percentage': 0}

        # 新5ステップシステムから現在の段階を取得
        stage_info = self.get_current_project_stage()
        phase = stage_info['stage']
        color = stage_info['color']

        # 実際に有効になっているステップを取得
        step_order = []
        if self.additional_items and 'step_order' in self.additional_items:
            step_order = self.additional_items.get('step_order', [])

        # step_orderが空の場合は、デフォルト4ステップを使用（survey除く）
        if not step_order:
            step_order = [
                {'step': 'step_attendance'},
                {'step': 'step_estimate'},
                {'step': 'step_construction_start'},
                {'step': 'step_completion'}
            ]

        total_steps = len(step_order)
        complex_fields = self.additional_items.get('complex_step_fields', {}) if self.additional_items else {}

        # 有効なステップの完了状況をチェック
        completed_count = 0

        # 今日の日付を取得
        from datetime import date
        today = date.today()

        for step_info in step_order:
            step_key = step_info.get('step')

            if step_key == 'step_attendance':
                # 予定日ベース：completedがtrueまたは予定日が過去なら完了
                attendance_completed_str = complex_fields.get('attendance_completed')
                attendance_completed = attendance_completed_str == 'true' or attendance_completed_str == True
                attendance_scheduled = complex_fields.get('attendance_scheduled_date')

                # 予定日を解析
                is_scheduled_past = False
                if attendance_scheduled:
                    try:
                        from datetime import datetime
                        scheduled_date = datetime.strptime(attendance_scheduled, '%Y-%m-%d').date()
                        is_scheduled_past = scheduled_date < today
                    except:
                        pass

                if attendance_completed or is_scheduled_past:
                    completed_count += 1
            elif step_key == 'step_survey':
                # 予定日ベース：completedがtrueまたは予定日が過去なら完了
                survey_completed_str = complex_fields.get('survey_completed')
                survey_completed = survey_completed_str == 'true' or survey_completed_str == True
                survey_scheduled = complex_fields.get('survey_scheduled_date')

                is_scheduled_past = False
                if survey_scheduled:
                    try:
                        from datetime import datetime
                        scheduled_date = datetime.strptime(survey_scheduled, '%Y-%m-%d').date()
                        is_scheduled_past = scheduled_date < today
                    except:
                        pass

                if survey_completed or is_scheduled_past:
                    completed_count += 1
            elif step_key == 'step_estimate':
                if self.estimate_issued_date or self.estimate_not_required:
                    completed_count += 1
            elif step_key == 'step_construction_start':
                # 予定日ベース：completedがtrueまたは予定日が過去なら完了
                construction_start_completed_str = complex_fields.get('construction_start_completed')
                construction_start_completed = construction_start_completed_str == 'true' or construction_start_completed_str == True
                construction_start_scheduled = complex_fields.get('construction_start_scheduled_date')

                is_scheduled_past = False
                if construction_start_scheduled:
                    try:
                        from datetime import datetime
                        scheduled_date = datetime.strptime(construction_start_scheduled, '%Y-%m-%d').date()
                        is_scheduled_past = scheduled_date < today
                    except:
                        pass

                if construction_start_completed or is_scheduled_past:
                    completed_count += 1
            elif step_key == 'step_completion':
                completion_completed_str = complex_fields.get('completion_completed')
                completion_completed = completion_completed_str == 'true' or completion_completed_str == True
                completion_scheduled = complex_fields.get('completion_scheduled_date')

                is_scheduled_past = False
                if completion_scheduled:
                    try:
                        from datetime import datetime
                        scheduled_date = datetime.strptime(completion_scheduled, '%Y-%m-%d').date()
                        is_scheduled_past = scheduled_date < today
                    except:
                        pass

                if completion_completed or is_scheduled_past:
                    completed_count += 1

        percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 0

        return {'phase': phase, 'color': color, 'percentage': percentage}

    def get_progress_details(self):
        """進捗の詳細情報を返す（ProjectProgressStepから読み込み）"""
        from order_management.services.progress_step_service import STEP_TEMPLATES
        from datetime import datetime, date

        # ProjectProgressStepから読み込み
        progress_steps = ProjectProgressStep.objects.filter(
            project=self,
            is_active=True
        ).select_related('template').order_by('order')

        # ステップテンプレートのマッピング（テンプレート名 -> キー）
        template_to_key = {}
        for key, config in STEP_TEMPLATES.items():
            template_to_key[config['name']] = key

        steps = []
        completed_steps_count = 0

        for progress_step in progress_steps:
            # テンプレート名からキーを取得
            step_key_without_prefix = template_to_key.get(progress_step.template.name)
            if not step_key_without_prefix:
                continue

            # step_プレフィックスを付ける
            step_key = f'step_{step_key_without_prefix}'

            # scheduled_dateを取得
            scheduled_date = ''
            if progress_step.value and isinstance(progress_step.value, dict):
                scheduled_date = progress_step.value.get('scheduled_date', '')

            # 完了判定: is_completedまたは予定日が過去
            is_scheduled_past = False
            if scheduled_date:
                try:
                    scheduled_date_obj = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                    is_scheduled_past = scheduled_date_obj < date.today()
                except:
                    pass

            is_completed = progress_step.is_completed or is_scheduled_past

            if is_completed:
                completed_steps_count += 1

            # ステップキーから日本語名へのマッピング
            step_name_mapping = {
                'attendance': '立ち会い',
                'survey': '現調',
                'estimate': '見積書発行',
                'construction_start': '着工',
                'completion': '完工',
                'contract': '契約',
                'invoice': '請求書発行',
                'permit_application': '許可申請',
                'material_order': '資材発注',
                'inspection': '検査'
            }

            japanese_name = step_name_mapping.get(step_key_without_prefix, progress_step.template.name)

            steps.append({
                'key': step_key,
                'name': japanese_name,
                'completed': is_completed,
                'completed_date': scheduled_date if is_completed else None,
                'scheduled_date': scheduled_date,
                'actual_date': None,
                'completed_checkbox': progress_step.is_completed,
                'has_not_required': False,
                'step_type': 'complex',
                'icon': 'fa-check'
            })

        total_steps = len(steps)

        return {
            'total_steps': total_steps,
            'completed_steps': completed_steps_count,
            'remaining_steps': total_steps - completed_steps_count,
            'steps': steps
        }

    def get_next_action_and_step(self):
        """次のアクションとNEXTステップを返す（動的ステップ管理対応）"""
        # 進捗詳細を取得
        details = self.get_progress_details()
        steps_list = details.get('steps', [])

        if not steps_list:
            return {
                'next_action': '',
                'next_step': '-'
            }

        # 未完了の最初のステップを見つける
        current_incomplete_step = None
        next_incomplete_step = None

        for i, step in enumerate(steps_list):
            if not step['completed']:
                if current_incomplete_step is None:
                    current_incomplete_step = step
                    # 次の未完了ステップを探す
                    if i + 1 < len(steps_list):
                        for next_step in steps_list[i + 1:]:
                            if not next_step['completed']:
                                next_incomplete_step = next_step
                                break
                    break

        # すべて完了している場合
        if current_incomplete_step is None:
            return {
                'next_action': '完了',
                'next_step': '-'
            }

        # 次のアクションを詳細に判定（JavaScript版と同じロジック）
        step_name = current_incomplete_step.get('name', '')
        step_type = current_incomplete_step.get('step_type')
        step_key = current_incomplete_step.get('key')
        scheduled_date = current_incomplete_step.get('scheduled_date')
        actual_date = current_incomplete_step.get('actual_date')
        completed_checkbox = current_incomplete_step.get('completed_checkbox')
        has_not_required = current_incomplete_step.get('has_not_required')

        # ステップタイプごとに適切なアクションを決定
        if step_type == 'estimate':
            # 見積書：「見積不要」か「発行日」
            if has_not_required:
                next_action = f"{step_name}：完了"
            else:
                next_action = f"{step_name}：発行日を入力してください"
        elif step_type == 'contract':
            # 契約：契約日を入力
            next_action = f"{step_name}：契約日を入力してください"
        elif step_type == 'work_start' or step_type == 'work_end':
            # 着工・完工：日付＋完了チェックボックス
            if actual_date and not completed_checkbox:
                next_action = f"{step_name}：完了チェックボックスをチェックしてください"
            else:
                next_action = f"{step_name}：日付を入力してください"
        elif step_type == 'invoice':
            # 請求書：完了チェックボックスのみ
            next_action = f"{step_name}：完了チェックボックスをチェックしてください"
        elif step_type == 'complex':
            # 複合ステップ（着手、現調、着工、完工）：予定日→自動完了（予定日ベース）
            # 予定日が過去かチェック
            is_scheduled_past = False
            if scheduled_date:
                try:
                    from datetime import datetime, date
                    scheduled_date_obj = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                    is_scheduled_past = scheduled_date_obj < date.today()
                except:
                    pass

            if completed_checkbox or is_scheduled_past:
                next_action = f"{step_name}：完了"
            elif scheduled_date:
                # 予定日が未来の場合は待機中
                next_action = f"{step_name}：予定日待ち（{scheduled_date}）"
            else:
                next_action = f"{step_name}：予定日を入力してください"
        elif step_type == 'dynamic':
            # 動的ステップ：completedチェックボックスまたは日付
            if completed_checkbox:
                next_action = f"{step_name}：完了"
            elif actual_date:
                next_action = f"{step_name}：完了チェックボックスをチェックしてください"
            else:
                next_action = f"{step_name}：日付を入力してください"
        else:
            # その他
            next_action = f"{step_name}：入力してください"

        # NEXTステップを設定（next_incomplete_stepについても同じロジックでアクションを判定）
        if next_incomplete_step:
            next_step_name = next_incomplete_step.get('name', '')
            next_step_type = next_incomplete_step.get('step_type')
            next_step_key = next_incomplete_step.get('key')
            next_scheduled_date = next_incomplete_step.get('scheduled_date')
            next_actual_date = next_incomplete_step.get('actual_date')
            next_completed_checkbox = next_incomplete_step.get('completed_checkbox')
            next_has_not_required = next_incomplete_step.get('has_not_required')

            # Next Stepのアクションを詳細に判定
            if next_step_type == 'estimate':
                if next_has_not_required:
                    next_step = f"{next_step_name}：完了"
                else:
                    next_step = f"{next_step_name}：発行日を入力してください"
            elif next_step_type == 'contract':
                next_step = f"{next_step_name}：契約日を入力してください"
            elif next_step_type == 'work_start' or next_step_type == 'work_end':
                if next_actual_date and not next_completed_checkbox:
                    next_step = f"{next_step_name}：完了チェックボックスをチェックしてください"
                else:
                    next_step = f"{next_step_name}：日付を入力してください"
            elif next_step_type == 'invoice':
                next_step = f"{next_step_name}：完了チェックボックスをチェックしてください"
            elif next_step_type == 'complex':
                # 複合ステップ：予定日→自動完了（予定日ベース）
                # 予定日が過去かチェック
                is_next_scheduled_past = False
                if next_scheduled_date:
                    try:
                        from datetime import datetime, date
                        next_scheduled_date_obj = datetime.strptime(next_scheduled_date, '%Y-%m-%d').date()
                        is_next_scheduled_past = next_scheduled_date_obj < date.today()
                    except:
                        pass

                if next_completed_checkbox or is_next_scheduled_past:
                    next_step = f"{next_step_name}：完了"
                elif next_scheduled_date:
                    # 予定日が未来の場合は待機中
                    next_step = f"{next_step_name}：予定日待ち（{next_scheduled_date}）"
                else:
                    next_step = f"{next_step_name}：予定日を入力してください"
            elif next_step_type == 'dynamic':
                if next_completed_checkbox:
                    next_step = f"{next_step_name}：完了"
                elif next_actual_date:
                    next_step = f"{next_step_name}：完了チェックボックスをチェックしてください"
                else:
                    next_step = f"{next_step_name}：日付を入力してください"
            else:
                next_step = f"{next_step_name}：入力してください"
        else:
            next_step = '完了'

        return {
            'next_action': next_action,
            'next_step': next_step
        }

    def get_current_project_stage(self):
        """現在のプロジェクト段階を返す

        DEPRECATED: This method returns cached values from current_stage field.
        Use calculate_current_stage() for dynamic calculation from ProjectProgressStep.

        カラーコード統一ルール:
        - verified (濃い緑): 完了チェックボックスON
        - success (緑): 実施日 OR 予定日が入力されている
        - warning (黄色): 予定日のみ入力されている（着工日待ちの場合）
        - secondary (グレー): 何も入力されていない
        """
        # NGステータスの場合は特別扱い
        if self.project_status == 'NG':
            return {
                'stage': 'NG',
                'color': 'secondary'
            }

        return {
            'stage': self.current_stage,
            'color': self.current_stage_color
        }

    def calculate_current_stage(self):
        """
        現在のプロジェクト段階を動的に計算（SSOT: Server-Side Truth）

        ProjectProgressStepから動的に進捗を計算し、JavaScriptに依存しない。
        これが唯一の真実の源（Single Source of Truth）となる。

        Returns:
            dict: {'stage': str, 'color': str}

        カラーコード:
        - 'verified' (濃い緑): 完了チェックボックスON
        - 'success' (緑): 実施日があるまたは予定日が過去
        - 'warning' (黄色): 予定日が未来（待機中）
        - 'secondary' (グレー): 未開始
        """
        from datetime import datetime

        # NGステータスの場合は特別扱い
        if self.project_status == 'NG':
            return {'stage': 'NG', 'color': 'secondary'}

        today = datetime.now().date()

        # Priority 1: 完工日チェック
        completion_step = self._get_step_by_key('completion')
        if completion_step:
            if completion_step.is_completed:
                return {'stage': '完工', 'color': 'verified'}
            if completion_step.value and completion_step.value.get('actual_date'):
                return {'stage': '完工', 'color': 'success'}

        # Priority 2: 着工日チェック
        construction_step = self._get_step_by_key('construction_start')
        if construction_step:
            scheduled_date_str = construction_step.value.get('scheduled_date') if construction_step.value else None

            if construction_step.is_completed:
                return {'stage': '工事中', 'color': 'verified'}
            if construction_step.value and construction_step.value.get('actual_date'):
                return {'stage': '工事中', 'color': 'success'}
            if scheduled_date_str:
                try:
                    scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
                    if scheduled_date < today:
                        return {'stage': '工事中の予定', 'color': 'success'}
                    else:
                        return {'stage': '着工日待ち', 'color': 'warning'}
                except (ValueError, TypeError):
                    pass

        # Priority 3: 見積もりチェック
        estimate_step = self._get_step_by_key('estimate')
        if estimate_step and estimate_step.value and estimate_step.value.get('scheduled_date'):
            return {'stage': '見積もり審査中', 'color': 'warning'}

        # Priority 4: 現調チェック
        survey_step = self._get_step_by_key('survey')
        if survey_step:
            scheduled_date_str = survey_step.value.get('scheduled_date') if survey_step.value else None

            if survey_step.is_completed:
                return {'stage': '現調済み', 'color': 'success'}
            if survey_step.value and survey_step.value.get('actual_date'):
                return {'stage': '現調済み', 'color': 'success'}
            if scheduled_date_str:
                try:
                    scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
                    if scheduled_date < today:
                        return {'stage': '現調済み', 'color': 'success'}
                    else:
                        return {'stage': '現調待ち', 'color': 'warning'}
                except (ValueError, TypeError):
                    pass

        # Priority 5: 立ち会いチェック
        attendance_step = self._get_step_by_key('attendance')
        if attendance_step:
            scheduled_date_str = attendance_step.value.get('scheduled_date') if attendance_step.value else None

            if attendance_step.is_completed:
                return {'stage': '立ち会い済み', 'color': 'success'}
            if attendance_step.value and attendance_step.value.get('actual_date'):
                return {'stage': '立ち会い済み', 'color': 'success'}
            if scheduled_date_str:
                try:
                    scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
                    if scheduled_date < today:
                        return {'stage': '立ち会い済み', 'color': 'success'}
                    else:
                        return {'stage': '立ち会い待ち', 'color': 'warning'}
                except (ValueError, TypeError):
                    pass

        return {'stage': '未開始', 'color': 'secondary'}

    def get_progress_percentage(self):
        """
        進捗率を計算（ProjectProgressStepから動的に計算）

        Returns:
            int: 進捗率（0-100）
        """
        active_steps = self.progress_steps.filter(is_active=True)
        total = active_steps.count()
        if total == 0:
            return 0

        completed = active_steps.filter(is_completed=True).count()
        return round((completed / total) * 100)

    def get_days_until_deadline(self):
        """締切までの日数を返す"""
        if not self.work_end_date:
            return None

        today = timezone.now().date()
        delta = self.work_end_date - today
        return delta.days

    def is_deadline_approaching(self):
        """締切が迫っているかどうか"""
        days = self.get_days_until_deadline()
        return days is not None and 0 <= days <= 7  # 1週間以内

    def get_construction_period(self):
        """工期を計算して返す（SSOT対応版）

        work_start_date と work_end_date プロパティから工期データを取得します。
        これらのプロパティはProjectProgressStepモデルから自動的に読み取ります。

        Returns:
            dict: {
                'days': 日数（整数）,
                'start_date': 開始日,
                'end_date': 終了日,
                'type': 'planned'  # 常に'planned'（将来的に実施日も対応可能）
            }
        """
        # SSOT: work_start_date と work_end_date プロパティから取得
        # これらは @property デコレータで ProjectProgressStep から自動取得
        start_date = self.work_start_date  # construction_start ステップの scheduled_date
        end_date = self.work_end_date      # completion ステップの scheduled_date

        # 両方の日付がある場合のみ工期を計算
        if start_date and end_date:
            delta = end_date - start_date
            return {
                'days': delta.days,
                'start_date': start_date,
                'end_date': end_date,
                'type': 'planned'
            }

        # どちらか一方しかない場合
        return {
            'days': None,
            'start_date': None,
            'end_date': None,
            'type': None
        }

    def get_subcontract_status(self):
        """発注連携状況を返す"""
        from subcontract_management.models import Subcontract

        subcontract_count = Subcontract.objects.filter(project=self).count()

        if subcontract_count == 0:
            return {
                'status': '未連携',
                'count': 0,
                'color': 'secondary',
                'icon': 'fa-times-circle'
            }
        else:
            return {
                'status': '連携済み',
                'count': subcontract_count,
                'color': 'success',
                'icon': 'fa-check-circle'
            }

    def get_comment_count(self):
        """コメント数を取得"""
        return self.comments.count()

    def get_grouped_subcontracts(self):
        """下請を業者・支払日でグループ化して合計金額を返す

        同じ業者・同じ支払日の下請を1つにまとめて表示するため
        """
        from collections import defaultdict
        from subcontract_management.models import Subcontract

        subcontracts = Subcontract.objects.filter(project=self).select_related('contractor', 'internal_worker')
        grouped = defaultdict(lambda: {
            'contractor': None,
            'internal_worker': None,
            'payment_due_date': None,
            'total_amount': 0,
            'count': 0
        })

        for sub in subcontracts:
            # グループキー: contractor_id or internal_worker_id + payment_due_date
            if sub.contractor:
                key = f"contractor_{sub.contractor.id}_{sub.payment_due_date}"
                if not grouped[key]['contractor']:
                    grouped[key]['contractor'] = sub.contractor
            elif sub.internal_worker:
                key = f"internal_{sub.internal_worker.id}_{sub.payment_due_date}"
                if not grouped[key]['internal_worker']:
                    grouped[key]['internal_worker'] = sub.internal_worker
            else:
                continue

            grouped[key]['payment_due_date'] = sub.payment_due_date
            amount = sub.billed_amount or sub.contract_amount or 0
            grouped[key]['total_amount'] += amount
            grouped[key]['count'] += 1

        return list(grouped.values())

    def get_material_status(self):
        """資材連携状況を返す"""
        material_count = self.material_orders.count()

        if material_count == 0:
            return {
                'status': '未連携',
                'count': 0,
                'color': 'secondary',
                'icon': 'fa-times-circle'
            }
        else:
            # 完了していない発注があるかチェック
            pending_count = self.material_orders.exclude(status='completed').count()
            if pending_count > 0:
                return {
                    'status': f'連携済み({pending_count}件進行中)',
                    'count': material_count,
                    'color': 'warning',
                    'icon': 'fa-clock'
                }
            else:
                return {
                    'status': '完了',
                    'count': material_count,
                    'color': 'success',
                    'icon': 'fa-check-circle'
                }

    def get_additional_items_summary(self):
        """追加項目の概要を返す"""
        if not self.additional_items:
            return {
                'has_items': False,
                'dynamic_steps_count': 0,
                'summary': '標準設定'
            }

        dynamic_steps = self.additional_items.get('dynamic_steps', {})
        step_order = self.additional_items.get('step_order', [])

        # 実際に追加された動的ステップをカウント（標準以外のステップ）
        standard_steps = {'estimate', 'contract', 'work_start', 'work_end', 'invoice'}
        custom_steps_in_order = [step for step in step_order if step.get('step') not in standard_steps]

        # dynamic_stepsのsite_surveyフィールドは、step_orderのsite_surveyステップの詳細設定
        # そのため、重複カウントしないようにする
        # step_orderにsite_surveyがある場合は、dynamic_stepsのsite_survey関連はカウントしない
        has_site_survey_in_order = any(s.get('step') == 'site_survey' for s in step_order)

        if has_site_survey_in_order:
            # step_orderに現場調査がある場合、dynamic_stepsからは除外
            custom_dynamic_steps = 0
        else:
            # step_orderに現場調査がない場合のみ、dynamic_stepsからカウント
            custom_dynamic_steps = len([k for k in dynamic_steps.keys() if 'site_survey' in k])
            # site_survey_scheduledとsite_survey_actualは同じステップの2つのフィールドなので1としてカウント
            if custom_dynamic_steps > 0:
                custom_dynamic_steps = 1

        total_custom_items = len(custom_steps_in_order)

        if total_custom_items == 0:
            return {
                'has_items': False,
                'dynamic_steps_count': 0,
                'summary': '標準設定'
            }

        summary_parts = []
        if custom_dynamic_steps > 0:
            summary_parts.append(f'追加ステップ: {custom_dynamic_steps}件')
        if len(custom_steps_in_order) > 0:
            summary_parts.append(f'カスタム順序: {len(custom_steps_in_order)}件')

        summary = ', '.join(summary_parts) if summary_parts else 'カスタム設定'

        return {
            'has_items': True,
            'dynamic_steps_count': total_custom_items,
            'custom_fields_count': len(custom_steps_in_order),
            'summary': summary
        }

    def get_revenue_breakdown(self):
        """売上・原価・利益の内訳を返す

        案件詳細画面のfinancial_info計算ロジックと完全に一致させています。
        """
        # Subcontractモデルをインポート（循環インポート回避のため、メソッド内でインポート）
        try:
            from subcontract_management.models import Subcontract
            subcontracts = Subcontract.objects.filter(project=self)

            # 実際の原価を計算（外注費 + 材料費 + 追加費用）
            # 被請求額がある場合はそれを使用、なければ契約金額を使用（案件詳細と同じロジック）
            total_subcontract_cost = sum((s.billed_amount if s.billed_amount else s.contract_amount) or 0 for s in subcontracts)
            total_material_cost = sum(s.total_material_cost or 0 for s in subcontracts)

            # 追加費用合計（dynamic_cost_items から計算）
            total_additional_cost = Decimal('0')
            for s in subcontracts:
                if s.dynamic_cost_items:
                    for item in s.dynamic_cost_items:
                        if 'cost' in item:
                            total_additional_cost += Decimal(str(item['cost']))

            # MaterialOrderの資材発注合計を追加
            material_order_total = sum(m.total_amount or 0 for m in self.material_orders.all())

            cost_of_sales = total_subcontract_cost + total_material_cost + total_additional_cost + material_order_total
        except ImportError:
            # subcontract_managementアプリが利用できない場合はフォールバック
            cost_of_sales = Decimal('0')

        # 売上 = 請求額
        revenue = self.billing_amount or Decimal('0')

        # 売上総利益 = 売上 - 売上原価
        gross_profit = revenue - cost_of_sales

        # 利益率
        profit_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0')

        return {
            'revenue': revenue,           # 売上
            'cost_of_sales': cost_of_sales,  # 売上原価（外注費＋材料費）
            'gross_profit': gross_profit,    # 売上総利益
            'profit_margin': profit_margin   # 利益率
        }

    def get_survey_status_display_with_color(self):
        """現地調査ステータスの表示名と色を返す

        Note: Uses survey_status_computed which is calculated from ProjectProgressStep (SSOT)
        """
        status_info = {
            'not_required': {'display': '不要', 'color': 'secondary'},
            'required': {'display': '必要', 'color': 'warning'},
            'scheduled': {'display': '予定済み', 'color': 'info'},
            'in_progress': {'display': '調査中', 'color': 'primary'},
            'completed': {'display': '完了', 'color': 'success'},
        }
        return status_info.get(self.survey_status_computed, {'display': '不明', 'color': 'secondary'})

    def get_latest_survey(self):
        """最新の現地調査を取得"""
        try:
            #from surveys.models import Survey
            return Survey.objects.filter(project=self).order_by('-scheduled_date', '-created_at').first()
        except ImportError:
            return None

    def get_survey_summary(self):
        """現地調査のサマリー情報を取得"""
        try:
            #from surveys.models import Survey
            surveys = Survey.objects.filter(project=self)

            if not surveys.exists():
                return None

            total_count = surveys.count()
            completed_count = surveys.filter(status='completed').count()
            in_progress_count = surveys.filter(status='in_progress').count()
            scheduled_count = surveys.filter(status='scheduled').count()

            # 次回予定の調査
            next_survey = surveys.filter(
                status__in=['scheduled', 'in_progress'],
                scheduled_date__gte=timezone.now().date()
            ).order_by('scheduled_date', 'scheduled_start_time').first()

            return {
                'total_count': total_count,
                'completed_count': completed_count,
                'in_progress_count': in_progress_count,
                'scheduled_count': scheduled_count,
                'next_survey': next_survey,
                'has_surveys': total_count > 0
            }
        except ImportError:
            return None

    # ==================== Phase 1: キャッシュフロー管理メソッド ====================

    def get_accrual_revenue(self):
        """発生主義売上を取得（完工ベース）"""
        if self.project_status == '完工' and self.completion_date:
            return self.billing_amount or Decimal('0')
        return Decimal('0')

    def get_cash_revenue(self):
        """現金主義売上を取得（入金ベース）"""
        if self.payment_received_date and self.payment_received_amount:
            return self.payment_received_amount
        elif self.payment_received_date:
            return self.billing_amount or Decimal('0')
        return Decimal('0')

    def get_accrual_expenses(self):
        """発生主義支出を取得（発注ベース）"""
        try:
            from subcontract_management.models import Subcontract
            subcontracts = Subcontract.objects.filter(project=self)
            total = sum(sc.contract_amount or Decimal('0') for sc in subcontracts)
            return total
        except ImportError:
            return Decimal('0')

    def get_cash_expenses(self):
        """現金主義支出を取得（支払ベース）"""
        try:
            from subcontract_management.models import Subcontract
            subcontracts = Subcontract.objects.filter(
                project=self,
                payment_date__isnull=False
            )
            total = sum(sc.contract_amount or Decimal('0') for sc in subcontracts)
            return total
        except ImportError:
            return Decimal('0')

    def get_revenue_status(self):
        """売上の状況を返す（発生 vs 入金）"""
        accrual = self.get_accrual_revenue()
        cash = self.get_cash_revenue()

        return {
            'accrual': accrual,
            'cash': cash,
            'receivable': accrual - cash,  # 売掛金
            'is_collected': cash >= accrual,  # 入金完了フラグ
            'collection_rate': (cash / accrual * 100) if accrual > 0 else Decimal('0')
        }

    def get_expense_status(self):
        """支出の状況を返す（発生 vs 出金）"""
        accrual = self.get_accrual_expenses()
        cash = self.get_cash_expenses()

        return {
            'accrual': accrual,
            'cash': cash,
            'payable': accrual - cash,  # 買掛金
            'is_paid': cash >= accrual,  # 支払完了フラグ
            'payment_rate': (cash / accrual * 100) if accrual > 0 else Decimal('0')
        }

    def get_cash_flow_summary(self):
        """キャッシュフロー概要を返す"""
        revenue_status = self.get_revenue_status()
        expense_status = self.get_expense_status()

        return {
            'revenue': revenue_status,
            'expense': expense_status,
            'net_accrual': revenue_status['accrual'] - expense_status['accrual'],
            'net_cash': revenue_status['cash'] - expense_status['cash'],
            'working_capital': revenue_status['receivable'] - expense_status['payable']
        }

    # ============================================================================
    # Property Adapters for SSOT Architecture (Single Source of Truth)
    # ============================================================================
    # These properties provide backward compatibility by dynamically reading
    # values from ProjectProgressStep instead of deprecated database fields.
    # This ensures data consistency and eliminates synchronization issues.
    # ============================================================================

    def _get_step_by_key(self, step_key):
        """
        Helper: 指定されたステップキーに対応するProjectProgressStepを取得

        Args:
            step_key: ステップキー（例: 'attendance', 'survey', 'estimate'）

        Returns:
            ProjectProgressStep or None
        """
        from order_management.services.progress_step_service import get_step
        return get_step(self, step_key)

    def _get_step_date_value(self, step_key, date_type='scheduled_date'):
        """
        Helper: ステップの日付を取得（date objectとして返す）

        Args:
            step_key: ステップキー
            date_type: 'scheduled_date' or 'actual_date'

        Returns:
            date object or None
        """
        step = self._get_step_by_key(step_key)
        if step and step.value and isinstance(step.value, dict):
            date_str = step.value.get(date_type)
            if date_str:
                from datetime import datetime
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    return None
        return None

    # ===== Computed Properties (Read from ProjectProgressStep) =====

    @property
    def witness_date(self):
        """立ち会い日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('attendance', 'scheduled_date')

    @property
    def witness_actual_date(self):
        """立ち会い実施日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('attendance', 'actual_date')

    @property
    def witness_assignees(self):
        """立ち会い担当者（ProjectProgressStepから計算）"""
        from order_management.services.progress_step_service import get_step_assignees
        return get_step_assignees(self, 'attendance')

    @property
    def witness_status(self):
        """立ち会いステータス（ProjectProgressStepから計算）"""
        step = self._get_step_by_key('attendance')
        if not step:
            return 'waiting'
        if step.is_completed:
            return 'completed'
        if step.value and step.value.get('scheduled_date'):
            return 'waiting'
        return 'waiting'

    @property
    def survey_date(self):
        """現調日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('survey', 'scheduled_date')

    @property
    def survey_actual_date(self):
        """現調実施日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('survey', 'actual_date')

    @property
    def survey_assignees(self):
        """現調担当者（ProjectProgressStepから計算）"""
        from order_management.services.progress_step_service import get_step_assignees
        return get_step_assignees(self, 'survey')

    @property
    def survey_status_computed(self):
        """現地調査ステータス（ProjectProgressStepから計算）

        Note: This is a computed property based on ProjectProgressStep.
        The actual survey_status field (line 134) is still used for backward compatibility.
        """
        step = self._get_step_by_key('survey')
        if not step:
            return 'not_required'
        if step.is_completed:
            return 'completed'
        if step.value and step.value.get('actual_date'):
            return 'in_progress'
        if step.value and step.value.get('scheduled_date'):
            return 'scheduled'
        return 'required'

    @property
    def estimate_issued_date(self):
        """見積書発行日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('estimate', 'scheduled_date')

    @property
    def estimate_actual_date(self):
        """見積書実施日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('estimate', 'actual_date')

    @property
    def estimate_status_computed(self):
        """見積もりステータス（ProjectProgressStepから計算）"""
        step = self._get_step_by_key('estimate')
        if not step:
            return 'not_issued'
        if step.is_completed:
            return 'approved'
        if step.value and step.value.get('actual_date'):
            return 'under_review'
        if step.value and step.value.get('scheduled_date'):
            return 'issued'
        return 'not_issued'

    @property
    def work_start_date(self):
        """着工日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('construction_start', 'scheduled_date')

    @property
    def work_start_actual_date(self):
        """着工実施日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('construction_start', 'actual_date')

    @property
    def work_start_completed(self):
        """着工完了フラグ（ProjectProgressStepから計算）"""
        step = self._get_step_by_key('construction_start')
        return step.is_completed if step else False

    @property
    def construction_assignees_computed(self):
        """施工担当者（ProjectProgressStepから計算）"""
        from order_management.services.progress_step_service import get_step_assignees
        return get_step_assignees(self, 'construction_start')

    @property
    def construction_status_computed(self):
        """工事ステータス（ProjectProgressStepから計算）"""
        step = self._get_step_by_key('construction_start')
        if not step:
            return 'waiting'
        if step.is_completed:
            return 'completed'
        if step.value and step.value.get('actual_date'):
            return 'in_progress'
        if step.value and step.value.get('scheduled_date'):
            return 'waiting'
        return 'waiting'

    @property
    def work_end_date(self):
        """完工日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('completion', 'scheduled_date')

    @property
    def work_end_actual_date(self):
        """完工実施日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('completion', 'actual_date')

    @property
    def work_end_completed(self):
        """完工完了フラグ（ProjectProgressStepから計算）"""
        step = self._get_step_by_key('completion')
        return step.is_completed if step else False

    @property
    def contract_date_computed(self):
        """契約日（ProjectProgressStepから計算）"""
        return self._get_step_date_value('contract', 'scheduled_date')


class ProgressStepTemplate(models.Model):
    """進捗ステップテンプレート"""
    name = models.CharField(max_length=100, verbose_name='ステップ名')
    icon = models.CharField(max_length=50, default='fas fa-circle', verbose_name='アイコン')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_default = models.BooleanField(default=False, verbose_name='デフォルト表示')
    is_system = models.BooleanField(default=False, verbose_name='システム項目')
    field_type = models.CharField(
        max_length=20,
        choices=[
            ('date', '日付'),
            ('checkbox', 'チェックボックス'),
            ('select', '選択肢'),
            ('text', 'テキスト')
        ],
        default='date',
        verbose_name='フィールドタイプ'
    )
    field_options = models.JSONField(blank=True, null=True, verbose_name='フィールドオプション')

    class Meta:
        verbose_name = '進捗ステップテンプレート'
        verbose_name_plural = '進捗ステップテンプレート一覧'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ProjectProgressStep(models.Model):
    """プロジェクト進捗ステップ"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_steps')
    template = models.ForeignKey(ProgressStepTemplate, on_delete=models.CASCADE)
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='アクティブ')
    is_completed = models.BooleanField(default=False, verbose_name='完了')
    value = models.JSONField(blank=True, null=True, verbose_name='値')
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')

    class Meta:
        verbose_name = 'プロジェクト進捗ステップ'
        verbose_name_plural = 'プロジェクト進捗ステップ一覧'
        ordering = ['order', 'template__order']
        unique_together = ['project', 'template']

    def __str__(self):
        return f"{self.project.management_no} - {self.template.name}"


class Contractor(models.Model):
    """業者マスター"""
    name = models.CharField(max_length=200, verbose_name='業者名')
    address = models.TextField(blank=True, verbose_name='住所')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話番号')
    email = models.EmailField(blank=True, verbose_name='メールアドレス')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='担当者名')
    specialties = models.TextField(blank=True, verbose_name='専門分野')

    # 業者分類（複数選択対応）
    is_ordering = models.BooleanField(default=False, verbose_name='発注業者')
    is_receiving = models.BooleanField(default=False, verbose_name='受注業者')
    is_supplier = models.BooleanField(default=False, verbose_name='資材屋')
    is_other = models.BooleanField(default=False, verbose_name='その他')
    other_description = models.CharField(max_length=100, blank=True, verbose_name='その他内容')

    is_active = models.BooleanField(default=True, verbose_name='アクティブ')

    # 支払情報
    payment_day = models.IntegerField(
        null=True, blank=True,
        verbose_name='支払日',
        help_text='支払月の何日に支払うか（1-31）。例：25日払いの場合は25'
    )
    payment_cycle = models.CharField(
        max_length=20,
        choices=[
            ('monthly', '月1回'),
            ('bimonthly', '月2回'),
            ('weekly', '週1回'),
            ('project_end', '案件完了時'),
        ],
        default='monthly',
        verbose_name='支払サイクル'
    )
    closing_day = models.IntegerField(
        null=True, blank=True,
        verbose_name='締め日',
        help_text='月末締めの場合は31、20日締めの場合は20'
    )
    bank_name = models.CharField(max_length=100, blank=True, verbose_name='銀行名')
    branch_name = models.CharField(max_length=100, blank=True, verbose_name='支店名')
    account_type = models.CharField(
        max_length=10,
        choices=[
            ('ordinary', '普通'),
            ('current', '当座'),
        ],
        default='ordinary',
        blank=True,
        verbose_name='口座種別'
    )
    account_number = models.CharField(max_length=20, blank=True, verbose_name='口座番号')
    account_holder = models.CharField(max_length=100, blank=True, verbose_name='口座名義')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '業者'
        verbose_name_plural = '業者一覧'
        ordering = ['-is_ordering', '-is_active', 'name']

    def __str__(self):
        return self.name

    def get_classification_display(self):
        """業者分類の表示用文字列を返す"""
        classifications = []
        if self.is_ordering:
            classifications.append('発注業者')
        if self.is_receiving:
            classifications.append('受注業者')
        if self.is_supplier:
            classifications.append('資材屋')
        if self.is_other and self.other_description:
            classifications.append(f'その他({self.other_description})')
        elif self.is_other:
            classifications.append('その他')

        return ', '.join(classifications) if classifications else '未分類'


class FixedCost(models.Model):
    """固定費管理"""
    COST_TYPE_CHOICES = [
        ('business_outsourcing', '業務委託費'),
        ('insurance', '保険'),
        ('legal_fee', '弁護士費用'),
        ('accounting_fee', '税理士費用'),
        ('executive_compensation', '役員報酬'),
        ('rent', '家賃'),
        ('utilities', '光熱費'),
        ('other', 'その他'),
    ]

    name = models.CharField(max_length=100, verbose_name='費目名')
    cost_type = models.CharField(
        max_length=30,
        choices=COST_TYPE_CHOICES,
        verbose_name='費目種別'
    )
    monthly_amount = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name='月額'
    )
    start_date = models.DateField(verbose_name='開始日')
    end_date = models.DateField(null=True, blank=True, verbose_name='終了日')
    is_active = models.BooleanField(default=True, verbose_name='アクティブ')
    notes = models.TextField(blank=True, verbose_name='備考')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '固定費'
        verbose_name_plural = '固定費一覧'
        ordering = ['cost_type', 'name']

    def __str__(self):
        return f"{self.name} (¥{self.monthly_amount:,})"

    def is_active_in_month(self, year, month):
        """指定月にアクティブかどうか"""
        from datetime import date
        target_date = date(year, month, 1)

        if not self.is_active:
            return False

        if self.start_date > target_date:
            return False

        if self.end_date and self.end_date < target_date:
            return False

        return True


class VariableCost(models.Model):
    """変動費管理（販管費等）"""
    COST_TYPE_CHOICES = [
        ('sales_expense', '営業費'),
        ('marketing_expense', 'マーケティング費'),
        ('admin_expense', '管理費'),
        ('travel_expense', '交通費'),
        ('entertainment_expense', '接待費'),
        ('other', 'その他'),
    ]

    name = models.CharField(max_length=100, verbose_name='費目名')
    cost_type = models.CharField(
        max_length=30,
        choices=COST_TYPE_CHOICES,
        verbose_name='費目種別'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name='金額'
    )
    incurred_date = models.DateField(verbose_name='発生日')
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='関連案件'
    )
    notes = models.TextField(blank=True, verbose_name='備考')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '変動費'
        verbose_name_plural = '変動費一覧'
        ordering = ['-incurred_date']

    def __str__(self):
        return f"{self.name} (¥{self.amount:,}) - {self.incurred_date}"


class MaterialOrder(models.Model):
    """資材発注管理"""
    ORDER_STATUS_CHOICES = [
        ('draft', '下書き'),
        ('ordered', '発注済み'),
        ('delivered', '納品済み'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='material_orders',
        verbose_name='案件'
    )
    contractor = models.ForeignKey(
        'subcontract_management.Contractor',
        on_delete=models.CASCADE,
        verbose_name='資材業者'
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='発注番号'
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='draft',
        verbose_name='ステータス'
    )
    order_date = models.DateField(verbose_name='発注日')
    delivery_date = models.DateField(
        null=True, blank=True,
        verbose_name='納期'
    )
    actual_delivery_date = models.DateField(
        null=True, blank=True,
        verbose_name='実際の納品日'
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=0,
        default=0,
        verbose_name='総額'
    )
    notes = models.TextField(blank=True, verbose_name='備考')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '資材発注'
        verbose_name_plural = '資材発注一覧'
        ordering = ['-order_date', '-created_at']

    def __str__(self):
        return f"{self.order_number} - {self.contractor.name}"

    def generate_order_number(self):
        """発注番号自動採番"""
        current_year = timezone.now().year
        year_suffix = str(current_year)[-2:]

        # 今年の最新番号を取得
        latest = MaterialOrder.objects.filter(
            order_number__startswith=f'M{year_suffix}'
        ).order_by('-order_number').first()

        if latest:
            latest_num = int(latest.order_number[3:])
            new_num = latest_num + 1
        else:
            new_num = 1

        return f'M{year_suffix}{new_num:04d}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def get_status_color(self):
        """ステータスに応じた色を返す"""
        color_map = {
            'draft': 'secondary',
            'ordered': 'warning',
            'delivered': 'info',
            'completed': 'success',
            'cancelled': 'danger',
        }
        return color_map.get(self.status, 'secondary')

    def get_status_color_hex(self):
        """ステータスに応じた背景色（Hex）を返す"""
        color_map = {
            'draft': '#6c757d',
            'ordered': '#f59e0b',
            'delivered': '#3b82f6',
            'completed': '#10b981',
            'cancelled': '#ef4444',
        }
        return color_map.get(self.status, '#6c757d')


class MaterialOrderItem(models.Model):
    """資材発注項目"""
    order = models.ForeignKey(
        MaterialOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='発注'
    )
    material_name = models.CharField(max_length=200, verbose_name='資材名')
    specification = models.TextField(blank=True, verbose_name='仕様・規格')
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='数量'
    )
    unit = models.CharField(max_length=20, verbose_name='単位')
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='単価'
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='小計'
    )
    notes = models.TextField(blank=True, verbose_name='備考')

    class Meta:
        verbose_name = '資材発注項目'
        verbose_name_plural = '資材発注項目一覧'

    def __str__(self):
        return f"{self.material_name} - {self.quantity}{self.unit}"

    def save(self, *args, **kwargs):
        # 小計の自動計算
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # 発注の総額を更新
        self.order.total_amount = sum(
            item.total_price for item in self.order.items.all()
        )
        self.order.save()


class Invoice(models.Model):
    """請求書モデル"""
    STATUS_CHOICES = [
        ('draft', '下書き'),
        ('issued', '発行済み'),
        ('sent', '送付済み'),
        ('paid', '入金済み'),
        ('overdue', '延滞'),
        ('cancelled', 'キャンセル'),
    ]

    TAX_TYPE_CHOICES = [
        ('included', '税込'),
        ('excluded', '税抜'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, verbose_name='請求書番号')
    client_name = models.CharField(max_length=200, verbose_name='受注先名')
    client_address = models.TextField(blank=True, verbose_name='受注先住所')

    # 請求書情報
    issue_date = models.DateField(verbose_name='発行日')
    due_date = models.DateField(verbose_name='支払期限')
    billing_period_start = models.DateField(verbose_name='請求期間開始')
    billing_period_end = models.DateField(verbose_name='請求期間終了')

    # 金額情報
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='小計（税抜）')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name='消費税率')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='消費税額')
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='合計金額')

    # ステータス
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='ステータス')

    # 備考
    notes = models.TextField(blank=True, verbose_name='備考')

    # システム情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    created_by = models.CharField(max_length=100, blank=True, verbose_name='作成者')

    class Meta:
        verbose_name = '請求書'
        verbose_name_plural = '請求書一覧'
        ordering = ['-issue_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"

    def generate_invoice_number(self):
        """請求書番号自動採番"""
        current_year = timezone.now().year
        current_month = timezone.now().month
        year_month = f'{current_year}{current_month:02d}'

        # 今月の最新番号を取得
        latest = Invoice.objects.filter(
            invoice_number__startswith=f'INV-{year_month}'
        ).order_by('-invoice_number').first()

        if latest:
            # 最新番号から連番部分を取得してインクリメント
            latest_num = int(latest.invoice_number.split('-')[-1])
            new_num = latest_num + 1
        else:
            new_num = 1

        return f'INV-{year_month}-{new_num:03d}'

    def calculate_tax_amount(self):
        """消費税額を計算"""
        return int(self.subtotal * (self.tax_rate / 100))

    def calculate_total_amount(self):
        """合計金額を計算"""
        return self.subtotal + self.tax_amount

    def save(self, *args, **kwargs):
        # 請求書番号自動採番
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()

        # 税額・合計額自動計算
        self.tax_amount = self.calculate_tax_amount()
        self.total_amount = self.calculate_total_amount()

        super().save(*args, **kwargs)

    def get_status_color(self):
        """ステータスに応じた色を返す"""
        color_map = {
            'draft': 'secondary',
            'issued': 'primary',
            'sent': 'info',
            'paid': 'success',
            'overdue': 'danger',
            'cancelled': 'warning',
        }
        return color_map.get(self.status, 'secondary')


class InvoiceItem(models.Model):
    """請求書明細"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items', verbose_name='請求書')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='案件')

    # 明細情報
    description = models.CharField(max_length=500, verbose_name='項目名')
    work_period_start = models.DateField(null=True, blank=True, verbose_name='作業期間開始')
    work_period_end = models.DateField(null=True, blank=True, verbose_name='作業期間終了')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name='数量')
    unit = models.CharField(max_length=20, default='式', verbose_name='単位')
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='単価')
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='金額')

    # 表示順
    order = models.IntegerField(default=0, verbose_name='表示順')

    class Meta:
        verbose_name = '請求書明細'
        verbose_name_plural = '請求書明細一覧'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"

    def save(self, *args, **kwargs):
        # 金額自動計算
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # 請求書の小計を更新
        self.invoice.subtotal = sum(item.amount for item in self.invoice.items.all())
        self.invoice.save()


class CashFlowTransaction(models.Model):
    """キャッシュフロー取引モデル - Phase 1"""
    TRANSACTION_TYPE_CHOICES = [
        ('revenue_accrual', '売上（発生）'),      # 完工ベース
        ('revenue_cash', '売上（入金）'),         # 入金ベース
        ('expense_accrual', '支出（発生）'),      # 発注ベース
        ('expense_cash', '支出（出金）'),         # 支払ベース
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='cash_transactions',
        verbose_name='関連案件'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='取引種別'
    )
    transaction_date = models.DateField(verbose_name='取引日')
    amount = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name='金額'
    )
    description = models.CharField(max_length=200, blank=True, verbose_name='説明')
    is_planned = models.BooleanField(default=False, verbose_name='予定/実績')

    # 外注先への支払の場合
    related_subcontract = models.ForeignKey(
        'subcontract_management.Subcontract',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='関連外注'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'キャッシュフロー取引'
        verbose_name_plural = 'キャッシュフロー取引一覧'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_date', 'transaction_type']),
            models.Index(fields=['project', 'transaction_type']),
        ]

    def __str__(self):
        status = '予定' if self.is_planned else '実績'
        return f"{self.project.management_no} - {self.get_transaction_type_display()} - {status} - ¥{self.amount:,}"

    def get_transaction_category(self):
        """取引カテゴリを返す（収入/支出）"""
        if self.transaction_type in ['revenue_accrual', 'revenue_cash']:
            return 'revenue'
        else:
            return 'expense'

    def get_accounting_basis(self):
        """会計基準を返す（発生主義/現金主義）"""
        if self.transaction_type in ['revenue_accrual', 'expense_accrual']:
            return 'accrual'
        else:
            return 'cash'


class ForecastScenario(models.Model):
    """売上予測シナリオ - Phase 2"""

    SCENARIO_TYPE_CHOICES = [
        ('worst', '最悪シナリオ'),
        ('normal', '通常シナリオ'),
        ('best', '最良シナリオ'),
        ('custom', 'カスタム'),
    ]

    # 基本情報
    name = models.CharField(max_length=100, verbose_name='シナリオ名')
    description = models.TextField(blank=True, verbose_name='説明')
    scenario_type = models.CharField(
        max_length=20,
        choices=SCENARIO_TYPE_CHOICES,
        default='custom',
        verbose_name='シナリオタイプ'
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='作成者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    # 成約率設定（%で保存、0-100）
    conversion_rate_neta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('30.00'),
        verbose_name='ネタ成約率（%）',
        help_text='ネタ→完工への成約確率'
    )
    conversion_rate_waiting = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('80.00'),
        verbose_name='施工日待ち成約率（%）',
        help_text='施工日待ち→完工への成約確率'
    )

    # コスト設定
    cost_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('75.00'),
        verbose_name='原価率（%）',
        help_text='売上に対する原価の割合'
    )
    fixed_cost_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='固定費係数',
        help_text='現在の固定費に対する係数（1.0=現状維持）'
    )
    variable_cost_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name='変動費係数',
        help_text='過去平均変動費に対する係数'
    )

    # 予測設定
    forecast_months = models.IntegerField(
        default=12,
        verbose_name='予測月数',
        help_text='1-24ヶ月'
    )
    seasonality_enabled = models.BooleanField(
        default=True,
        verbose_name='季節性考慮',
        help_text='過去の季節性パターンを考慮'
    )

    # 予測結果（JSON格納）
    forecast_results = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='予測結果',
        help_text='計算された予測データ'
    )

    # ステータス
    is_active = models.BooleanField(default=True, verbose_name='アクティブ')
    is_default = models.BooleanField(default=False, verbose_name='デフォルトシナリオ')

    class Meta:
        verbose_name = '売上予測シナリオ'
        verbose_name_plural = '売上予測シナリオ一覧'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scenario_type', 'is_active']),
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_scenario_type_display()})"

    def save(self, *args, **kwargs):
        # デフォルトシナリオは1つのみ
        if self.is_default:
            ForecastScenario.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def get_conversion_rates(self):
        """成約率を辞書で返す"""
        return {
            'ネタ': self.conversion_rate_neta / Decimal('100'),
            '施工日待ち': self.conversion_rate_waiting / Decimal('100'),
        }

    def calculate_forecast(self):
        """予測を計算して forecast_results に保存"""
        from .forecast_utils import generate_full_forecast
        self.forecast_results = generate_full_forecast(self)
        self.save(update_fields=['forecast_results', 'updated_at'])

    def get_summary(self):
        """予測サマリーを返す"""
        if not self.forecast_results:
            return None

        return {
            'total_revenue': self.forecast_results.get('total_revenue', 0),
            'total_profit': self.forecast_results.get('total_profit', 0),
            'profit_margin': self.forecast_results.get('profit_margin', 0),
            'months': len(self.forecast_results.get('monthly_data', []))
        }


# =============================================================================
# Phase 3: 進捗管理・レポート機能
# =============================================================================

class ProjectProgress(models.Model):
    """プロジェクト進捗記録 - Phase 3"""

    STATUS_CHOICES = [
        ('on_track', '順調'),
        ('at_risk', '注意'),
        ('delayed', '遅延'),
        ('completed', '完了'),
    ]

    RISK_LEVEL_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
    ]

    # 基本情報
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name='プロジェクト'
    )
    recorded_date = models.DateField(
        default=timezone.now,
        verbose_name='記録日'
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='記録者'
    )

    # 進捗情報
    progress_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name='進捗率（%）',
        help_text='0-100%'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='on_track',
        verbose_name='ステータス'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    # マイルストーン
    milestone_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='マイルストーン名'
    )
    milestone_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='マイルストーン予定日'
    )
    milestone_completed = models.BooleanField(
        default=False,
        verbose_name='マイルストーン完了'
    )

    # リスク・課題
    has_risk = models.BooleanField(
        default=False,
        verbose_name='リスクあり'
    )
    risk_description = models.TextField(
        blank=True,
        verbose_name='リスク内容'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        blank=True,
        verbose_name='リスクレベル'
    )

    # システム情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'プロジェクト進捗'
        verbose_name_plural = 'プロジェクト進捗'
        ordering = ['-recorded_date', '-created_at']
        indexes = [
            models.Index(fields=['project', '-recorded_date']),
            models.Index(fields=['status']),
            models.Index(fields=['recorded_date']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.recorded_date} ({self.progress_rate}%)"

    def get_schedule_variance_days(self):
        """スケジュール差異（日数）を計算"""
        if not self.project.start_date or not self.project.expected_completion_date:
            return None

        total_days = (self.project.expected_completion_date - self.project.start_date).days
        if total_days <= 0:
            return None

        expected_progress = Decimal('100.00')
        today = timezone.now().date()
        if today < self.project.expected_completion_date:
            elapsed_days = (today - self.project.start_date).days
            expected_progress = (Decimal(str(elapsed_days)) / Decimal(str(total_days))) * Decimal('100.00')

        progress_variance = self.progress_rate - expected_progress
        variance_days = int((progress_variance / Decimal('100.00')) * Decimal(str(total_days)))

        return variance_days

    def is_on_schedule(self):
        """予定通りか判定"""
        variance = self.get_schedule_variance_days()
        if variance is None:
            return True
        return variance >= -7  # 1週間以内の遅れは許容


class Report(models.Model):
    """レポート - Phase 3"""

    REPORT_TYPE_CHOICES = [
        ('monthly', '月次経営レポート'),
        ('project', 'プロジェクト別レポート'),
        ('cashflow', 'キャッシュフローレポート'),
        ('forecast', '予測レポート'),
        ('progress', '進捗レポート'),
    ]

    # 基本情報
    title = models.CharField(
        max_length=200,
        verbose_name='レポートタイトル'
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='レポートタイプ'
    )
    description = models.TextField(
        blank=True,
        verbose_name='説明'
    )

    # 生成情報
    generated_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='生成日時'
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='生成者'
    )

    # 対象期間
    period_start = models.DateField(
        verbose_name='対象期間開始'
    )
    period_end = models.DateField(
        verbose_name='対象期間終了'
    )

    # レポートデータ
    report_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='レポートデータ'
    )

    # PDF保存
    pdf_file = models.FileField(
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='PDFファイル'
    )

    # ステータス
    is_published = models.BooleanField(
        default=False,
        verbose_name='公開済み'
    )

    # システム情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'レポート'
        verbose_name_plural = 'レポート'
        ordering = ['-generated_date']
        indexes = [
            models.Index(fields=['report_type', '-generated_date']),
            models.Index(fields=['period_start', 'period_end']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"

    def generate_pdf(self):
        """PDFを生成"""
        from .pdf_utils import generate_pdf_report
        pdf_path = generate_pdf_report(self.report_data, self.report_type, self.title)
        self.pdf_file.name = pdf_path
        self.save(update_fields=['pdf_file', 'updated_at'])
        return pdf_path


class SeasonalityIndex(models.Model):
    """季節性指数設定 - Phase 3 (季節性詳細調整用)"""

    # 紐付け
    forecast_scenario = models.OneToOneField(
        ForecastScenario,
        on_delete=models.CASCADE,
        related_name='seasonality_index',
        verbose_name='予測シナリオ'
    )

    # 月別指数（1.0 = 平均月）
    january_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='1月指数'
    )
    february_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='2月指数'
    )
    march_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='3月指数'
    )
    april_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='4月指数'
    )
    may_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='5月指数'
    )
    june_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='6月指数'
    )
    july_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='7月指数'
    )
    august_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='8月指数'
    )
    september_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='9月指数'
    )
    october_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='10月指数'
    )
    november_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='11月指数'
    )
    december_index = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('3.00'))],
        verbose_name='12月指数'
    )

    # 自動計算フラグ
    use_auto_calculation = models.BooleanField(
        default=True,
        verbose_name='自動計算を使用',
        help_text='ONの場合は過去データから自動計算、OFFの場合は手動設定値を使用'
    )

    # システム情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '季節性指数'
        verbose_name_plural = '季節性指数'

    def __str__(self):
        return f"{self.forecast_scenario.name} - 季節性指数"

    def get_index_for_month(self, month):
        """指定月の季節性指数を取得"""
        month_fields = {
            1: 'january_index',
            2: 'february_index',
            3: 'march_index',
            4: 'april_index',
            5: 'may_index',
            6: 'june_index',
            7: 'july_index',
            8: 'august_index',
            9: 'september_index',
            10: 'october_index',
            11: 'november_index',
            12: 'december_index',
        }
        field_name = month_fields.get(month)
        if field_name:
            return getattr(self, field_name)
        return Decimal('1.00')

    def set_index_for_month(self, month, value):
        """指定月の季節性指数を設定"""
        month_fields = {
            1: 'january_index',
            2: 'february_index',
            3: 'march_index',
            4: 'april_index',
            5: 'may_index',
            6: 'june_index',
            7: 'july_index',
            8: 'august_index',
            9: 'september_index',
            10: 'october_index',
            11: 'november_index',
            12: 'december_index',
        }
        field_name = month_fields.get(month)
        if field_name:
            setattr(self, field_name, value)

    def calculate_from_historical_data(self):
        """過去データから自動計算"""
        from .forecast_utils import analyze_historical_performance

        historical_data = analyze_historical_performance()
        seasonal_factors = historical_data.get('seasonal_factors', {})

        for month in range(1, 13):
            index = seasonal_factors.get(month, Decimal('1.00'))
            self.set_index_for_month(month, index)

        self.use_auto_calculation = True
        self.save()



class UserProfile(models.Model):
    """ユーザープロファイル - ロール管理とアバター"""

    # 背景色の選択肢
    BACKGROUND_COLOR_CHOICES = [
        ('#007bff', 'ブルー'),
        ('#6c757d', 'グレー'),
        ('#28a745', 'グリーン'),
        ('#dc3545', 'レッド'),
        ('#ffc107', 'イエロー'),
        ('#17a2b8', 'シアン'),
        ('#6f42c1', 'パープル'),
        ('#fd7e14', 'オレンジ'),
        ('#e83e8c', 'ピンク'),
        ('#20c997', 'ティール'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    roles = models.JSONField(default=list, verbose_name="ロール")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='プロフィール画像')
    avatar_background_color = models.CharField(
        max_length=7,
        choices=BACKGROUND_COLOR_CHOICES,
        default='#007bff',
        verbose_name='アバター背景色'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'user_profile'
        verbose_name = "ユーザープロファイル"
        verbose_name_plural = "ユーザープロファイル一覧"

    def __str__(self):
        roles_str = ", ".join(self.roles) if self.roles else "ロールなし"
        return f"{self.user.username} - {roles_str}"

    def has_role(self, role):
        """指定されたロールを持っているかチェック"""
        return role in self.roles

    def add_role(self, role):
        """ロールを追加"""
        if role not in self.roles:
            self.roles.append(role)
            self.save()

    def remove_role(self, role):
        """ロールを削除"""
        if role in self.roles:
            self.roles.remove(role)
            self.save()

    def get_initials(self):
        """ユーザーのイニシャルを取得"""
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name[0]}{self.user.last_name[0]}'.upper()
        elif self.user.first_name:
            return self.user.first_name[:2].upper()
        elif self.user.last_name:
            return self.user.last_name[:2].upper()
        else:
            return self.user.username[:2].upper()

    def get_avatar_data(self):
        """アバター表示用のデータを取得"""
        if self.avatar:
            return {
                'type': 'image',
                'url': self.avatar.url,
            }
        else:
            return {
                'type': 'initials',
                'initials': self.get_initials(),
                'background_color': self.avatar_background_color,
            }

    def get_roles_display(self):
        """ロールの表示名を取得"""
        from .user_roles import UserRole
        role_dict = dict(UserRole.CHOICES)
        return [role_dict.get(role, role) for role in self.roles]


class Comment(models.Model):
    """案件コメント・チャット機能"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments', verbose_name="案件")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name="投稿者")
    content = models.TextField(verbose_name="コメント内容")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name="返信先コメント")
    mentioned_users = models.ManyToManyField(User, related_name='mentioned_in_comments', blank=True, verbose_name="メンションユーザー")
    is_important = models.BooleanField(default=False, verbose_name="重要フラグ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="投稿日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "コメント"
        verbose_name_plural = "コメント一覧"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.site_name} - {self.author.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def extract_mentions(self):
        """コメント内容から@メンションを抽出"""
        import re
        mention_pattern = r'@(\w+)'
        usernames = re.findall(mention_pattern, self.content)
        return User.objects.filter(username__in=usernames)


class CommentAttachment(models.Model):
    """コメント添付ファイル"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='attachments', verbose_name="コメント")
    file = models.FileField(upload_to='comment_attachments/%Y/%m/%d/', verbose_name="ファイル")
    file_name = models.CharField(max_length=255, verbose_name="ファイル名")
    file_size = models.IntegerField(verbose_name="ファイルサイズ（バイト）")
    file_type = models.CharField(max_length=100, verbose_name="ファイルタイプ")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="アップロード日時")

    class Meta:
        verbose_name = "コメント添付ファイル"
        verbose_name_plural = "コメント添付ファイル一覧"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.comment.project.site_name} - {self.file_name}"

    def get_file_size_display(self):
        """ファイルサイズを読みやすい形式で表示"""
        size = self.file_size
        if size is None:
            return "不明"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def is_image(self):
        """画像ファイルかどうか"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        return self.file_type.lower() in image_types or any(ext in self.file_name.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'])

    def is_pdf(self):
        """PDFファイルかどうか"""
        return 'pdf' in self.file_type.lower() or self.file_name.lower().endswith('.pdf')


class CommentReadStatus(models.Model):
    """コメント既読状態管理"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comment_read_statuses', verbose_name="案件")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_read_statuses', verbose_name="ユーザー")
    last_read_at = models.DateTimeField(auto_now=True, verbose_name="最終既読日時")

    class Meta:
        verbose_name = "コメント既読状態"
        verbose_name_plural = "コメント既読状態一覧"
        unique_together = [['project', 'user']]

    def __str__(self):
        return f"{self.project.site_name} - {self.user.username} - {self.last_read_at.strftime('%Y-%m-%d %H:%M')}"


class Notification(models.Model):
    """通知モデル"""
    NOTIFICATION_TYPES = [
        ('mention', 'メンション'),
        ('comment', 'コメント'),
        ('project_update', '案件更新'),
        ('work_completion_overdue', '完工遅延'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="受信者")
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, verbose_name="通知タイプ")
    title = models.CharField(max_length=200, verbose_name="タイトル")
    message = models.TextField(verbose_name="メッセージ")
    link = models.CharField(max_length=500, blank=True, verbose_name="リンク")
    is_read = models.BooleanField(default=False, verbose_name="既読フラグ")
    is_archived = models.BooleanField(default=False, verbose_name="アーカイブ済み")
    related_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="関連コメント")
    related_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="関連案件")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="アーカイブ日時")

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知一覧"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.get_notification_type_display()} - {self.title}"


class ClientCompany(models.Model):
    """元請会社マスター - Phase 8"""
    company_name = models.CharField(max_length=200, unique=True, verbose_name='会社名')
    address = models.TextField(blank=True, verbose_name='住所')
    managed_units = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='管理戸数',
        help_text='元請会社が管理している戸数'
    )

    # 鍵受け渡しデフォルト設定
    default_key_handover_location = models.TextField(blank=True, verbose_name='鍵受け渡し場所（デフォルト）')
    key_handover_notes = models.TextField(blank=True, verbose_name='鍵受け渡し特記事項')

    # 完了報告シートテンプレート
    completion_report_template = models.FileField(
        upload_to='completion_templates/',
        null=True,
        blank=True,
        verbose_name='完了報告シートテンプレート'
    )
    completion_report_notes = models.TextField(blank=True, verbose_name='完了報告特記事項')

    # 支払いサイクル設定
    payment_cycle = models.CharField(
        max_length=20,
        choices=[
            ('monthly', '月1回'),
            ('bimonthly', '月2回'),
            ('weekly', '週1回'),
            ('custom', 'その他'),
        ],
        default='monthly',
        blank=True,
        verbose_name='支払サイクル',
        help_text='案件登録時のデフォルト値として使用されます'
    )
    closing_day = models.IntegerField(
        null=True,
        blank=True,
        default=31,
        verbose_name='締め日',
        help_text='月末締めの場合は31、20日締めの場合は20。デフォルト: 31（月末）'
    )
    payment_day = models.IntegerField(
        null=True,
        blank=True,
        default=31,
        verbose_name='支払日',
        help_text='支払月の何日に支払うか（1-31）。例：25日払いの場合は25。デフォルト: 31（月末）'
    )
    payment_offset_months = models.IntegerField(
        null=True,
        blank=True,
        default=1,
        choices=[
            (0, '当月'),
            (1, '翌月'),
            (2, '翌々月'),
            (3, '3ヶ月後'),
        ],
        verbose_name='支払月',
        help_text='締日から何ヶ月後に支払うか（0=当月、1=翌月、2=翌々月）。デフォルト: 1（翌月）'
    )

    # 承認設定
    approval_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=1000000,
        verbose_name='承認必要金額閾値',
        help_text='この金額以上の案件は承認が必要'
    )

    # 運用ルール
    special_notes = models.TextField(blank=True, verbose_name='特記事項・運用ルール')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    # ① 基本情報 - 追加フィールド
    invoice_submission_deadline = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='請求書提出期限（日）',
        help_text='毎月の請求書提出期限日（例：25日提出の場合は25）'
    )
    invoice_submission_notes = models.TextField(
        blank=True,
        verbose_name='請求書提出期限 補足説明',
        help_text='例：毎月25日必着、月末必着など'
    )

    # ② 業務情報
    work_types = models.ManyToManyField(
        'WorkType',
        blank=True,
        related_name='client_companies',
        verbose_name='対応可能な工事種別',
        help_text='この元請から依頼される工事の種類を選択'
    )
    pricing_tier = models.TextField(
        blank=True,
        verbose_name='単価帯・共有単価表',
        help_text='例：A単価表、B単価のみ共有、1式◯万円など'
    )
    site_rules = models.TextField(
        blank=True,
        verbose_name='現場ルール',
        help_text='現場での注意事項やルールを箇条書きで入力'
    )

    # ③ 品質・コミュニケーション
    trouble_tendencies = models.TextField(
        blank=True,
        verbose_name='トラブル傾向',
        help_text='例：追加書類が多い、現場変更が急、指示内容が曖昧など'
    )

    WORK_EASE_CHOICES = [
        (1, 'とても作業しにくい'),
        (2, '作業しにくい'),
        (3, '普通'),
        (4, '作業しやすい'),
        (5, 'とても作業しやすい'),
    ]
    work_ease_rating = models.IntegerField(
        choices=WORK_EASE_CHOICES,
        null=True,
        blank=True,
        verbose_name='作業のしやすさ',
        help_text='現場での作業のしやすさを5段階で評価'
    )
    work_ease_notes = models.TextField(
        blank=True,
        verbose_name='作業のしやすさ 補足',
        help_text='作業のしやすさに関する具体的な情報'
    )

    # ④ 評価・リスク・戦略
    RATING_CHOICES = [
        (1, '非常に低い'),
        (2, '低い'),
        (3, '普通'),
        (4, '高い'),
        (5, 'とても高い'),
    ]
    response_ease_rating = models.IntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        verbose_name='対応のしやすさ',
        help_text='連絡対応や意思決定のスムーズさを5段階で評価'
    )
    response_ease_notes = models.TextField(
        blank=True,
        verbose_name='対応のしやすさ 補足',
        help_text='対応のしやすさに関する具体的な情報'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '元請会社'
        verbose_name_plural = '元請会社一覧'
        ordering = ['company_name']

    def __str__(self):
        return self.company_name

    def get_total_projects(self):
        """総案件数を取得"""
        return self.projects.count()

    def get_active_projects(self):
        """進行中の案件数を取得"""
        return self.projects.filter(
            project_status__in=['施工日待ち', '進行中']
        ).count()

    def get_statistics(self, start_date=None, end_date=None):
        """元請サマリ統計を計算（期間指定可能）"""
        from django.db.models import Sum, Avg, Count
        from decimal import Decimal

        # 対象案件を絞り込み
        projects = self.projects.all()
        if start_date:
            projects = projects.filter(created_at__gte=start_date)
        if end_date:
            projects = projects.filter(created_at__lte=end_date)

        # 基本集計
        stats = projects.aggregate(
            total_sales=Sum('order_amount'),
            avg_sales=Avg('order_amount'),
            project_count=Count('id')
        )

        # None値を0に変換
        total_sales = stats['total_sales'] or Decimal('0')
        avg_sales = stats['avg_sales'] or Decimal('0')
        project_count = stats['project_count'] or 0

        # 利益率の平均を手動計算（フィールドではなくメソッドなので）
        avg_profit_margin = Decimal('0')
        if project_count > 0:
            profit_margins = []
            for project in projects:
                breakdown = project.get_revenue_breakdown()
                if breakdown and breakdown.get('profit_margin'):
                    profit_margins.append(breakdown['profit_margin'])

            if profit_margins:
                avg_profit_margin = sum(profit_margins) / len(profit_margins)

        # レーダーチャート用データ（0-5のスケール）
        # 評価基準マスターから基準値を取得
        criteria = RatingCriteria.get_criteria()

        # 累計売上スコア計算
        if total_sales >= criteria.total_sales_score_5:
            total_sales_score = 5
        elif total_sales >= criteria.total_sales_score_4:
            total_sales_score = 4
        elif total_sales >= criteria.total_sales_score_3:
            total_sales_score = 3
        elif total_sales >= criteria.total_sales_score_2:
            total_sales_score = 2
        elif total_sales > 0:
            total_sales_score = 1
        else:
            total_sales_score = 0

        # 平均売上スコア計算
        if avg_sales >= criteria.avg_sales_score_5:
            avg_sales_score = 5
        elif avg_sales >= criteria.avg_sales_score_4:
            avg_sales_score = 4
        elif avg_sales >= criteria.avg_sales_score_3:
            avg_sales_score = 3
        elif avg_sales >= criteria.avg_sales_score_2:
            avg_sales_score = 2
        elif avg_sales > 0:
            avg_sales_score = 1
        else:
            avg_sales_score = 0

        # 平均粗利益率スコア計算
        if avg_profit_margin >= criteria.profit_margin_score_5:
            profit_margin_score = 5
        elif avg_profit_margin >= criteria.profit_margin_score_4:
            profit_margin_score = 4
        elif avg_profit_margin >= criteria.profit_margin_score_3:
            profit_margin_score = 3
        elif avg_profit_margin >= criteria.profit_margin_score_2:
            profit_margin_score = 2
        elif avg_profit_margin > 0:
            profit_margin_score = 1
        else:
            profit_margin_score = 0

        # 手動評価をスコアとして使用
        response_ease_score = self.response_ease_rating or 0
        work_ease_score = self.work_ease_rating or 0

        return {
            'total_sales': float(total_sales),
            'avg_sales': float(avg_sales),
            'avg_profit_margin': float(avg_profit_margin),
            'project_count': project_count,
            'total_sales_score': total_sales_score,
            'avg_sales_score': avg_sales_score,
            'profit_margin_score': profit_margin_score,
            'response_ease_score': response_ease_score,
            'work_ease_score': work_ease_score,
        }


class ContactPerson(models.Model):
    """元請会社の担当者情報"""
    client_company = models.ForeignKey(
        ClientCompany,
        on_delete=models.CASCADE,
        related_name='contact_persons',
        verbose_name='元請会社'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='担当者名'
    )
    personality_notes = models.TextField(
        blank=True,
        verbose_name='性格・特徴',
        help_text='担当者の性格や特徴、コミュニケーション時の注意点など'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='主担当',
        help_text='主担当者の場合はチェック'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='メールアドレス'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='電話番号'
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='役職'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='表示順'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        verbose_name = '担当者'
        verbose_name_plural = '担当者一覧'
        ordering = ['-is_primary', 'display_order', 'name']

    def __str__(self):
        primary_mark = '★' if self.is_primary else ''
        return f"{primary_mark}{self.name} ({self.client_company.company_name})"


class WorkType(models.Model):
    """工事種別マスター"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='工事種別名'
    )
    description = models.TextField(
        blank=True,
        verbose_name='説明'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='表示順'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        verbose_name = '工事種別'
        verbose_name_plural = '工事種別一覧'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class ContractorReview(models.Model):
    """職人評価 - Phase 8"""
    contractor = models.ForeignKey(
        'subcontract_management.Contractor',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='職人'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='contractor_reviews',
        verbose_name='案件'
    )

    # 評価スコア（1-5）
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='総合評価'
    )
    quality_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='品質スコア'
    )
    speed_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='スピードスコア'
    )
    communication_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='コミュニケーションスコア'
    )

    review_comment = models.TextField(blank=True, verbose_name='コメント')
    would_recommend = models.BooleanField(default=True, verbose_name='次回も依頼したい')

    # メタ情報
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='評価者'
    )
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name='評価日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '職人評価'
        verbose_name_plural = '職人評価一覧'
        ordering = ['-reviewed_at']
        unique_together = ['contractor', 'project']

    def __str__(self):
        return f"{self.contractor.name} - {self.project.management_no} ({self.overall_rating}点)"


class ApprovalLog(models.Model):
    """承認履歴 - Phase 8"""
    APPROVAL_TYPE_CHOICES = [
        ('estimate', '見積承認'),
        ('contractor_assign', '職人アサイン承認'),
        ('payment', '支払承認'),
        ('project_start', '案件開始承認'),
    ]

    STATUS_CHOICES = [
        ('pending', '承認待ち'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
        ('cancelled', 'キャンセル'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='approval_logs',
        verbose_name='案件'
    )
    approval_type = models.CharField(
        max_length=20,
        choices=APPROVAL_TYPE_CHOICES,
        verbose_name='承認種別'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='ステータス'
    )

    # 申請情報
    requester = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_requests',
        verbose_name='申請者'
    )
    request_reason = models.TextField(blank=True, verbose_name='申請理由')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='金額'
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name='申請日時')

    # 承認情報
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals',
        verbose_name='承認者'
    )
    approval_comment = models.TextField(blank=True, verbose_name='承認コメント')
    rejection_reason = models.TextField(blank=True, verbose_name='却下理由')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='承認日時')

    class Meta:
        verbose_name = '承認履歴'
        verbose_name_plural = '承認履歴一覧'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.project.management_no} - {self.get_approval_type_display()} ({self.get_status_display()})"


class ChecklistTemplate(models.Model):
    """チェックリストテンプレート - Phase 8"""
    name = models.CharField(max_length=200, verbose_name='テンプレート名')
    work_type = models.CharField(max_length=50, verbose_name='施工種別')
    description = models.TextField(blank=True, verbose_name='説明')

    # チェック項目（JSON配列）
    # [{"name": "項目名", "description": "説明", "order": 1}]
    items = models.JSONField(default=list, verbose_name='チェック項目')

    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'チェックリストテンプレート'
        verbose_name_plural = 'チェックリストテンプレート一覧'
        ordering = ['work_type', 'name']

    def __str__(self):
        return f"{self.work_type} - {self.name}"


class ProjectChecklist(models.Model):
    """案件チェックリスト - Phase 8"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='checklists',
        verbose_name='案件'
    )
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='テンプレート'
    )

    # チェック項目の状態（JSON配列）
    # [{"name": "項目名", "completed": true/false, "notes": "メモ", "completed_by": "user_id", "completed_at": "datetime"}]
    items = models.JSONField(default=list, verbose_name='チェック項目')

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '案件チェックリスト'
        verbose_name_plural = '案件チェックリスト一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.management_no} - {self.template.name if self.template else 'カスタム'}"

    def get_completion_rate(self):
        """完了率を計算"""
        if not self.items:
            return 0
        completed = sum(1 for item in self.items if item.get('completed', False))
        return int((completed / len(self.items)) * 100) if self.items else 0



class ProjectFile(models.Model):
    """案件ファイル添付 - Phase 5"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='案件'
    )
    file = models.FileField(
        upload_to='project_files/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='ファイル'
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name='ファイル名'
    )
    file_size = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='ファイルサイズ（バイト）'
    )
    file_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='ファイルタイプ'
    )
    description = models.TextField(
        blank=True,
        verbose_name='説明'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='アップロード者'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='アップロード日時'
    )
    related_step = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='関連ステップ',
        help_text='このファイルが関連するステップ（例：estimate, survey）'
    )

    # リンクされたファイル用のフィールド
    is_linked_file = models.BooleanField(
        default=False,
        verbose_name='リンクファイル',
        help_text='他の案件のPDF（発注書・請求書）へのリンク'
    )
    linked_source_file = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='リンク元ファイルパス',
        help_text='発注書または請求書のファイルパス'
    )
    linked_source_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('purchase_order', '発注書'),
            ('invoice', '請求書'),
        ],
        verbose_name='リンク元タイプ'
    )
    linked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='リンク作成日時',
        help_text='ファイルがリンクされた日時（秒単位）'
    )

    class Meta:
        verbose_name = '案件ファイル'
        verbose_name_plural = '案件ファイル一覧'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.project.management_no} - {self.file_name}"

    def get_file_size_display(self):
        """ファイルサイズを人間が読める形式で表示"""
        size = self.file_size
        if size is None:
            return "不明"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class RatingCriteria(models.Model):
    """レーダーチャート評価基準マスター

    累計売上、平均売上、平均粗利益率のスコア基準を管理
    シングルトンモデル（1レコードのみ）
    """
    # 累計売上スコア基準（円）
    total_sales_score_5 = models.DecimalField(
        max_digits=12, decimal_places=0, default=10000000,
        verbose_name='累計売上5点基準', help_text='この金額以上で5点'
    )
    total_sales_score_4 = models.DecimalField(
        max_digits=12, decimal_places=0, default=5000000,
        verbose_name='累計売上4点基準', help_text='この金額以上で4点'
    )
    total_sales_score_3 = models.DecimalField(
        max_digits=12, decimal_places=0, default=1000000,
        verbose_name='累計売上3点基準', help_text='この金額以上で3点'
    )
    total_sales_score_2 = models.DecimalField(
        max_digits=12, decimal_places=0, default=500000,
        verbose_name='累計売上2点基準', help_text='この金額以上で2点'
    )

    # 平均売上スコア基準（円）
    avg_sales_score_5 = models.DecimalField(
        max_digits=12, decimal_places=0, default=1000000,
        verbose_name='平均売上5点基準', help_text='この金額以上で5点'
    )
    avg_sales_score_4 = models.DecimalField(
        max_digits=12, decimal_places=0, default=500000,
        verbose_name='平均売上4点基準', help_text='この金額以上で4点'
    )
    avg_sales_score_3 = models.DecimalField(
        max_digits=12, decimal_places=0, default=300000,
        verbose_name='平均売上3点基準', help_text='この金額以上で3点'
    )
    avg_sales_score_2 = models.DecimalField(
        max_digits=12, decimal_places=0, default=100000,
        verbose_name='平均売上2点基準', help_text='この金額以上で2点'
    )

    # 平均粗利益率スコア基準（%）
    profit_margin_score_5 = models.DecimalField(
        max_digits=5, decimal_places=2, default=40.0,
        verbose_name='平均粗利益率5点基準', help_text='この%以上で5点'
    )
    profit_margin_score_4 = models.DecimalField(
        max_digits=5, decimal_places=2, default=30.0,
        verbose_name='平均粗利益率4点基準', help_text='この%以上で4点'
    )
    profit_margin_score_3 = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.0,
        verbose_name='平均粗利益率3点基準', help_text='この%以上で3点'
    )
    profit_margin_score_2 = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.0,
        verbose_name='平均粗利益率2点基準', help_text='この%以上で2点'
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='更新者'
    )

    class Meta:
        db_table = 'rating_criteria'
        verbose_name = '評価基準'
        verbose_name_plural = '評価基準'

    def __str__(self):
        return '評価基準設定'

    @classmethod
    def get_criteria(cls):
        """評価基準を取得（シングルトン）"""
        criteria, created = cls.objects.get_or_create(pk=1)
        return criteria

    def save(self, *args, **kwargs):
        """シングルトンを保証"""
        self.pk = 1
        super().save(*args, **kwargs)


class CompanySettings(models.Model):
    """会社情報とPDF設定を管理するシングルトンモデル"""

    # 自社情報
    company_name = models.CharField(max_length=200, verbose_name='会社名', blank=True, default='')
    company_address = models.TextField(verbose_name='住所', blank=True, default='')
    company_phone = models.CharField(max_length=50, verbose_name='電話番号', blank=True, default='')
    company_fax = models.CharField(max_length=50, verbose_name='FAX', blank=True, default='')
    company_email = models.EmailField(verbose_name='メールアドレス', blank=True, default='')
    company_representative = models.CharField(max_length=100, verbose_name='代表者名', blank=True, default='')

    # 発注書設定
    purchase_order_remarks = models.TextField(
        verbose_name='発注書 備考欄',
        blank=True,
        default='上記の通り発注いたします。\nご査収の程よろしくお願い申し上げます。',
        help_text='発注書の備考欄に表示されるテキスト'
    )

    # 請求書設定
    invoice_remarks = models.TextField(
        verbose_name='請求書 備考欄',
        blank=True,
        default='上記の通り請求させていただきます。\nお支払いの程よろしくお願い申し上げます。',
        help_text='請求書の備考欄に表示されるテキスト'
    )

    # 作成・更新日時
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'company_settings'
        verbose_name = '会社設定'
        verbose_name_plural = '会社設定'

    def __str__(self):
        return f'会社設定 ({self.company_name or "未設定"})'

    @classmethod
    def get_settings(cls):
        """設定を取得（シングルトン）"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        """PKを1に固定してシングルトンを保証"""
        self.pk = 1
        super().save(*args, **kwargs)
