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


class PaymentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'order_management/payment_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # 経理・役員のみアクセス可能
        if not has_any_role(request.user, [UserRole.ACCOUNTING, UserRole.EXECUTIVE]):
            raise PermissionDenied("出金管理画面へのアクセス権限がありません。")
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

        # 出金トランザクション（expense_cash）のみ取得
        base_query = CashFlowTransaction.objects.filter(
            transaction_type='expense_cash',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).select_related('project')

        # 支払い状況による絞り込み
        today = timezone.now().date()
        if status_filter == 'executed':
            # 支払済み（is_planned=False）
            base_query = base_query.filter(is_planned=False)
        elif status_filter == 'scheduled':
            # 支払予定（is_planned=True、まだ未来）
            base_query = base_query.filter(is_planned=True, transaction_date__gte=today)
        elif status_filter == 'overdue':
            # 遅延（is_planned=True、過去日付）
            base_query = base_query.filter(is_planned=True, transaction_date__lt=today)

        payment_transactions = base_query.order_by('transaction_date', 'description')

        # 支払先別の集計データ
        payee_summary = {}

        # 今月の出金統計
        monthly_payment_stats = {
            'scheduled_amount': Decimal('0'),  # 支払予定
            'executed_amount': Decimal('0'),   # 支払済み
            'overdue_amount': Decimal('0'),    # 遅延
            'total_payment': Decimal('0')      # 今月の総出金予定額
        }

        # 詳細リスト用のデータ
        paid_list = []          # 今月振り込み済みリスト
        pending_list = []       # 今月振り込み予定リスト（未支払）

        for transaction in payment_transactions:
            # descriptionから支払先を抽出（フォーマット: "{業者名} - {説明}"）
            payee_name = '不明な支払先'
            if transaction.description and ' - ' in transaction.description:
                payee_name = transaction.description.split(' - ')[0]
            elif transaction.description:
                payee_name = transaction.description

            if payee_name not in payee_summary:
                payee_summary[payee_name] = {
                    'payee_name': payee_name,
                    'transactions': [],
                    'total_amount': Decimal('0'),
                    'paid_amount': Decimal('0'),
                    'pending_amount': Decimal('0'),
                    'overdue_amount': Decimal('0'),
                    'transaction_count': 0
                }

            amount = transaction.amount

            payee_summary[payee_name]['transactions'].append(transaction)
            payee_summary[payee_name]['total_amount'] += amount
            payee_summary[payee_name]['transaction_count'] += 1

            # 支払い状況別の集計
            if not transaction.is_planned:
                # 実績支払
                payee_summary[payee_name]['paid_amount'] += amount
                monthly_payment_stats['executed_amount'] += amount

                paid_list.append({
                    'payee_name': payee_name,
                    'description': transaction.description,
                    'amount': amount,
                    'payment_date': transaction.transaction_date,
                    'project': transaction.project,
                    'transaction': transaction
                })
            elif transaction.transaction_date < today:
                # 予定だったが過ぎている = 遅延
                payee_summary[payee_name]['overdue_amount'] += amount
                monthly_payment_stats['overdue_amount'] += amount

                pending_list.append({
                    'payee_name': payee_name,
                    'description': transaction.description,
                    'amount': amount,
                    'payment_date': transaction.transaction_date,
                    'project': transaction.project,
                    'transaction': transaction,
                    'is_overdue': True
                })
            else:
                # 今後の支払予定
                payee_summary[payee_name]['pending_amount'] += amount
                monthly_payment_stats['scheduled_amount'] += amount

                pending_list.append({
                    'payee_name': payee_name,
                    'description': transaction.description,
                    'amount': amount,
                    'payment_date': transaction.transaction_date,
                    'project': transaction.project,
                    'transaction': transaction,
                    'is_overdue': False
                })

            monthly_payment_stats['total_payment'] += amount

        # リストをソート
        paid_list.sort(key=lambda x: x['payment_date'], reverse=True)
        pending_list.sort(key=lambda x: x['payment_date'])

        # 統計情報
        stats = {
            'total_payees': len(payee_summary),
            'total_transactions': payment_transactions.count(),
            'total_payment': monthly_payment_stats['total_payment'],
            'scheduled_amount': monthly_payment_stats['scheduled_amount'],
            'executed_amount': monthly_payment_stats['executed_amount'],
            'overdue_amount': monthly_payment_stats['overdue_amount'],
            'paid_count': len([x for x in paid_list]),
            'pending_count': len([x for x in pending_list]),
        }

        # 支払い状況の選択肢
        payment_status_choices = [
            ('all', 'すべて'),
            ('scheduled', '支払予定'),
            ('executed', '支払済み'),
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
            'payment_status_choices': payment_status_choices,
            'payee_summary': payee_summary,
            'payment_transactions': payment_transactions,
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
            'paid_list': paid_list,
            'pending_list': pending_list,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'today': today,
        })

        return context
