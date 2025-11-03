"""業者新規作成ビュー"""
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

from .models import Contractor


class ContractorCreateView(LoginRequiredMixin, CreateView):
    """業者新規作成ビュー"""
    model = Contractor
    template_name = 'order_management/contractor_create.html'
    fields = [
        'name', 'address', 'phone', 'email', 'contact_person',
        'specialties', 'is_ordering', 'is_receiving', 'is_supplier',
        'is_other', 'other_description', 'is_active'
    ]
    success_url = reverse_lazy('order_management:ordering_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # URLパラメータから業者タイプを取得
        contractor_type = self.request.GET.get('type', '')

        # タイプに応じたページタイトルとデフォルト値を設定
        if contractor_type == 'is_ordering':
            context['page_title'] = '新規外注業者追加'
            context['contractor_type'] = 'external'
            context['default_is_ordering'] = True
        elif contractor_type == 'is_supplier':
            context['page_title'] = '新規資材屋追加'
            context['contractor_type'] = 'supplier'
            context['default_is_supplier'] = True
        elif contractor_type == 'is_receiving':
            context['page_title'] = '新規受注業者追加'
            context['contractor_type'] = 'receiving'
            context['default_is_receiving'] = True
        else:
            context['page_title'] = '新規業者追加'
            context['contractor_type'] = 'general'

        context['back_url'] = self.request.GET.get('back', reverse_lazy('order_management:ordering_dashboard'))

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
        form.fields['specialties'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '専門分野を入力してください（例：建築工事、電気工事）'
        })
        form.fields['is_ordering'].widget.attrs.update({
            'class': 'form-check-input'
        })
        form.fields['is_receiving'].widget.attrs.update({
            'class': 'form-check-input'
        })
        form.fields['is_supplier'].widget.attrs.update({
            'class': 'form-check-input'
        })
        form.fields['is_other'].widget.attrs.update({
            'class': 'form-check-input'
        })
        form.fields['other_description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'その他の内容を入力してください'
        })
        form.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input'
        })

        return form

    def get_initial(self):
        initial = super().get_initial()

        # URLパラメータから業者タイプを取得してデフォルト値を設定
        contractor_type = self.request.GET.get('type', '')

        if contractor_type == 'is_ordering':
            initial['is_ordering'] = True
        elif contractor_type == 'is_supplier':
            initial['is_supplier'] = True
        elif contractor_type == 'is_receiving':
            initial['is_receiving'] = True

        # デフォルトでアクティブに設定
        initial['is_active'] = True

        return initial

    def form_valid(self, form):
        # 業者名の重複チェック
        name = form.cleaned_data['name']
        if Contractor.objects.filter(name=name).exists():
            messages.error(self.request, f'業者名「{name}」は既に登録されています。')
            return self.form_invalid(form)

        # 成功メッセージ
        contractor_type = self.request.GET.get('type', '')
        type_name = ''
        if contractor_type == 'is_ordering':
            type_name = '外注業者'
        elif contractor_type == 'is_supplier':
            type_name = '資材屋'
        elif contractor_type == 'is_receiving':
            type_name = '受注業者'
        else:
            type_name = '業者'

        messages.success(self.request, f'{type_name}「{name}」を登録しました。')

        return super().form_valid(form)

    def get_success_url(self):
        # back パラメータがあればそのURLに、なければデフォルトのURLに
        back_url = self.request.GET.get('back')
        if back_url:
            return back_url
        return self.success_url