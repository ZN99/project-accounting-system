from django import forms
from django.utils import timezone
from .models import Project, FixedCost, VariableCost, ClientCompany, ApprovalLog, ContractorReview, ChecklistTemplate, ProjectChecklist, ProjectFile


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = [
            'management_no', 'billing_amount', 'amount_difference',
            'created_at', 'updated_at',
            # Phase 8: 自動計算・システム管理フィールド
            'priority_score', 'requires_approval', 'approval_status',
            'approved_by', 'approved_at',
            # Phase 11: デフォルト値があるフィールド（フォームから除外）
            'witness_status', 'witness_assignee_type', 'estimate_status',
            'construction_status', 'payment_status',
        ]
        widgets = {
            'site_address': forms.Textarea(attrs={'rows': 2}),
            'client_address': forms.Textarea(attrs={'rows': 2}),  # 旧: contractor_address
            'notes': forms.Textarea(attrs={'rows': 4}),
            'estimate_issued_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_due_date': forms.DateInput(attrs={'type': 'date'}),
            'work_start_date': forms.DateInput(attrs={'type': 'date'}),
            'work_end_date': forms.DateInput(attrs={'type': 'date'}),
            'contract_date': forms.DateInput(attrs={'type': 'date'}),
            # Phase 5 widgets
            'asap_requested': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'work_date_specified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'invoice_status': forms.Select(attrs={'class': 'form-select'}),
            # Phase 8 widgets
            'client_company': forms.Select(attrs={'class': 'form-select', 'id': 'id_client_company'}),
            'key_handover_location': forms.Textarea(attrs={'rows': 2}),
            'key_handover_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'key_handover_notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
                field.widget.attrs['class'] = 'form-control'

        # 必須項目の設定（基本情報のみ）
        required_fields = [
            'site_name',  # 現場名
            'work_type',  # 施工種別
            'client_name',  # 元請会社名
        ]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

        # 以下は必須ではない
        if 'project_manager' in self.fields:
            self.fields['project_manager'].required = False
        if 'payment_due_date' in self.fields:
            self.fields['payment_due_date'].required = False

        # Phase 8: 元請会社選択肢
        if 'client_company' in self.fields:
            self.fields['client_company'].queryset = ClientCompany.objects.filter(is_active=True).order_by('company_name')
            self.fields['client_company'].empty_label = "選択してください（任意）"
            self.fields['client_company'].required = False

        # 諸経費金額は必須でない
        if 'expense_amount_1' in self.fields:
            self.fields['expense_amount_1'].required = False
        if 'expense_amount_2' in self.fields:
            self.fields['expense_amount_2'].required = False


class FixedCostForm(forms.ModelForm):
    """固定費入力フォーム"""

    class Meta:
        model = FixedCost
        fields = ['name', 'cost_type', 'monthly_amount', 'start_date', 'end_date', 'is_active', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '費目名を入力（例：事務所家賃）'
            }),
            'cost_type': forms.Select(attrs={'class': 'form-select'}),
            'monthly_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '月額（円）',
                'min': '0'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備考があれば入力'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # デフォルト値設定
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['is_active'].initial = True

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError('終了日は開始日より後の日付を選択してください。')

        return cleaned_data


class VariableCostForm(forms.ModelForm):
    """変動費入力フォーム"""

    class Meta:
        model = VariableCost
        fields = ['name', 'cost_type', 'amount', 'incurred_date', 'project', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '費目名を入力（例：交通費、接待費）'
            }),
            'cost_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '金額（円）',
                'min': '0'
            }),
            'incurred_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備考があれば入力'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # デフォルト値設定
        if not self.instance.pk:
            self.fields['incurred_date'].initial = timezone.now().date()

        # プロジェクト選択肢を完工済みのものに限定（旧: 受注）
        self.fields['project'].queryset = Project.objects.filter(project_status='完工').order_by('-created_at')
        self.fields['project'].empty_label = "関連案件なし（一般経費）"

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('金額は0円より大きい値を入力してください。')
        return amount


