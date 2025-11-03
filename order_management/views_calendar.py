"""
施工カレンダー・スケジュール管理ビュー
"""
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
from calendar import monthrange
from .models import Project
import json


class ConstructionCalendarView(LoginRequiredMixin, TemplateView):
    """施工カレンダービュー - 月間工事予定表示"""
    template_name = 'order_management/construction_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 表示月の取得（デフォルトは今月）
        year = int(self.request.GET.get('year', datetime.now().year))
        month = int(self.request.GET.get('month', datetime.now().month))

        context['year'] = year
        context['month'] = month
        context['month_name'] = f'{year}年{month}月'

        # 前月・次月の計算
        if month == 1:
            context['prev_year'] = year - 1
            context['prev_month'] = 12
        else:
            context['prev_year'] = year
            context['prev_month'] = month - 1

        if month == 12:
            context['next_year'] = year + 1
            context['next_month'] = 1
        else:
            context['next_year'] = year
            context['next_month'] = month + 1

        return context


def calendar_events_api(request):
    """カレンダーイベントAPIエンドポイント"""
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # 月の最初と最後の日
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, monthrange(year, month)[1]).date()

    # 表示対象の案件を取得
    # 工事開始日または工事終了日が指定月内にある案件
    projects = Project.objects.filter(
        Q(work_start_date__gte=first_day, work_start_date__lte=last_day) |
        Q(work_end_date__gte=first_day, work_end_date__lte=last_day) |
        Q(work_start_date__lte=first_day, work_end_date__gte=last_day)
    ).select_related('project_manager')

    events = []
    for project in projects:
        # 案件進捗に応じた色分け
        color_map = {
            'ネタ': '#6c757d',  # グレー
            '施工日待ち': '#ffc107',  # 黄色
            '進行中': '#28a745',  # 緑
            '完工': '#007bff',  # 青
            'NG': '#dc3545',  # 赤
        }

        # 工事期間のイベントを作成
        if project.work_start_date and project.work_end_date:
            events.append({
                'id': project.id,
                'title': f'{project.site_name}（{project.work_type}）',
                'start': project.work_start_date.isoformat(),
                'end': (project.work_end_date + timedelta(days=1)).isoformat(),  # FullCalendarは終了日を含まない
                'color': color_map.get(project.project_status, '#6c757d'),
                'extendedProps': {
                    'status': project.project_status,
                    'client': project.client_name,
                    'manager': project.project_manager,
                    'amount': float(project.order_amount) if project.order_amount else 0,
                }
            })
        elif project.work_start_date:
            # 開始日のみの場合は単日イベント
            events.append({
                'id': project.id,
                'title': f'{project.site_name}（{project.work_type}）',
                'start': project.work_start_date.isoformat(),
                'color': color_map.get(project.project_status, '#6c757d'),
                'extendedProps': {
                    'status': project.project_status,
                    'client': project.client_name,
                    'manager': project.project_manager,
                    'amount': float(project.order_amount) if project.order_amount else 0,
                }
            })

    return JsonResponse({'events': events})


class PerformanceMonthlyView(LoginRequiredMixin, TemplateView):
    """月次業績ビュー - 営業担当別パフォーマンス"""
    template_name = 'order_management/performance_monthly.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 表示月の取得
        year = int(self.request.GET.get('year', datetime.now().year))
        month = int(self.request.GET.get('month', datetime.now().month))

        context['year'] = year
        context['month'] = month
        context['month_name'] = f'{year}年{month}月'

        # 前月・次月の計算
        if month == 1:
            context['prev_year'] = year - 1
            context['prev_month'] = 12
        else:
            context['prev_year'] = year
            context['prev_month'] = month - 1

        if month == 12:
            context['next_year'] = year + 1
            context['next_month'] = 1
        else:
            context['next_year'] = year
            context['next_month'] = month + 1

        return context


