"""
レポート管理Views - Phase 3

レポート生成・閲覧・ダウンロード機能を提供します。
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView, DeleteView
from django.http import JsonResponse, FileResponse, Http404
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from datetime import datetime, date
import os

from .models import Report, Project, ForecastScenario
from .report_utils import (
    generate_monthly_report,
    generate_project_report,
    generate_cashflow_report,
    generate_forecast_report
)
from .pdf_utils import generate_pdf_report
from .utils import safe_int


class ReportDashboardView(LoginRequiredMixin, TemplateView):
    """レポートダッシュボード"""
    template_name = 'order_management/report_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 最近のレポート
        recent_reports = Report.objects.all().order_by('-generated_date')[:10]

        # レポートタイプ別集計
        report_counts = {
            'monthly': Report.objects.filter(report_type='monthly').count(),
            'project': Report.objects.filter(report_type='project').count(),
            'cashflow': Report.objects.filter(report_type='cashflow').count(),
            'forecast': Report.objects.filter(report_type='forecast').count(),
        }

        context['recent_reports'] = recent_reports
        context['report_counts'] = report_counts

        return context


class ReportListView(LoginRequiredMixin, ListView):
    """レポート一覧"""
    model = Report
    template_name = 'order_management/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        queryset = Report.objects.all().order_by('-generated_date')

        # フィルタリング
        report_type = self.request.GET.get('type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_type'] = self.request.GET.get('type', '')
        return context


class ReportDetailView(LoginRequiredMixin, DetailView):
    """レポート詳細"""
    model = Report
    template_name = 'order_management/report_detail.html'
    context_object_name = 'report'


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    """レポート削除"""
    model = Report
    template_name = 'order_management/report_confirm_delete.html'
    success_url = reverse_lazy('order_management:report_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'レポートを削除しました')
        return super().delete(request, *args, **kwargs)


class ReportGenerateView(LoginRequiredMixin, TemplateView):
    """レポート生成画面"""
    template_name = 'order_management/report_generate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # プロジェクト一覧（プロジェクト別レポート用）
        context['projects'] = Project.objects.all().order_by('-created_at')[:100]

        # シナリオ一覧（予測レポート用）
        context['scenarios'] = ForecastScenario.objects.filter(is_active=True)

        # 現在の年月
        today = date.today()
        context['current_year'] = today.year
        context['current_month'] = today.month

        return context

    def post(self, request, *args, **kwargs):
        """レポート生成処理"""
        report_type = request.POST.get('report_type')
        include_pdf = request.POST.get('include_pdf') == 'on'

        try:
            # レポートデータ生成
            if report_type == 'monthly':
                year = int(request.POST.get('year'))
                month = int(request.POST.get('month'))
                report_data = generate_monthly_report(year, month)
                title = f"{year}年{month}月 月次経営レポート"
                period_start = date(year, month, 1)
                if month == 12:
                    period_end = date(year + 1, 1, 1)
                else:
                    period_end = date(year, month + 1, 1)

            elif report_type == 'project':
                project_id = int(request.POST.get('project_id'))
                report_data = generate_project_report(project_id)
                project = Project.objects.get(id=project_id)
                title = f"プロジェクトレポート - {project.site_name}"
                period_start = project.work_start_date or date.today()
                period_end = project.work_end_date or date.today()

            elif report_type == 'cashflow':
                year = int(request.POST.get('year'))
                month = int(request.POST.get('month'))
                report_data = generate_cashflow_report(year, month)
                title = f"{year}年{month}月 キャッシュフローレポート"
                period_start = date(year, month, 1)
                if month == 12:
                    period_end = date(year + 1, 1, 1)
                else:
                    period_end = date(year, month + 1, 1)

            elif report_type == 'forecast':
                scenario_id = int(request.POST.get('scenario_id'))
                report_data = generate_forecast_report(scenario_id)
                scenario = ForecastScenario.objects.get(id=scenario_id)
                title = f"予測レポート - {scenario.name}"
                period_start = date.today()
                period_end = date.today()

            else:
                messages.error(request, '無効なレポートタイプです')
                return redirect('order_management:report_generate')

            # Reportオブジェクト作成
            report = Report.objects.create(
                title=title,
                report_type=report_type,
                description=f'{title} - 自動生成',
                period_start=period_start,
                period_end=period_end,
                report_data=report_data,
                generated_by=request.user,
                is_published=True
            )

            # PDF生成
            if include_pdf:
                try:
                    pdf_path = generate_pdf_report(report_data, report_type, title)
                    report.pdf_file = pdf_path
                    report.save()
                except Exception as e:
                    messages.warning(request, f'PDF生成に失敗しました: {str(e)}')

            messages.success(request, 'レポートを生成しました')
            return redirect('order_management:report_detail', pk=report.id)

        except Exception as e:
            messages.error(request, f'レポート生成に失敗しました: {str(e)}')
            return redirect('order_management:report_generate')


@login_required
def report_download_pdf(request, pk):
    """レポートPDFダウンロード"""
    report = get_object_or_404(Report, id=pk)

    if not report.pdf_file:
        messages.error(request, 'PDFファイルが存在しません')
        return redirect('order_management:report_detail', pk=pk)

    # PDFファイルパス
    from django.conf import settings
    pdf_path = os.path.join(settings.MEDIA_ROOT, report.pdf_file.name)

    if not os.path.exists(pdf_path):
        messages.error(request, 'PDFファイルが見つかりません')
        return redirect('order_management:report_detail', pk=pk)

    # ファイルレスポンス
    response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
    return response


@login_required
@require_http_methods(["POST"])
def report_regenerate_pdf(request, pk):
    """レポートPDFを再生成"""
    report = get_object_or_404(Report, id=pk)

    try:
        pdf_path = generate_pdf_report(report.report_data, report.report_type, report.title)
        report.pdf_file = pdf_path
        report.save()

        messages.success(request, 'PDFを再生成しました')
    except Exception as e:
        messages.error(request, f'PDF生成に失敗しました: {str(e)}')

    return redirect('order_management:report_detail', pk=pk)


@login_required
@require_http_methods(["GET"])
def report_preview_api(request):
    """レポートプレビューAPI"""
    report_type = request.GET.get('type')

    try:
        if report_type == 'monthly':
            year = safe_int(request.GET.get('year'))
            month = safe_int(request.GET.get('month'))
            report_data = generate_monthly_report(year, month)

        elif report_type == 'project':
            project_id = safe_int(request.GET.get('project_id'))
            report_data = generate_project_report(project_id)

        elif report_type == 'cashflow':
            year = safe_int(request.GET.get('year'))
            month = safe_int(request.GET.get('month'))
            report_data = generate_cashflow_report(year, month)

        elif report_type == 'forecast':
            scenario_id = safe_int(request.GET.get('scenario_id'))
            report_data = generate_forecast_report(scenario_id)

        else:
            return JsonResponse({'success': False, 'error': '無効なレポートタイプです'}, status=400)

        return JsonResponse({
            'success': True,
            'report_data': report_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
