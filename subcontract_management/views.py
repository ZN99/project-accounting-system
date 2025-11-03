from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from .models import Contractor, Subcontract, ProjectProfitAnalysis
from .forms import ContractorForm, SubcontractForm
from order_management.models import Project


def subcontract_dashboard(request):
    """発注管理ダッシュボード"""
    # 基本統計
    total_subcontracts = Subcontract.objects.count()
    total_contractors = Contractor.objects.filter(is_active=True).count()
    pending_payments = Subcontract.objects.filter(payment_status='pending').count()

    # 支払い統計
    pending_amount = Subcontract.objects.filter(
        payment_status='pending'
    ).aggregate(Sum('billed_amount'))['billed_amount__sum'] or 0

    paid_amount = Subcontract.objects.filter(
        payment_status='paid'
    ).aggregate(Sum('billed_amount'))['billed_amount__sum'] or 0

    # 利益率統計
    profit_analyses = ProjectProfitAnalysis.objects.all()
    avg_profit_rate = profit_analyses.aggregate(
        Avg('profit_rate')
    )['profit_rate__avg'] or 0

    # 最近の発注
    recent_subcontracts = Subcontract.objects.select_related(
        'project', 'contractor', 'internal_worker'
    ).order_by('-created_at')[:5]

    # 支払い予定
    upcoming_payments = Subcontract.objects.filter(
        payment_status='pending',
        payment_due_date__lte=timezone.now().date() + timedelta(days=7)
    ).select_related('project', 'contractor').order_by('payment_due_date')[:5]

    # 利益率トップ5
    top_profit_projects = profit_analyses.select_related(
        'project'
    ).order_by('-profit_rate')[:5]

    context = {
        'total_subcontracts': total_subcontracts,
        'total_contractors': total_contractors,
        'pending_payments': pending_payments,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
        'avg_profit_rate': avg_profit_rate,
        'recent_subcontracts': recent_subcontracts,
        'upcoming_payments': upcoming_payments,
        'top_profit_projects': top_profit_projects,
    }

    return render(request, 'subcontract_management/dashboard.html', context)


def project_subcontract_list(request, project_id):
    """案件別発注一覧"""
    project = get_object_or_404(Project, pk=project_id)
    subcontracts = Subcontract.objects.filter(
        project=project
    ).select_related('contractor', 'internal_worker')

    # 利益分析
    try:
        profit_analysis = ProjectProfitAnalysis.objects.get(project=project)
    except ProjectProfitAnalysis.DoesNotExist:
        profit_analysis = None

    context = {
        'project': project,
        'subcontracts': subcontracts,
        'profit_analysis': profit_analysis,
    }

    return render(request, 'subcontract_management/project_subcontract_list.html', context)


def subcontract_create(request, project_id):
    """発注新規作成"""
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        form = SubcontractForm(request.POST)
        if form.is_valid():
            subcontract = form.save(commit=False)
            subcontract.project = project
            subcontract.save()
            messages.success(request, f'外注先「{subcontract.contractor.name}」を追加しました。')
            return redirect('subcontract_management:project_subcontract_list', project_id=project.pk)
    else:
        form = SubcontractForm()

    context = {
        'form': form,
        'project': project,
        'title': '外注先追加'
    }

    return render(request, 'subcontract_management/subcontract_form.html', context)


def subcontract_update(request, pk):
    """外注編集"""
    subcontract = get_object_or_404(Subcontract, pk=pk)

    if request.method == 'POST':
        form = SubcontractForm(request.POST, instance=subcontract)
        if form.is_valid():
            subcontract = form.save()
            messages.success(request, f'外注先「{subcontract.contractor.name}」を更新しました。')
            return redirect('subcontract_management:project_subcontract_list',
                          project_id=subcontract.project.pk)
    else:
        form = SubcontractForm(instance=subcontract)

    context = {
        'form': form,
        'subcontract': subcontract,
        'project': subcontract.project,
        'title': '外注先編集'
    }

    return render(request, 'subcontract_management/subcontract_form.html', context)