def performance_monthly_api(request):
    """月次業績データAPIエンドポイント"""
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # 月の最初と最後の日
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, monthrange(year, month)[1]).date()

    # 指定月に完工した案件を取得
    projects = Project.objects.filter(
        work_end_date__gte=first_day,
        work_end_date__lte=last_day,
        project_status__in=['完工', '進行中', '施工日待ち']
    ).select_related('project_manager')

    # 担当者別の集計
    performance_by_manager = {}
    for project in projects:
        manager = project.project_manager
        if manager not in performance_by_manager:
            performance_by_manager[manager] = {
                'manager': manager,
                'project_count': 0,
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'projects': []
            }

        # 案件の利益計算
        revenue = float(project.order_amount) if project.order_amount else 0
        cost = float(project.total_cost) if hasattr(project, 'total_cost') else 0
        profit = revenue - cost

        performance_by_manager[manager]['project_count'] += 1
        performance_by_manager[manager]['total_revenue'] += revenue
        performance_by_manager[manager]['total_cost'] += cost
        performance_by_manager[manager]['total_profit'] += profit
        performance_by_manager[manager]['projects'].append({
            'id': project.id,
            'site_name': project.site_name,
            'status': project.project_status,
            'revenue': revenue,
            'cost': cost,
            'profit': profit,
        })

    # リスト形式に変換
    performance_list = list(performance_by_manager.values())

    # 利益順にソート
    performance_list.sort(key=lambda x: x['total_profit'], reverse=True)

    return JsonResponse({'performance': performance_list})


class GanttChartView(LoginRequiredMixin, TemplateView):
    """ガントチャートビュー - 案件の工事期間を視覚化"""
    template_name = 'order_management/gantt_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 表示期間の取得（デフォルトは今月から3ヶ月）
        year = int(self.request.GET.get('year', datetime.now().year))
        month = int(self.request.GET.get('month', datetime.now().month))

        context['year'] = year
        context['month'] = month
        context['month_name'] = f'{year}年{month}月'

        return context


def gantt_data_api(request):
    """ガントチャートデータAPIエンドポイント"""
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # 表示期間（指定月から3ヶ月間）
    start_date = datetime(year, month, 1).date()
    end_month = month + 3
    end_year = year
    if end_month > 12:
        end_year += 1
        end_month -= 12
    end_date = datetime(end_year, end_month, monthrange(end_year, end_month)[1]).date()

    # 表示期間内に工事がある案件を取得
    projects = Project.objects.filter(
        Q(work_start_date__lte=end_date, work_end_date__gte=start_date) |
        Q(work_start_date__isnull=False, work_end_date__isnull=True, work_start_date__lte=end_date)
    ).exclude(
        project_status='NG'
    ).select_related('project_manager').order_by('work_start_date')

    # ガントチャート用のデータ形式に変換
    tasks = []
    for project in projects:
        if not project.work_start_date:
            continue

        # 終了日が未定の場合は開始日から30日後を仮の終了日とする
        end_date_display = project.work_end_date if project.work_end_date else project.work_start_date + timedelta(days=30)

        # 進捗率の計算
        progress = 0
        if project.project_status == '完工':
            progress = 100
        elif project.project_status == '進行中':
            if project.work_start_date and project.work_end_date:
                today = datetime.now().date()
                total_days = (project.work_end_date - project.work_start_date).days
                elapsed_days = (today - project.work_start_date).days
                if total_days > 0:
                    progress = min(100, max(0, int((elapsed_days / total_days) * 100)))
                else:
                    progress = 50
            else:
                progress = 50
        elif project.project_status == '施工日待ち':
            progress = 0

        # ステータス別の色
        color_map = {
            'ネタ': '#6c757d',
            '施工日待ち': '#ffc107',
            '進行中': '#28a745',
            '完工': '#007bff',
        }

        tasks.append({
            'id': str(project.id),
            'name': f'{project.site_name}（{project.work_type}）',
            'start': project.work_start_date.isoformat(),
            'end': end_date_display.isoformat(),
            'progress': progress,
            'custom_class': project.project_status,
            'dependencies': '',
            'project_id': project.id,
            'status': project.project_status,
            'manager': project.project_manager,
            'client': project.client_name,
            'amount': float(project.order_amount) if project.order_amount else 0,
            'color': color_map.get(project.project_status, '#6c757d'),
        })

    return JsonResponse({'tasks': tasks})
