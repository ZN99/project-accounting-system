from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import Project, MaterialOrder, MaterialOrderItem
from subcontract_management.models import Contractor


@login_required
def material_order_list(request, project_id):
    """案件の資材発注一覧"""
    project = get_object_or_404(Project, id=project_id)
    orders = project.material_orders.all().order_by('-order_date')

    context = {
        'project': project,
        'orders': orders,
    }
    return render(request, 'order_management/material/material_order_list.html', context)


@login_required
def material_order_create(request, project_id):
    """資材発注作成"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        # 発注の基本情報
        contractor_id = request.POST.get('contractor_id')
        order_date = request.POST.get('order_date')
        delivery_date = request.POST.get('delivery_date')
        notes = request.POST.get('notes', '')

        # 業者の処理
        contractor = None
        if contractor_id:
            contractor = get_object_or_404(Contractor, id=contractor_id)
        else:
            # 新しい業者を作成
            contractor_name = request.POST.get('contractor_name')
            client_address = request.POST.get('client_address', '')
            if contractor_name and contractor_name.strip():
                contractor = Contractor.objects.create(
                    name=contractor_name.strip(),
                    address=client_address,
                    is_active=True
                )

        if contractor:
            # 資材発注を作成
            order = MaterialOrder.objects.create(
                project=project,
                contractor=contractor,
                order_date=order_date,
                delivery_date=delivery_date if delivery_date else None,
                notes=notes
            )

            # 資材項目を追加
            material_names = request.POST.getlist('material_name[]')
            specifications = request.POST.getlist('specification[]')
            quantities = request.POST.getlist('quantity[]')
            units = request.POST.getlist('unit[]')
            unit_prices = request.POST.getlist('unit_price[]')

            for i in range(len(material_names)):
                if material_names[i].strip():
                    MaterialOrderItem.objects.create(
                        order=order,
                        material_name=material_names[i],
                        specification=specifications[i] if i < len(specifications) else '',
                        quantity=float(quantities[i]) if quantities[i] else 0,
                        unit=units[i] if i < len(units) else '個',
                        unit_price=float(unit_prices[i]) if unit_prices[i] else 0
                    )

            messages.success(request, f'資材発注 {order.order_number} を作成しました。')
            return redirect('order_management:material_order_list', project_id=project.id)
        else:
            messages.error(request, '業者情報が正しく入力されていません。')

    # 資材業者一覧（アクティブな業者のみ）
    contractors = Contractor.objects.filter(
        is_active=True
    ).order_by('name')

    context = {
        'project': project,
        'contractors': contractors,
    }
    return render(request, 'order_management/material/material_order_form.html', context)


@login_required
def material_order_detail(request, project_id, order_id):
    """資材発注詳細"""
    project = get_object_or_404(Project, id=project_id)
    order = get_object_or_404(MaterialOrder, id=order_id, project=project)

    context = {
        'project': project,
        'order': order,
    }
    return render(request, 'order_management/material/material_order_detail.html', context)


@login_required
def material_order_edit(request, project_id, order_id):
    """資材発注編集"""
    project = get_object_or_404(Project, id=project_id)
    order = get_object_or_404(MaterialOrder, id=order_id, project=project)

    if request.method == 'POST':
        # 基本情報の更新
        order.order_date = request.POST.get('order_date')
        delivery_date = request.POST.get('delivery_date')
        order.delivery_date = delivery_date if delivery_date else None
        order.status = request.POST.get('status', order.status)
        order.notes = request.POST.get('notes', '')

        # 実際の納品日
        actual_delivery_date = request.POST.get('actual_delivery_date')
        order.actual_delivery_date = actual_delivery_date if actual_delivery_date else None

        order.save()

        # 既存の項目を削除して再作成
        order.items.all().delete()

        # 資材項目を再追加
        material_names = request.POST.getlist('material_name[]')
        specifications = request.POST.getlist('specification[]')
        quantities = request.POST.getlist('quantity[]')
        units = request.POST.getlist('unit[]')
        unit_prices = request.POST.getlist('unit_price[]')

        for i in range(len(material_names)):
            if material_names[i].strip():
                MaterialOrderItem.objects.create(
                    order=order,
                    material_name=material_names[i],
                    specification=specifications[i] if i < len(specifications) else '',
                    quantity=float(quantities[i]) if quantities[i] else 0,
                    unit=units[i] if i < len(units) else '個',
                    unit_price=float(unit_prices[i]) if unit_prices[i] else 0
                )

        messages.success(request, f'資材発注 {order.order_number} を更新しました。')
        return redirect('order_management:material_order_detail', project_id=project.id, order_id=order.id)

    # 資材業者一覧（アクティブな業者のみ）
    contractors = Contractor.objects.filter(
        is_active=True
    ).order_by('name')

    context = {
        'project': project,
        'order': order,
        'contractors': contractors,
    }
    return render(request, 'order_management/material/material_order_form.html', context)


@csrf_exempt
@login_required
def material_order_status_update(request, project_id, order_id):
    """資材発注ステータス更新（AJAX）"""
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        order = get_object_or_404(MaterialOrder, id=order_id, project=project)

        try:
            data = json.loads(request.body)
            new_status = data.get('status')

            if new_status in dict(MaterialOrder.ORDER_STATUS_CHOICES):
                order.status = new_status

                # 納品済みにする場合は納品日を設定
                if new_status == 'delivered' and not order.actual_delivery_date:
                    order.actual_delivery_date = timezone.now().date()

                order.save()

                return JsonResponse({
                    'success': True,
                    'status': order.get_status_display(),
                    'color': order.get_status_color()
                })
            else:
                return JsonResponse({'success': False, 'error': '無効なステータスです'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': '無効なリクエストです'})