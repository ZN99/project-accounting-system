"""統合業者管理ビュー"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal

from .models import Project, Contractor


class UnifiedContractorManagementView(LoginRequiredMixin, TemplateView):
    """統合業者管理ダッシュボード"""
    template_name = 'order_management/unified_contractor_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 全業者のカテゴリ別集計
        context['contractor_summary'] = self.get_contractor_summary()

        # 受注業者（is_receiving=True）
        context['receiving_contractors'] = self.get_receiving_contractors()

        # 発注先業者（is_ordering=True）
        context['ordering_contractors'] = self.get_ordering_contractors()

        # 資材屋（is_supplier=True）
        context['suppliers'] = self.get_suppliers()

        # その他業者（is_other=True）
        context['other_contractors'] = self.get_other_contractors()

        # 総合統計
        context['overall_stats'] = self.get_overall_stats()

        return context

    def get_contractor_summary(self):
        """業者カテゴリ別サマリー"""
        return {
            'receiving_count': Contractor.objects.filter(is_receiving=True, is_active=True).count(),
            'ordering_count': Contractor.objects.filter(is_ordering=True, is_active=True).count(),
            'supplier_count': Contractor.objects.filter(is_supplier=True, is_active=True).count(),
            'other_count': Contractor.objects.filter(is_other=True, is_active=True).count(),
            'total_count': Contractor.objects.filter(is_active=True).count(),
            'inactive_count': Contractor.objects.filter(is_active=False).count(),
        }

    def get_receiving_contractors(self):
        """受注業者の情報"""
        contractors = Contractor.objects.filter(
            is_receiving=True,
            is_active=True
        ).order_by('name')[:5]  # 上位5件

        contractor_list = []
        for contractor in contractors:
            project_count = Project.objects.filter(client_name=contractor.name).count()
            total_revenue = Project.objects.filter(client_name=contractor.name).aggregate(
                total=Sum('order_amount')
            )['total'] or Decimal('0')

            contractor_list.append({
                'id': contractor.id,
                'name': contractor.name,
                'specialties': contractor.specialties,
                'project_count': project_count,
                'total_revenue': total_revenue,
                'type': 'receiving'
            })

        return contractor_list

    def get_ordering_contractors(self):
        """発注先業者の情報"""
        contractors = Contractor.objects.filter(
            is_ordering=True,
            is_active=True
        ).order_by('name')[:5]  # 上位5件

        contractor_list = []
        for contractor in contractors:
            project_count = Project.objects.filter(client_name=contractor.name).count()

            contractor_list.append({
                'id': contractor.id,
                'name': contractor.name,
                'specialties': contractor.specialties,
                'project_count': project_count,
                'type': 'ordering'
            })

        return contractor_list

    def get_suppliers(self):
        """資材屋の情報"""
        suppliers = Contractor.objects.filter(
            is_supplier=True,
            is_active=True
        ).order_by('name')[:5]  # 上位5件

        supplier_list = []
        for supplier in suppliers:
            usage_count = Project.objects.filter(client_name=supplier.name).count()

            supplier_list.append({
                'id': supplier.id,
                'name': supplier.name,
                'specialties': supplier.specialties,
                'usage_count': usage_count,
                'type': 'supplier'
            })

        return supplier_list

    def get_other_contractors(self):
        """その他業者の情報"""
        contractors = Contractor.objects.filter(
            is_other=True,
            is_active=True
        ).order_by('name')[:5]  # 上位5件

        contractor_list = []
        for contractor in contractors:
            contractor_list.append({
                'id': contractor.id,
                'name': contractor.name,
                'specialties': contractor.specialties,
                'other_description': contractor.other_description,
                'type': 'other'
            })

        return contractor_list

    def get_overall_stats(self):
        """総合統計"""
        # 今月の新規登録業者数
        this_month_new = Contractor.objects.filter(
            created_at__year=timezone.now().year,
            created_at__month=timezone.now().month
        ).count()

        # 最も多い専門分野（仮集計）
        popular_specialties = Contractor.objects.exclude(
            specialties=''
        ).values_list('specialties', flat=True)

        # 専門分野の出現頻度計算（簡易版）
        specialty_count = {}
        for specialty in popular_specialties:
            if specialty:
                specialty_count[specialty] = specialty_count.get(specialty, 0) + 1

        most_popular_specialty = max(specialty_count.items(), key=lambda x: x[1])[0] if specialty_count else '不明'

        return {
            'this_month_new': this_month_new,
            'most_popular_specialty': most_popular_specialty,
            'total_projects_managed': Project.objects.count(),
            'active_project_count': Project.objects.filter(project_status='完工').count(),
        }