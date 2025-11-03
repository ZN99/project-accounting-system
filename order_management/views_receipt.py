from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import CashFlowTransaction
from .user_roles import has_any_role, UserRole
import calendar
from decimal import Decimal
from .utils import safe_int


class ReceiptDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'order_management/receipt_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # 経理・役員のみアクセス可能
        if not has_any_role(request.user, [UserRole.ACCOUNTING, UserRole.EXECUTIVE]):
            raise PermissionDenied("入金管理画面へのアクセス権限がありません。")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 現在の月を取得（デフォルト）
        now = timezone.now()
        year = safe_int(self.request.GET.get('year', now.year))
        month = safe_int(self.request.GET.get('month', now.month))
        status_filter = self.request.GET.get('status', 'all')

        # 月の開始日と終了日
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()

        # 入金トランザクション（revenue_cash）のみ取得
        base_query = CashFlowTransaction.objects.filter(
            transaction_type='revenue_cash',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).select_related('project')

        # 入金状況による絞り込み
        today = timezone.now().date()
        if status_filter == 'received':
            # 入金済み（is_planned=False）
            base_query = base_query.filter(is_planned=False)
        elif status_filter == 'pending':
            # 入金待ち（is_planned=True、まだ未来）
            base_query = base_query.filter(is_planned=True, transaction_date__gte=today)
        elif status_filter == 'overdue':
            # 遅延（is_planned=True、過去日付）
            base_query = base_query.filter(is_planned=True, transaction_date__lt=today)

        receipt_transactions = base_query.order_by('transaction_date', 'project__client_name')

        # 顧客別の集計データ
        client_summary = {}

        # 今月の入金統計
        monthly_receipt_stats = {
            'pending_amount': Decimal('0'),    # 入金待ち
            'received_amount': Decimal('0'),   # 入金済み
            'overdue_amount': Decimal('0'),    # 遅延
            'total_receipt': Decimal('0')      # 今月の総入金予定額
        }

        for transaction in receipt_transactions:
            # プロジェクトから顧客名を取得
            client_name = transaction.project.client_name if transaction.project else '不明な顧客'

            if client_name not in client_summary:
                client_summary[client_name] = {
                    'client_name': client_name,
                    'transactions': [],
                    'total_amount': Decimal('0'),
                    'received_amount': Decimal('0'),
                    'pending_amount': Decimal('0'),
                    'overdue_amount': Decimal('0'),
                    'transaction_count': 0
                }

            amount = transaction.amount

            client_summary[client_name]['transactions'].append(transaction)
            client_summary[client_name]['total_amount'] += amount
            client_summary[client_name]['transaction_count'] += 1

            # 入金状況別の集計
            if not transaction.is_planned:
                # 実績入金
                client_summary[client_name]['received_amount'] += amount
                monthly_receipt_stats['received_amount'] += amount
            elif transaction.transaction_date < today:
                # 予定だったが過ぎている = 遅延
                client_summary[client_name]['overdue_amount'] += amount
                monthly_receipt_stats['overdue_amount'] += amount
            else:
                # 今後の入金予定
                client_summary[client_name]['pending_amount'] += amount
                monthly_receipt_stats['pending_amount'] += amount

            monthly_receipt_stats['total_receipt'] += amount

        # 統計情報
        stats = {
            'total_clients': len(client_summary),
            'total_transactions': receipt_transactions.count(),
            'total_receipt': monthly_receipt_stats['total_receipt'],
            'pending_amount': monthly_receipt_stats['pending_amount'],
            'received_amount': monthly_receipt_stats['received_amount'],
            'overdue_amount': monthly_receipt_stats['overdue_amount'],
        }

        # 入金状況の選択肢
        receipt_status_choices = [
            ('all', 'すべて'),
            ('pending', '入金待ち'),
            ('received', '入金済み'),
            ('overdue', '遅延'),
        ]

        # 前月・次月のナビゲーション
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        context.update({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'status_filter': status_filter,
            'receipt_status_choices': receipt_status_choices,
            'client_summary': client_summary,
            'receipt_transactions': receipt_transactions,
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'today': today,
        })

        return context
