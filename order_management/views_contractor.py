"""業者管理ダッシュボード関連のビュー"""
from django.views.generic import TemplateView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import Project, Contractor
from django.shortcuts import get_object_or_404


class ContractorDashboardView(LoginRequiredMixin, TemplateView):
    """業者管理ダッシュボード"""
    template_name = 'order_management/contractor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 現在の日付情報
        now = timezone.now()
        current_year = now.year
        current_month = now.month

        # 過去12ヶ月の期間を計算
        start_date = now - timedelta(days=365)

        # 全ての受注業者を取得（仮のデータも含む）
        contractors = self.get_contractors_with_metrics()

        # ダッシュボードのサマリー情報
        context['summary'] = self.get_summary_metrics(contractors)

        # 業者ごとの詳細データ
        context['contractors'] = contractors

        # 月別の推移データ（グラフ用）
        context['monthly_data'] = self.get_monthly_metrics(start_date, now)

        # グラフ用のラベルとデータセット
        context['chart_labels'] = self.get_chart_labels(start_date, now)

        # JavaScript用にJSON形式でも提供（Decimalをfloatに変換）
        contractors_json = []
        for c in contractors:
            contractor_dict = {
                'id': str(c['id']),  # IDを文字列に変換
                'name': c['name'],
                'project_count': c['project_count'],
                'total_revenue': float(c['total_revenue']) if c['total_revenue'] else 0,
                'total_cost': float(c['total_cost']) if c['total_cost'] else 0,
                'profit': float(c['profit']) if c['profit'] else 0,
                'profit_rate': float(c['profit_rate']) if c['profit_rate'] else 0,
                'specialties': c['specialties'],
                'status': c['status'],
                'monthly_trends': c['monthly_trends']
            }
            contractors_json.append(contractor_dict)

        context['contractors_json'] = json.dumps(contractors_json)
        context['monthly_data_json'] = json.dumps(context['monthly_data'])
        context['chart_labels_json'] = json.dumps(context['chart_labels'])

        return context

    def get_contractors_with_metrics(self):
        """業者ごとの指標を計算"""
        contractors_data = []

        # 実際のContractorモデルから取得（受注業者のみ）
        contractors = Contractor.objects.filter(is_receiving=True).order_by('name')

        for contractor in contractors:
            # この業者の全プロジェクトを取得（client_nameフィールドで検索）
            projects = Project.objects.filter(client_name=contractor.name)

            # 集計
            total_projects = projects.count()
            total_revenue = projects.aggregate(
                total=Coalesce(Sum('order_amount'), Decimal('0'))
            )['total']

            # 原価計算（仮: 売上の60-80%をランダムに設定）
            import random
            cost_ratio = Decimal(str(random.uniform(0.6, 0.8)))
            total_cost = total_revenue * cost_ratio if total_revenue else Decimal('0')

            # 利益計算
            profit = total_revenue - total_cost if total_revenue else Decimal('0')
            profit_rate = (profit / total_revenue * 100) if total_revenue and total_revenue > 0 else Decimal('0')

            # 業者タグを取得
            contractor_tags = []
            if contractor.is_ordering:
                contractor_tags.append('発注業者')
            if contractor.is_receiving:
                contractor_tags.append('受注業者')
            if contractor.is_supplier:
                contractor_tags.append('資材屋')
            if contractor.is_other:
                contractor_tags.append('その他')

            contractors_data.append({
                'id': contractor.id,
                'name': contractor.name,
                'project_count': total_projects,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'profit': profit,
                'profit_rate': profit_rate,
                'specialties': contractor.specialties,
                'status': 'active' if contractor.is_active else 'inactive',
                'contractor_tags': contractor_tags,
                'monthly_trends': self.get_contractor_monthly_trends(contractor)
            })

        # ダミーデータを追加（デモ用）
        if len(contractors_data) < 5:
            dummy_contractors = [
                {
                    'id': 'dummy_1',
                    'name': '山田建設',
                    'project_count': 45,
                    'total_revenue': Decimal('125000000'),
                    'total_cost': Decimal('95000000'),
                    'profit': Decimal('30000000'),
                    'profit_rate': Decimal('24.0'),
                    'specialties': '建築一般',
                    'status': 'active',
                    'contractor_tags': ['受注業者'],
                    'monthly_trends': self.get_dummy_monthly_trends()
                },
                {
                    'id': 'dummy_2',
                    'name': '鈴木電気工事',
                    'project_count': 32,
                    'total_revenue': Decimal('68000000'),
                    'total_cost': Decimal('51000000'),
                    'profit': Decimal('17000000'),
                    'profit_rate': Decimal('25.0'),
                    'specialties': '電気工事',
                    'status': 'active',
                    'contractor_tags': ['受注業者', '資材屋'],
                    'monthly_trends': self.get_dummy_monthly_trends()
                },
                {
                    'id': 'dummy_3',
                    'name': '佐藤設備',
                    'project_count': 28,
                    'total_revenue': Decimal('52000000'),
                    'total_cost': Decimal('40560000'),
                    'profit': Decimal('11440000'),
                    'profit_rate': Decimal('22.0'),
                    'specialties': '給排水設備',
                    'status': 'active',
                    'contractor_tags': ['受注業者'],
                    'monthly_trends': self.get_dummy_monthly_trends()
                },
                {
                    'id': 'dummy_4',
                    'name': '高橋塗装',
                    'project_count': 18,
                    'total_revenue': Decimal('35000000'),
                    'total_cost': Decimal('28000000'),
                    'profit': Decimal('7000000'),
                    'profit_rate': Decimal('20.0'),
                    'specialties': '塗装工事',
                    'status': 'active',
                    'contractor_tags': ['発注業者', '受注業者'],
                    'monthly_trends': self.get_dummy_monthly_trends()
                },
                {
                    'id': 'dummy_5',
                    'name': '中村内装',
                    'project_count': 15,
                    'total_revenue': Decimal('28000000'),
                    'total_cost': Decimal('21840000'),
                    'profit': Decimal('6160000'),
                    'profit_rate': Decimal('22.0'),
                    'specialties': '内装工事',
                    'status': 'active',
                    'contractor_tags': ['その他'],
                    'monthly_trends': self.get_dummy_monthly_trends()
                }
            ]

            # 既存のデータが少ない場合はダミーデータを追加
            for dummy in dummy_contractors[len(contractors_data):]:
                contractors_data.append(dummy)

        # 売上高順でソート
        contractors_data.sort(key=lambda x: x['total_revenue'] or 0, reverse=True)

        return contractors_data

    def get_contractor_monthly_trends(self, contractor):
        """業者の月別推移データを取得"""
        now = timezone.now()
        monthly_data = []

        for i in range(12):
            month_date = now - timedelta(days=30 * (11 - i))
            year = month_date.year
            month = month_date.month

            # その月のプロジェクトを集計
            month_projects = Project.objects.filter(
                client_name=contractor.name,
                created_at__year=year,
                created_at__month=month
            )

            revenue = month_projects.aggregate(
                total=Coalesce(Sum('order_amount'), Decimal('0'))
            )['total']

            # 仮の原価率
            cost_ratio = Decimal('0.7')
            cost = revenue * cost_ratio if revenue else Decimal('0')
            profit = revenue - cost if revenue else Decimal('0')
            profit_rate = (profit / revenue * 100) if revenue and revenue > 0 else Decimal('0')

            monthly_data.append({
                'month': f'{year}/{month:02d}',
                'revenue': float(revenue),
                'profit': float(profit),
                'profit_rate': float(profit_rate)
            })

        return monthly_data

    def get_dummy_monthly_trends(self):
        """ダミーの月別推移データ"""
        import random
        now = timezone.now()
        monthly_data = []

        for i in range(12):
            month_date = now - timedelta(days=30 * (11 - i))

            # ランダムな値を生成
            revenue = random.uniform(5000000, 15000000)
            profit_rate = random.uniform(18, 28)
            profit = revenue * profit_rate / 100

            monthly_data.append({
                'month': f'{month_date.year}/{month_date.month:02d}',
                'revenue': revenue,
                'profit': profit,
                'profit_rate': profit_rate
            })

        return monthly_data

    def get_summary_metrics(self, contractors):
        """全体のサマリー情報を計算"""
        total_revenue = sum(c['total_revenue'] for c in contractors if c['total_revenue'])
        total_profit = sum(c['profit'] for c in contractors if c['profit'])
        total_projects = sum(c['project_count'] for c in contractors)
        avg_profit_rate = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'total_contractors': len(contractors),
            'total_projects': total_projects,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'avg_profit_rate': avg_profit_rate,
            'best_performer': max(contractors, key=lambda x: x['profit_rate']) if contractors else None,
            'highest_revenue': max(contractors, key=lambda x: x['total_revenue'] or 0) if contractors else None
        }

    def get_monthly_metrics(self, start_date, end_date):
        """月別の全体推移データ"""
        monthly_metrics = []
        current_date = start_date

        while current_date <= end_date:
            year = current_date.year
            month = current_date.month

            # その月の全プロジェクトを集計
            month_projects = Project.objects.filter(
                created_at__year=year,
                created_at__month=month
            )

            revenue = month_projects.aggregate(
                total=Coalesce(Sum('order_amount'), Decimal('0'))
            )['total']

            # 仮の集計値
            cost_ratio = Decimal('0.72')
            cost = revenue * cost_ratio if revenue else Decimal('0')
            profit = revenue - cost if revenue else Decimal('0')
            profit_rate = (profit / revenue * 100) if revenue and revenue > 0 else Decimal('0')

            monthly_metrics.append({
                'month': f'{year}/{month:02d}',
                'revenue': float(revenue),
                'cost': float(cost),
                'profit': float(profit),
                'profit_rate': float(profit_rate),
                'project_count': month_projects.count()
            })

            # 次の月へ
            if month == 12:
                current_date = current_date.replace(year=year + 1, month=1)
            else:
                current_date = current_date.replace(month=month + 1)

        return monthly_metrics

    def get_chart_labels(self, start_date, end_date):
        """グラフ用のラベルを生成"""
        labels = []
        current_date = start_date

        while current_date <= end_date:
            labels.append(f'{current_date.year}/{current_date.month:02d}')

            # 次の月へ
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        return labels


