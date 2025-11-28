from django import forms
from .models import Contractor, Subcontract


class ContractorForm(forms.ModelForm):
    # Phase 8: JSONField用のテキスト入力フィールド
    skill_categories_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': '例: 電気工事, 空調工事, 給排水工事'}),
        label='スキルカテゴリ',
        help_text='カンマ区切りで入力'
    )
    service_areas_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': '例: 東京23区, 神奈川県全域'}),
        label='対応可能地域',
        help_text='カンマ区切りで入力'
    )

    class Meta:
        model = Contractor
        fields = [
            'name', 'contractor_type', 'address', 'contact_person',
            'phone', 'email', 'specialties', 'hourly_rate', 'is_active',
            'bank_name', 'branch_name', 'account_type', 'account_number',
            'account_holder', 'payment_day', 'payment_cycle',
            # Phase 8 新規フィールド
            'skill_level', 'trust_level', 'certifications'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'specialties': forms.Textarea(attrs={'rows': 3}),
            'hourly_rate': forms.NumberInput(attrs={'step': '1'}),
            'payment_day': forms.NumberInput(attrs={'min': '1', 'max': '31'}),
            'certifications': forms.Textarea(attrs={'rows': 3, 'placeholder': '保有資格を改行区切りで入力'}),
            'trust_level': forms.NumberInput(attrs={'min': '1', 'max': '5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'

        # Phase 8: 既存データがある場合、JSONFieldをテキストに変換
        if self.instance.pk:
            if self.instance.skill_categories:
                self.fields['skill_categories_text'].initial = ', '.join(self.instance.skill_categories)
            if self.instance.service_areas:
                self.fields['service_areas_text'].initial = ', '.join(self.instance.service_areas)

        # 必須項目の設定
        required_fields = ['name', 'contractor_type', 'address']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Phase 8: テキストフィールドをJSON配列に変換
        skill_categories_text = self.cleaned_data.get('skill_categories_text', '')
        if skill_categories_text:
            instance.skill_categories = [s.strip() for s in skill_categories_text.split(',') if s.strip()]
        else:
            instance.skill_categories = []

        service_areas_text = self.cleaned_data.get('service_areas_text', '')
        if service_areas_text:
            instance.service_areas = [s.strip() for s in service_areas_text.split(',') if s.strip()]
        else:
            instance.service_areas = []

        if commit:
            instance.save()
        return instance


class SubcontractForm(forms.ModelForm):
    class Meta:
        model = Subcontract
        exclude = [
            'project', 'management_no', 'site_name', 'site_address',
            'total_material_cost', 'created_at', 'updated_at',
            # 外注先編集では使用しないフィールド
            'worker_type', 'internal_worker', 'internal_worker_name',
            'internal_department', 'internal_pricing_type',
            'internal_hourly_rate', 'estimated_hours',
            'dynamic_cost_items', 'dynamic_material_costs',
            'dynamic_additional_cost_items', 'tax_type'
        ]
        widgets = {
            'payment_due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'work_description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # 外注先を有効なもののみに限定
        self.fields['contractor'].queryset = Contractor.objects.filter(is_active=True)

        # 必須項目の設定
        required_fields = ['contractor']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

        # 任意項目の設定
        optional_fields = [
            'billed_amount',
            'material_cost_1', 'material_cost_2', 'material_cost_3',
            'material_item_1', 'material_item_2', 'material_item_3'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

        # フィールドラベルの設定
        self.fields['billed_amount'].help_text = '実際に請求された金額を入力してください（任意）'
        self.fields['contract_amount'].help_text = '発注金額を入力してください（任意）'
        self.fields['contract_amount'].required = False