"""業者管理ビュー"""
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from .models import Project
from subcontract_management.models import Contractor


class ContractorDashboardView(LoginRequiredMixin, TemplateView):
    """元請け検索ダッシュボード（開発中）"""
    template_name = 'order_management/contractor_dashboard.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Sum, Q, F
        from .models import ClientCompany
        from datetime import datetime, timedelta
        import json

        context = super().get_context_data(**kwargs)

        # すべての元請け業者を取得
        contractors = ClientCompany.objects.all().order_by('company_name')

        # 各業者に集計データを追加
        contractors_data = []
        total_contractors = 0
        total_projects_count = 0
        total_revenue = 0
        total_cost = 0

        for client_company in contractors:
            # この元請けからの案件を取得
            projects = Project.objects.filter(client_company=client_company)

            # 案件数
            project_count = projects.count()

            # 売上合計（受注額）
            contractor_revenue = projects.aggregate(total=Sum('billing_amount'))['total'] or 0
            contractor_revenue = float(contractor_revenue)

            # 原価合計（発注額）
            contractor_cost = projects.aggregate(total=Sum('order_amount'))['total'] or 0
            contractor_cost = float(contractor_cost)

            # 利益
            profit = contractor_revenue - contractor_cost

            # 利益率
            profit_rate = (profit / contractor_revenue * 100) if contractor_revenue > 0 else 0

            # 業者タグ
            contractor_tags = ['元請け業者']
            if client_company.payment_cycle:
                contractor_tags.append(f'支払い: {client_company.get_payment_cycle_display()}')

            # 月次トレンドデータ（過去12ヶ月）
            monthly_trends = []
            today = datetime.now()
            for i in range(12):
                month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
                month_label = month_start.strftime('%Y/%m')

                # その月の案件
                month_projects = projects.filter(
                    created_at__year=month_start.year,
                    created_at__month=month_start.month
                )

                month_revenue = month_projects.aggregate(total=Sum('billing_amount'))['total'] or 0
                month_revenue = float(month_revenue)
                month_cost = month_projects.aggregate(total=Sum('order_amount'))['total'] or 0
                month_cost = float(month_cost)
                month_profit = month_revenue - month_cost
                month_profit_rate = (month_profit / month_revenue * 100) if month_revenue > 0 else 0

                monthly_trends.insert(0, {
                    'month': month_label,
                    'revenue': month_revenue,
                    'profit': month_profit,
                    'profit_rate': month_profit_rate
                })

            contractor_obj = {
                'id': client_company.id,
                'name': client_company.company_name,
                'contractor_type': 'client',
                'specialties': client_company.address or '',
                'status': 'active' if client_company.is_active else 'inactive',
                'contractor_tags': contractor_tags,
                'project_count': project_count,
                'total_revenue': contractor_revenue,
                'total_cost': contractor_cost,
                'profit': profit,
                'profit_rate': profit_rate,
                'monthly_trends': monthly_trends
            }

            contractors_data.append(contractor_obj)

            # 全体集計
            total_contractors += 1
            total_projects_count += project_count
            total_revenue += contractor_revenue
            total_cost += contractor_cost

        # サマリーデータ
        avg_profit_rate = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0

        summary = {
            'total_contractors': total_contractors,
            'total_projects': total_projects_count,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'avg_profit_rate': avg_profit_rate
        }

        # 月次データ（全体）
        monthly_data = []
        chart_labels = []
        today = datetime.now()
        for i in range(12):
            month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_label = month_start.strftime('%Y/%m')

            month_projects = Project.objects.filter(
                created_at__year=month_start.year,
                created_at__month=month_start.month
            )

            month_revenue = month_projects.aggregate(total=Sum('billing_amount'))['total'] or 0
            month_revenue = float(month_revenue)
            month_cost = month_projects.aggregate(total=Sum('order_amount'))['total'] or 0
            month_cost = float(month_cost)
            month_profit = month_revenue - month_cost
            month_profit_rate = (month_profit / month_revenue * 100) if month_revenue > 0 else 0

            monthly_data.insert(0, {
                'revenue': month_revenue,
                'profit': month_profit,
                'profit_rate': month_profit_rate
            })
            chart_labels.insert(0, month_label)

        context['contractors'] = contractors_data
        context['contractors_json'] = json.dumps(contractors_data)
        context['summary'] = summary
        context['monthly_data_json'] = json.dumps(monthly_data)
        context['chart_labels_json'] = json.dumps(chart_labels)

        return context


class ContractorProjectsView(LoginRequiredMixin, TemplateView):
    """業者別案件一覧"""
    template_name = 'order_management/contractor_projects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor_id = self.kwargs.get('contractor_id')
        contractor = get_object_or_404(Contractor, id=contractor_id)

        # この業者が担当している案件を取得
        projects = Project.objects.filter(
            subcontract__contractor=contractor
        ).distinct().order_by('-created_at')

        context['contractor'] = contractor
        context['projects'] = projects
        return context


class ContractorEditView(LoginRequiredMixin, UpdateView):
    """業者編集"""
    model = Contractor
    template_name = 'order_management/contractor_edit.html'
    fields = [
        'name', 'contractor_type', 'address', 'phone', 'email', 'contact_person',
        'hourly_rate', 'specialties', 'is_active',
        # 支払い情報
        'payment_cycle', 'closing_day', 'payment_offset_months', 'payment_day',
        # 銀行口座情報
        'bank_name', 'branch_name', 'account_type', 'account_number', 'account_holder'
    ]

    def get_success_url(self):
        """保存後のリダイレクト先を取得（元のページに戻る）"""
        # リファラーがあればそこに戻る
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            # 編集ページ自体のURLは除外（無限ループ防止）
            if f'/contractors/{self.object.pk}/edit/' not in referer:
                return referer

        # デフォルトは下請け検索ページ
        return reverse_lazy('subcontract_management:contractor_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # フォームフィールドにBootstrapクラスを追加
        form.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: ○○建設株式会社'
        })
        form.fields['contractor_type'].widget.attrs.update({
            'class': 'form-select'
        })
        form.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 東京都渋谷区...'
        })
        form.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 03-1234-5678'
        })
        form.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: info@example.com'
        })
        form.fields['contact_person'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 山田 太郎'
        })
        form.fields['hourly_rate'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '3000',
            'min': '0',
            'step': '100'
        })
        form.fields['specialties'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '例: 建築工事、内装工事'
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