class ContractorProjectsView(LoginRequiredMixin, ListView):
    """業者別プロジェクト一覧"""
    model = Project
    template_name = 'order_management/contractor_projects.html'
    context_object_name = 'projects'
    paginate_by = 20

    def get_queryset(self):
        contractor_id = self.kwargs['contractor_id']
        contractor = get_object_or_404(Contractor, pk=contractor_id)
        return Project.objects.filter(client_name=contractor.name).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor_id = self.kwargs['contractor_id']
        contractor = get_object_or_404(Contractor, pk=contractor_id)
        context['contractor'] = contractor

        # この業者の統計情報
        projects = self.get_queryset()
        context['stats'] = {
            'total_projects': projects.count(),
            'total_revenue': projects.aggregate(
                total=Coalesce(Sum('order_amount'), Decimal('0'))
            )['total'],
            'active_projects': projects.filter(project_status='完工').count(),
            'completed_projects': projects.filter(work_end_completed=True).count(),
        }

        # 最近の活動
        context['recent_projects'] = projects[:5]

        # 月別統計（直近6ヶ月）
        monthly_stats = []
        now = timezone.now()
        for i in range(6):
            month_date = now - timedelta(days=30 * i)
            month_projects = projects.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            )
            monthly_stats.append({
                'month': month_date.strftime('%Y/%m'),
                'count': month_projects.count(),
                'revenue': month_projects.aggregate(
                    total=Coalesce(Sum('order_amount'), Decimal('0'))
                )['total']
            })

        context['monthly_stats'] = reversed(monthly_stats)

        return context


class ContractorEditView(LoginRequiredMixin, UpdateView):
    """業者編集ビュー"""
    model = Contractor
    template_name = 'order_management/contractor_edit.html'
    fields = [
        'name', 'address', 'phone', 'email', 'contact_person',
        'specialties', 'is_ordering', 'is_receiving', 'is_supplier',
        'is_other', 'other_description', 'is_active'
    ]
    success_url = '/orders/contractor-dashboard/'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # フォームフィールドにBootstrapクラスを追加
        form.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '業者名を入力してください'
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '業者情報編集'
        return context

    def form_valid(self, form):
        messages = __import__('django.contrib.messages', fromlist=['messages'])
        messages.success(self.request, f'{form.instance.name}の情報を更新しました。')
        return super().form_valid(form)