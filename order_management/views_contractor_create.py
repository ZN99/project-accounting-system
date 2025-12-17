"""業者新規作成ビュー"""
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

# 修正: subcontract_managementのContractorモデルを使用
from subcontract_management.models import Contractor, ContractorFieldCategory, ContractorFieldDefinition


class ContractorCreateView(LoginRequiredMixin, CreateView):
    """業者新規作成ビュー"""
    model = Contractor
    template_name = 'order_management/contractor_form.html'
    fields = [
        'name', 'contractor_type', 'address', 'phone', 'email', 'contact_person',
        'hourly_rate', 'specialties', 'is_active',
        # 支払い情報
        'payment_cycle', 'closing_day', 'payment_offset_months', 'payment_day',
        # 銀行口座情報
        'bank_name', 'branch_name', 'account_type', 'account_number', 'account_holder'
    ]
    success_url = reverse_lazy('order_management:external_contractor_management')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # URLパラメータから業者タイプを取得
        contractor_type = self.request.GET.get('type', '')

        # タイプに応じたページタイトルとデフォルト値を設定
        if contractor_type == 'individual':
            context['page_title'] = '新規個人職人追加'
            context['contractor_type'] = 'individual'
        elif contractor_type == 'company':
            context['page_title'] = '新規協力会社追加'
            context['contractor_type'] = 'company'
        elif contractor_type == 'material':
            context['page_title'] = '新規資材業者追加'
            context['contractor_type'] = 'material'
        else:
            context['page_title'] = '新規業者追加'
            context['contractor_type'] = 'company'  # デフォルトは協力会社

        context['back_url'] = self.request.GET.get('back', reverse_lazy('order_management:external_contractor_management'))

        # カスタムフィールド定義をカテゴリごとに取得
        categories = ContractorFieldCategory.objects.filter(
            is_active=True
        ).prefetch_related('field_definitions').order_by('order')

        custom_fields_by_category = []
        for category in categories:
            fields_data = []
            for field_def in category.field_definitions.filter(is_active=True).order_by('order'):
                fields_data.append({
                    'definition': field_def,
                    'current_value': ''  # 新規作成なので空
                })

            if fields_data:  # フィールドがある場合のみ追加
                custom_fields_by_category.append({
                    'category': category,
                    'fields': fields_data
                })

        context['custom_fields_by_category'] = custom_fields_by_category

        # 地方ごとの都道府県マッピング
        context['regions_mapping'] = {
            '北海道': ['北海道'],
            '東北': ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県'],
            '関東': ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県'],
            '中部': ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県'],
            '近畿': ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県'],
            '中国': ['鳥取県', '島根県', '岡山県', '広島県', '山口県'],
            '四国': ['徳島県', '香川県', '愛媛県', '高知県'],
            '九州・沖縄': ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
        }

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # フォームフィールドにBootstrapクラスを追加
        form.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '業者名を入力してください',
            'required': True
        })
        form.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '住所を入力してください'
        })
        form.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '電話番号を入力してください'
        })
        form.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'メールアドレスを入力してください'
        })
        form.fields['contact_person'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '担当者名を入力してください'
        })
        form.fields['contractor_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['specialties'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '専門分野を入力してください（例：建築工事、電気工事）'
        })
        form.fields['hourly_rate'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '時給単価を入力してください'
        })
        form.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input'
        })

        # 支払い情報フィールド
        form.fields['payment_cycle'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['closing_day'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1-31',
            'min': '1',
            'max': '31'
        })
        form.fields['payment_offset_months'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['payment_day'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1-31',
            'min': '1',
            'max': '31'
        })

        # 銀行口座情報フィールド
        form.fields['bank_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: みずほ銀行'
        })
        form.fields['branch_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 渋谷支店'
        })
        form.fields['account_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['account_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '1234567'
        })
        form.fields['account_holder'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: カ）マルマルケンセツ'
        })

        return form

    def get_initial(self):
        initial = super().get_initial()

        # URLパラメータから業者タイプを取得してデフォルト値を設定
        contractor_type = self.request.GET.get('type', '')

        if contractor_type == 'individual':
            initial['contractor_type'] = 'individual'
        elif contractor_type == 'material':
            initial['contractor_type'] = 'material'
        else:
            initial['contractor_type'] = 'company'  # デフォルトは協力会社

        # デフォルトでアクティブに設定
        initial['is_active'] = True

        return initial

    def form_valid(self, form):
        # 業者名の重複チェック
        name = form.cleaned_data['name']
        if Contractor.objects.filter(name=name).exists():
            messages.error(self.request, f'業者名「{name}」は既に登録されています。')
            return self.form_invalid(form)

        # 保存前にカスタムフィールドの値を設定
        contractor = form.save(commit=False)

        # カスタムフィールドの値を取得して保存
        custom_fields_data = {}
        field_definitions = ContractorFieldDefinition.objects.filter(is_active=True)

        for field_def in field_definitions:
            field_name = f'custom_{field_def.slug}'

            if field_def.field_type == 'checkbox':
                # チェックボックスは on/off で送信される
                value = field_name in self.request.POST
                custom_fields_data[field_def.slug] = value
            elif field_def.field_type == 'multiselect':
                # 複数選択はリストで取得
                values = self.request.POST.getlist(field_name)
                custom_fields_data[field_def.slug] = values
            else:
                # その他のフィールドタイプ
                value = self.request.POST.get(field_name, '')
                if value:
                    custom_fields_data[field_def.slug] = value

        # custom_fieldsフィールドに保存
        if not contractor.custom_fields:
            contractor.custom_fields = {}
        contractor.custom_fields.update(custom_fields_data)

        contractor.save()

        # 成功メッセージ
        contractor_type = form.cleaned_data.get('contractor_type', 'company')
        type_names = {
            'individual': '個人職人',
            'company': '協力会社',
            'material': '資材業者'
        }
        type_name = type_names.get(contractor_type, '協力会社')

        messages.success(self.request, f'{type_name}「{name}」を登録しました。')

        # form.instance を更新して、super().form_valid() がリダイレクトできるようにする
        form.instance = contractor
        return super(CreateView, self).form_valid(form)

    def get_success_url(self):
        # back パラメータがあればそのURLに、なければデフォルトのURLに
        back_url = self.request.GET.get('back')
        if back_url:
            return back_url
        return self.success_url