class FixedCostFilterForm(forms.Form):
    """固定費フィルタフォーム"""
    cost_type = forms.ChoiceField(
        choices=[('', '全ての種別')] + FixedCost.COST_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.ChoiceField(
        choices=[('', '全て'), ('true', 'アクティブのみ'), ('false', '無効のみ')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class VariableCostFilterForm(forms.Form):
    """変動費フィルタフォーム"""
    cost_type = forms.ChoiceField(
        choices=[('', '全ての種別')] + VariableCost.COST_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(project_status='完工'),  # 旧: order_status='受注'
        required=False,
        empty_label="全ての案件",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ClientCompanyForm(forms.ModelForm):
    """元請会社登録・編集フォーム - Phase 8"""

    class Meta:
        model = ClientCompany
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 'address',
            'default_key_handover_location', 'key_handover_notes',
            'completion_report_template', 'completion_report_notes',
            'approval_threshold', 'special_notes', 'is_active'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '会社名を入力'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '担当者名を入力'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '03-1234-5678'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '住所を入力'
            }),
            'default_key_handover_location': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '鍵受け渡し場所（デフォルト）'
            }),
            'key_handover_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '鍵受け渡しに関する特記事項'
            }),
            'completion_report_template': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'completion_report_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '完了報告に関する特記事項'
            }),
            'approval_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1000000',
                'min': '0'
            }),
            'special_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '特記事項・運用ルールなど'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # デフォルト値設定
        if not self.instance.pk:
            self.fields['is_active'].initial = True
            self.fields['approval_threshold'].initial = 1000000

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and '@' not in email:
            raise forms.ValidationError('正しいメールアドレスを入力してください。')
        return email


class ClientCompanyFilterForm(forms.Form):
    """元請会社フィルタフォーム - Phase 8"""
    is_active = forms.ChoiceField(
        choices=[('', '全て'), ('true', 'アクティブのみ'), ('false', '無効のみ')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '会社名で検索'
        })
    )


class ApprovalRequestForm(forms.ModelForm):
    """承認申請フォーム - Phase 8"""

    class Meta:
        model = ApprovalLog
        fields = ['approval_type', 'request_reason', 'amount']
        widgets = {
            'approval_type': forms.Select(attrs={'class': 'form-select'}),
            'request_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '承認が必要な理由を入力してください'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '金額（円）',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_reason'].required = True
        self.fields['amount'].required = False


class ApprovalActionForm(forms.Form):
    """承認処理フォーム - Phase 8"""
    action = forms.ChoiceField(
        choices=[('approve', '承認'), ('reject', '却下')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='処理'
    )
    approval_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '承認コメント（任意）'
        }),
        label='承認コメント'
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '却下理由（却下の場合は必須）'
        }),
        label='却下理由'
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')

        if action == 'reject' and not rejection_reason:
            raise forms.ValidationError('却下する場合は理由を入力してください。')

        return cleaned_data


class ContractorReviewForm(forms.ModelForm):
    """職人評価フォーム - Phase 8"""

    class Meta:
        model = ContractorReview
        fields = [
            'overall_rating', 'quality_score', 'speed_score',
            'communication_score', 'review_comment', 'would_recommend'
        ]
        widgets = {
            'overall_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'placeholder': '1〜5'
            }),
            'quality_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'placeholder': '1〜5'
            }),
            'speed_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'placeholder': '1〜5'
            }),
            'communication_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'placeholder': '1〜5'
            }),
            'review_comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '評価コメントを入力してください'
            }),
            'would_recommend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['overall_rating', 'quality_score', 'speed_score', 'communication_score']:
            self.fields[field_name].required = True


class ChecklistTemplateForm(forms.ModelForm):
    """チェックリストテンプレートフォーム - Phase 8"""

    class Meta:
        model = ChecklistTemplate
        fields = ['name', 'work_type', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'テンプレート名を入力'
            }),
            'work_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '施工種別を入力（例：解体工事、電気工事）'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'テンプレートの説明を入力'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['work_type'].required = True
        if not self.instance.pk:
            self.fields['is_active'].initial = True


class ProjectChecklistSelectForm(forms.Form):
    """案件チェックリスト選択フォーム - Phase 8"""
    template = forms.ModelChoiceField(
        queryset=ChecklistTemplate.objects.filter(is_active=True),
        required=True,
        empty_label="テンプレートを選択してください",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='チェックリストテンプレート'
    )

    def __init__(self, *args, **kwargs):
        work_type = kwargs.pop('work_type', None)
        super().__init__(*args, **kwargs)
        if work_type:
            self.fields['template'].queryset = ChecklistTemplate.objects.filter(
                is_active=True,
                work_type=work_type
            )

class ProjectFileUploadForm(forms.ModelForm):
    """案件ファイルアップロードフォーム - Phase 5"""

    class Meta:
        model = ProjectFile
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ファイルの説明（任意）'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = True
        self.fields['description'].required = False
