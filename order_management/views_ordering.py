"""発注業務ダッシュボード関連のビュー"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Project, Contractor


class OrderingDashboardView(LoginRequiredMixin, TemplateView):
    """発注業務ダッシュボード"""
    template_name = 'order_management/ordering_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 現在の日付情報
        now = timezone.now()
        current_year = now.year
        current_month = now.month

        # 発注業務のサマリー情報
        context['summary'] = self.get_ordering_summary()

        # 外注業者の情報
        context['external_contractors'] = self.get_external_contractors()

        # 資材屋の情報
        context['suppliers'] = self.get_suppliers()

        # 社内リソースの情報（現在のプロジェクトから）
        context['internal_resources'] = self.get_internal_resources()

        # 発注統計
        context['ordering_stats'] = self.get_ordering_statistics()

        return context

    def get_ordering_summary(self):
        """発注業務のサマリー情報を取得"""
        # 外注業者数
        external_contractor_count = Contractor.objects.filter(
            is_ordering=True,
            is_active=True
        ).count()

        # 資材屋数
        supplier_count = Contractor.objects.filter(
            is_supplier=True,
            is_active=True
        ).count()

        # 今月の発注予定案件数（仮：受注済み案件をベース）
        this_month_orders = Project.objects.filter(
            created_at__year=timezone.now().year,
            created_at__month=timezone.now().month,
            project_status='完工'
        ).count()

        # 総発注金額（仮：今月の見積金額合計）
        total_order_amount = Project.objects.filter(
            created_at__year=timezone.now().year,
            created_at__month=timezone.now().month,
            project_status='完工'
        ).aggregate(
            total=Sum('order_amount')
        )['total'] or Decimal('0')

        return {
            'external_contractor_count': external_contractor_count,
            'supplier_count': supplier_count,
            'this_month_orders': this_month_orders,
            'total_order_amount': total_order_amount,
        }

    def get_external_contractors(self):
        """外注業者の情報を取得"""
        contractors = Contractor.objects.filter(
            is_ordering=True,
            is_active=True
        ).order_by('name')

        contractor_list = []
        for contractor in contractors:
            # この業者に発注した案件数を計算
            project_count = Project.objects.filter(
                client_name=contractor.name
            ).count()

            # 発注金額合計
            total_amount = Project.objects.filter(
                client_name=contractor.name
            ).aggregate(
                total=Sum('order_amount')
            )['total'] or Decimal('0')

            contractor_list.append({
                'id': contractor.id,
                'name': contractor.name,
                'specialties': contractor.specialties,
                'contact_person': contractor.contact_person,
                'phone': contractor.phone,
                'email': contractor.email,
                'project_count': project_count,
                'total_amount': total_amount,
            })

        return contractor_list

    def get_suppliers(self):
        """資材屋の情報を取得"""
        suppliers = Contractor.objects.filter(
            is_supplier=True,
            is_active=True
        ).order_by('name')

        supplier_list = []
        for supplier in suppliers:
            # 資材屋の利用実績を計算（仮：専門分野で判断）
            related_projects = Project.objects.filter(
                client_name=supplier.name
            ).count()

            supplier_list.append({
                'id': supplier.id,
                'name': supplier.name,
                'specialties': supplier.specialties,
                'contact_person': supplier.contact_person,
                'phone': supplier.phone,
                'email': supplier.email,
                'usage_count': related_projects,
            })

        return supplier_list

    def get_internal_resources(self):
        """社内リソース情報を取得（プロジェクトの担当者ベース）"""
        # プロジェクトの担当者から社内リソースを抽出
        internal_staff = Project.objects.values('project_manager').annotate(
            project_count=Count('id'),
            total_amount=Sum('order_amount')
        ).filter(
            project_manager__isnull=False,
            project_manager__gt=''
        ).order_by('-project_count')

        return list(internal_staff)

    def get_ordering_statistics(self):
        """発注統計情報を取得"""
        # 過去6ヶ月の発注推移
        monthly_stats = []
        now = timezone.now()

        for i in range(6):
            month_date = now - timedelta(days=30 * (5 - i))
            year = month_date.year
            month = month_date.month

            # その月の発注案件数と金額
            month_projects = Project.objects.filter(
                created_at__year=year,
                created_at__month=month,
                project_status='完工'
            )

            project_count = month_projects.count()
            total_amount = month_projects.aggregate(
                total=Sum('order_amount')
            )['total'] or Decimal('0')

            monthly_stats.append({
                'month': f'{year}/{month:02d}',
                'project_count': project_count,
                'total_amount': float(total_amount),
            })

        return {
            'monthly_stats': monthly_stats,
        }


class ExternalContractorManagementView(LoginRequiredMixin, TemplateView):
    """外注業者管理ビュー"""
    template_name = 'order_management/external_contractor_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 外注業者一覧
        contractors = Contractor.objects.filter(
            is_ordering=True
        ).order_by('-is_active', 'name')

        context['contractors'] = contractors
        context['page_title'] = '外注業者管理'

        return context


class SupplierManagementView(LoginRequiredMixin, TemplateView):
    """資材屋管理ビュー"""
    template_name = 'order_management/supplier_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 資材屋一覧
        suppliers = Contractor.objects.filter(
            is_supplier=True
        ).order_by('-is_active', 'name')

        context['suppliers'] = suppliers
        context['page_title'] = '資材屋管理'

        return context