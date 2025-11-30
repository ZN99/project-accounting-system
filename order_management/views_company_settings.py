"""
会社設定ビュー
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import CompanySettings


class CompanySettingsView(LoginRequiredMixin, TemplateView):
    """会社設定画面"""
    template_name = 'order_management/company_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = CompanySettings.get_settings()
        return context


@require_http_methods(["POST"])
@csrf_exempt
def update_company_settings_api(request):
    """会社設定を更新するAPI"""
    try:
        data = json.loads(request.body)
        settings = CompanySettings.get_settings()

        # 自社情報
        if 'company_name' in data:
            settings.company_name = data['company_name']
        if 'company_address' in data:
            settings.company_address = data['company_address']
        if 'company_phone' in data:
            settings.company_phone = data['company_phone']
        if 'company_fax' in data:
            settings.company_fax = data['company_fax']
        if 'company_email' in data:
            settings.company_email = data['company_email']
        if 'company_representative' in data:
            settings.company_representative = data['company_representative']

        # PDF設定
        if 'purchase_order_remarks' in data:
            settings.purchase_order_remarks = data['purchase_order_remarks']
        if 'invoice_remarks' in data:
            settings.invoice_remarks = data['invoice_remarks']

        settings.save()

        return JsonResponse({
            'success': True,
            'message': '設定を保存しました'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '無効なJSONデータです'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
