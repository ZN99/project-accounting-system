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

    # 受注・見積情報
    project_status = models.CharField(  # 旧: order_status
        max_length=20,  # max_lengthを20に拡張（「施工日待ち」対応）
        choices=PROJECT_STATUS_CHOICES,
        default='ネタ',  # 旧: 検討中
        verbose_name='受注ヨミ'
    )
    estimate_issued_date = models.DateField(
        null=True, blank=True, verbose_name='見積書発行日'
    )
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
    client_name = models.CharField(max_length=100, verbose_name='元請名')  # 旧: contractor_name (請負業者名)
    client_address = models.TextField(verbose_name='元請住所', blank=True)  # 旧: contractor_address (請負業者住所)、任意に変更
    project_manager = models.CharField(max_length=50, verbose_name='案件担当')

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

    work_start_date = models.DateField(
        null=True, blank=True, verbose_name='工事開始日'
    )
    work_start_completed = models.BooleanField(
        default=False, verbose_name='工事開始完了'
    )
    work_end_date = models.DateField(
        null=True, blank=True, verbose_name='工事終了日'
    )
    work_end_completed = models.BooleanField(
        default=False, verbose_name='工事終了完了'
    )
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

    # 現地調査関連
    survey_required = models.BooleanField(default=False, verbose_name='現地調査必要')
    survey_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', '不要'),
            ('required', '必要'),
            ('scheduled', '予定済み'),
            ('in_progress', '調査中'),
            ('completed', '完了'),
        ],
        default='not_required',
        verbose_name='現地調査ステータス'
    )
    survey_date = models.DateField(
        null=True, blank=True, verbose_name='現調日'
    )
    survey_assignees = models.JSONField(
        default=list, blank=True,
        verbose_name='現調担当者',
        help_text='現地調査の担当者リスト（職人）'
    )

    # 立ち会い関連 - Phase 11 追加
    witness_date = models.DateField(
        null=True, blank=True, verbose_name='立ち会い日'
    )
    witness_status = models.CharField(
        max_length=20,
        choices=[
            ('waiting', '立ち会い待ち'),
            ('in_progress', '立ち会い中'),
            ('completed', '完了'),
        ],
        default='waiting',
        verbose_name='立ち会いステータス'
    )
    witness_assignees = models.JSONField(
        default=list, blank=True,
        verbose_name='立ち会い担当者',
        help_text='立ち会いの担当者リスト（自社または職人）'
    )
    witness_assignee_type = models.CharField(
        max_length=20,
        choices=[
            ('internal', '自社'),
            ('contractor', '職人'),
        ],
        default='internal',
        verbose_name='立ち会い担当者タイプ'
    )

    # 見積もりステータス拡張 - Phase 11 追加
    estimate_status = models.CharField(
        max_length=20,
        choices=[
            ('not_issued', '未発行'),
            ('issued', '見積もり書発行'),
            ('under_review', '見積もり審査中'),
            ('approved', '承認'),
        ],
        default='not_issued',
        verbose_name='見積もりステータス'
    )

    # 着工ステータス拡張 - Phase 11 追加
    construction_status = models.CharField(
        max_length=20,
        choices=[
            ('waiting', '着工日待ち'),
            ('in_progress', '工事中'),
            ('completed', '完工'),
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

    # 完工・請求管理 - Phase 1 追加
    completion_date = models.DateField(
        null=True, blank=True,
        verbose_name='完工日',
        help_text='工事が完工した日（発生主義売上の基準日）'
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

    # その他
    notes = models.TextField(blank=True, verbose_name='備考')
    additional_items = models.JSONField(default=dict, blank=True, verbose_name="追加項目")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '案件'
        verbose_name_plural = '案件一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.management_no} - {self.site_name}"

    def generate_management_no(self):
        """管理No自動採番"""
        current_year = timezone.now().year
        year_suffix = str(current_year)[-2:]  # 下2桁

        # 今年の最新番号を取得
        latest = Project.objects.filter(
            management_no__startswith=f'P{year_suffix}'
        ).order_by('-management_no').first()

        if latest:
            # 最新番号から連番部分を取得してインクリメント
            latest_num = int(latest.management_no[3:])
            new_num = latest_num + 1
        else:
            new_num = 1

        return f'P{year_suffix}{new_num:04d}'

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

        # Phase 8: 元請会社連携処理
        if self.client_company:
            # 鍵受け渡し場所のデフォルト値設定
            if not self.key_handover_location and self.client_company.default_key_handover_location:
                self.key_handover_location = self.client_company.default_key_handover_location

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

        super().save(*args, **kwargs)

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
        """ステータスに応じた背景色（Hex）を返す"""
        color_map = {
            '完工': '#28a745',       # 緑（旧: 受注）
            'NG': '#6c757d',        # グレー
            '施工日待ち': '#dc3545', # ピンク/赤（旧: A）
            'ネタ': '#ffc107',      # 黄色（旧: 検討中）
            '進行中': '#17a2b8'     # 青（新規）
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
        """進捗状況の総合判定を返す - 新5ステップシステムと同期"""
        if self.project_status == 'NG':
            return {'phase': 'NG', 'color': 'secondary', 'percentage': 0}
        elif self.project_status == 'ネタ':  # 旧: 検討中
            return {'phase': 'ネタ', 'color': 'warning', 'percentage': 0}

        # 新5ステップシステムから現在の段階を取得
        stage_info = self.get_current_project_stage()
        phase = stage_info['stage']
        color = stage_info['color']

        # パーセンテージを計算（5つのステップから）
        if not self.additional_items:
            percentage = 0
        else:
            complex_fields = self.additional_items.get('complex_step_fields', {})

            # 5つのステップの完了状況をチェック
            completed_count = 0
            total_steps = 5

            # 1. 立ち会い日
            if complex_fields.get('attendance_actual_date'):
                completed_count += 1

            # 2. 現調日
            if complex_fields.get('survey_actual_date'):
                completed_count += 1

            # 3. 見積もり発行日
            if complex_fields.get('estimate_issued_date') or complex_fields.get('estimate_not_required'):
                completed_count += 1

            # 4. 着工日
            if complex_fields.get('construction_start_actual_date'):
                completed_count += 1

            # 5. 完工日
            if complex_fields.get('completion_actual_date') or complex_fields.get('completion_completed'):
                completed_count += 1

            percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 0

        return {'phase': phase, 'color': color, 'percentage': percentage}

    def get_progress_details(self):
        """進捗の詳細情報を返す（動的ステップを含む）"""
        active_steps = self.progress_steps.filter(is_active=True).order_by('order', 'template__order')
        completed_steps = active_steps.filter(is_completed=True)

        # 実際のステップ数を使用する
        # additional_itemsのstep_orderはUIの表示順序を定義しているが、
        # 実際のステップがすべて作成されているとは限らない
        total_steps = active_steps.count()

        # step_orderに現場調査があるが、実際のステップが作成されていない場合の対応
        if self.additional_items and 'step_order' in self.additional_items:
            step_order = self.additional_items.get('step_order', [])

            # step_orderに現場調査が含まれているか確認
            has_site_survey_in_order = any(s.get('step') == 'site_survey' for s in step_order)

            # 実際のステップに現場調査が含まれているか確認
            has_site_survey_step = active_steps.filter(template__name='現場調査').exists()

            # step_orderに現場調査があるが、実際のステップにない場合
            if has_site_survey_in_order and not has_site_survey_step:
                # UIの整合性のため、仮想的に1ステップ追加
                total_steps += 1

        completed_steps_count = completed_steps.count()

        return {
            'total_steps': total_steps,
            'completed_steps': completed_steps_count,
            'remaining_steps': total_steps - completed_steps_count,
            'steps': [
                {
                    'name': step.template.name,
                    'completed': step.is_completed,
                    'completed_date': step.completed_date,
                    'icon': step.template.icon
                }
                for step in active_steps
            ]
        }

    def get_current_project_stage(self):
        """5つのステップに基づいた現在のプロジェクト段階を返す

        このロジックは案件詳細画面のJavaScriptと完全に一致させています。

        カラーコード統一ルール:
        - verified (濃い緑): 完了チェックボックスON
        - success (緑): 実施日 OR 予定日が入力されている
        - warning (黄色): 予定日のみ入力されている（着工日待ちの場合）
        - secondary (グレー): 何も入力されていない
        """
        complex_fields = self.additional_items.get('complex_step_fields', {}) if self.additional_items else {}

        # 完工日をチェック（基本フィールドと複合フィールドの両方）
        if self.work_end_completed or complex_fields.get('completion_completed'):
            return {'stage': '完工', 'color': 'verified'}  # 完了チェックON → 濃い緑
        elif complex_fields.get('completion_actual_date') or self.work_end_date:
            return {'stage': '完工', 'color': 'success'}  # 実施日入力 → 緑

        # 着工日をチェック（基本フィールドと複合フィールドの両方）
        if self.work_start_completed:
            return {'stage': '工事中', 'color': 'verified'}  # 完了チェックON → 濃い緑
        elif complex_fields.get('construction_start_actual_date'):
            return {'stage': '工事中', 'color': 'success'}  # 実施日入力 → 緑
        elif self.work_start_date or complex_fields.get('construction_start_scheduled_date'):
            return {'stage': '着工日待ち', 'color': 'warning'}  # 着工予定のみ → 着工日待ち（黄色）

        # 見積もり発行日をチェック（基本フィールドと複合フィールドの両方）
        if self.estimate_issued_date or complex_fields.get('estimate_issued_date'):
            return {'stage': '見積もり審査中', 'color': 'warning'}  # 発行済み → 黄色
        # 見積もり不要の場合は、次のステップの状態を表示するため、ここでは何もしない

        # 現調日をチェック
        if complex_fields.get('survey_actual_date'):
            return {'stage': '現調済み', 'color': 'success'}  # 実施日入力 → 緑
        elif complex_fields.get('survey_scheduled_date'):
            return {'stage': '現調待ち', 'color': 'warning'}  # 予定日のみ → 黄色

        # 立ち会い日をチェック
        if complex_fields.get('attendance_actual_date'):
            return {'stage': '立ち会い済み', 'color': 'success'}  # 実施日入力 → 緑
        elif complex_fields.get('attendance_scheduled_date'):
            return {'stage': '立ち会い待ち', 'color': 'warning'}  # 予定日のみ → 黄色

        # デフォルト
        return {'stage': '未開始', 'color': 'secondary'}  # 何も入力なし → グレー

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

            # 実際の原価を計算（外注費 + 材料費）
            total_subcontract_cost = sum(s.billed_amount for s in subcontracts)
            total_material_cost = sum(s.total_material_cost for s in subcontracts)
            cost_of_sales = total_subcontract_cost + total_material_cost
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
        """現地調査ステータスの表示名と色を返す"""
        status_info = {
            'not_required': {'display': '不要', 'color': 'secondary'},
            'required': {'display': '必要', 'color': 'warning'},
            'scheduled': {'display': '予定済み', 'color': 'info'},
            'in_progress': {'display': '調査中', 'color': 'primary'},
            'completed': {'display': '完了', 'color': 'success'},
        }
        return status_info.get(self.survey_status, {'display': '不明', 'color': 'secondary'})

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
        help_text='毎月の支払日（1-31）。例：25日払いの場合は25'
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
        Contractor,
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
    """ユーザープロファイル - ロール管理"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    roles = models.JSONField(default=list, verbose_name="ロール")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
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


class Notification(models.Model):
    """通知モデル"""
    NOTIFICATION_TYPES = [
        ('mention', 'メンション'),
        ('comment', 'コメント'),
        ('project_update', '案件更新'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="受信者")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="通知タイプ")
    title = models.CharField(max_length=200, verbose_name="タイトル")
    message = models.TextField(verbose_name="メッセージ")
    link = models.CharField(max_length=500, blank=True, verbose_name="リンク")
    is_read = models.BooleanField(default=False, verbose_name="既読フラグ")
    related_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="関連コメント")
    related_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name="関連案件")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知一覧"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.get_notification_type_display()} - {self.title}"


class ClientCompany(models.Model):
    """元請会社マスター - Phase 8"""
    company_name = models.CharField(max_length=200, unique=True, verbose_name='会社名')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='担当者名')
    email = models.EmailField(blank=True, verbose_name='メールアドレス')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話番号')
    address = models.TextField(blank=True, verbose_name='住所')

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
        verbose_name='ファイル'
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name='ファイル名'
    )
    file_size = models.IntegerField(
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

    class Meta:
        verbose_name = '案件ファイル'
        verbose_name_plural = '案件ファイル一覧'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.project.management_no} - {self.file_name}"

    def get_file_size_display(self):
        """ファイルサイズを人間が読める形式で表示"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