def subcontract_delete(request, pk):
    """外注削除"""
    subcontract = get_object_or_404(Subcontract, pk=pk)
    project = subcontract.project

    if request.method == 'POST':
        contractor_name = subcontract.contractor.name if subcontract.contractor else "不明な外注先"
        subcontract.delete()
        messages.success(request, f'外注先「{contractor_name}」を削除しました。')
        return redirect('subcontract_management:project_subcontract_list', project_id=project.pk)

    # GETリクエストの場合は一覧ページにリダイレクト
    return redirect('subcontract_management:project_subcontract_list', project_id=project.pk)


def contractor_list(request):
    """外注先マスター一覧"""
    contractors = Contractor.objects.all()

    # フィルタリング
    contractor_type = request.GET.get('contractor_type')
    if contractor_type:
        contractors = contractors.filter(contractor_type=contractor_type)

    is_active = request.GET.get('is_active')
    if is_active:
        contractors = contractors.filter(is_active=is_active == 'true')

    # 検索
    search_query = request.GET.get('search')
    if search_query:
        contractors = contractors.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(specialties__icontains=search_query)
        )

    # ページネーション
    paginator = Paginator(contractors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'contractors': page_obj,
        'contractor_type_choices': Contractor.CONTRACTOR_TYPE_CHOICES,
        'contractor_type': contractor_type,
        'is_active': is_active,
        'search_query': search_query,
    }

    return render(request, 'subcontract_management/contractor_list.html', context)


def contractor_create(request):
    """外注先マスター新規作成"""
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            contractor = form.save()
            messages.success(request, f'外注先「{contractor.name}」を登録しました。')
            return redirect('subcontract_management:contractor_list')
    else:
        form = ContractorForm()

    context = {
        'form': form,
        'title': '外注先新規登録'
    }

    return render(request, 'subcontract_management/contractor_form.html', context)


def profit_analysis_list(request):
    """利益分析一覧"""
    analyses = ProjectProfitAnalysis.objects.select_related(
        'project'
    ).order_by('-profit_rate')

    # フィルタリング
    min_profit_rate = request.GET.get('min_profit_rate')
    if min_profit_rate:
        analyses = analyses.filter(profit_rate__gte=min_profit_rate)

    context = {
        'analyses': analyses,
        'min_profit_rate': min_profit_rate,
    }

    return render(request, 'subcontract_management/profit_analysis_list.html', context)


def payment_tracking(request):
    """支払い追跡"""
    subcontracts = Subcontract.objects.select_related(
        'project', 'contractor'
    ).order_by('payment_due_date')

    # ステータスフィルター
    payment_status = request.GET.get('payment_status')
    if payment_status:
        subcontracts = subcontracts.filter(payment_status=payment_status)

    # 期日フィルター
    overdue_only = request.GET.get('overdue_only')
    if overdue_only:
        subcontracts = subcontracts.filter(
            payment_due_date__lt=timezone.now().date(),
            payment_status='pending'
        )

    context = {
        'subcontracts': subcontracts,
        'payment_status_choices': Subcontract.PAYMENT_STATUS_CHOICES,
        'payment_status': payment_status,
        'overdue_only': overdue_only,
    }

    return render(request, 'subcontract_management/payment_tracking.html', context)


def export_subcontracts_csv(request):
    """外注データCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="subcontracts.csv"'

    # BOM付きでUTF-8エンコード
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        '管理No', '現場名', '外注先', '業者種別', '依頼金額', '被請求額',
        '部材費合計', '総コスト', '支払状況', '出金予定日', '出金日',
        '発注書', '作業内容', '備考', '登録日'
    ])

    subcontracts = Subcontract.objects.select_related(
        'project', 'contractor'
    ).order_by('-created_at')

    for sub in subcontracts:
        writer.writerow([
            sub.management_no,
            sub.site_name,
            sub.contractor.name,
            sub.contractor.get_contractor_type_display(),
            sub.contract_amount,
            sub.billed_amount,
            sub.total_material_cost,
            sub.get_total_cost(),
            sub.get_payment_status_display(),
            sub.payment_due_date.strftime('%Y-%m-%d') if sub.payment_due_date else '',
            sub.payment_date.strftime('%Y-%m-%d') if sub.payment_date else '',
            '発行済み' if sub.purchase_order_issued else '未発行',
            sub.work_description,
            sub.notes,
            sub.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response
