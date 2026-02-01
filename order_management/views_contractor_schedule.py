from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Max
import json
from datetime import datetime

from .models import Project, ContractorSchedule
from subcontract_management.models import Contractor


@login_required
@require_http_methods(["GET"])
def contractor_schedule_list_api(request, project_pk):
    """業者スケジュール一覧API

    指定された案件の業者スケジュール一覧を返す
    """
    try:
        project = get_object_or_404(Project, pk=project_pk)

        schedules = ContractorSchedule.objects.filter(
            project=project
        ).select_related('contractor').order_by('order', 'work_start_date')

        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                'id': schedule.id,
                'contractor_id': schedule.contractor.id,
                'contractor_name': schedule.contractor.name,
                'work_start_date': schedule.work_start_date.strftime('%Y-%m-%d'),
                'work_end_date': schedule.work_end_date.strftime('%Y-%m-%d'),
                'work_description': schedule.work_description,
                'notes': schedule.notes,
                'order': schedule.order,
                'duration_days': schedule.get_duration_days(),
            })

        return JsonResponse({
            'success': True,
            'schedules': schedule_list
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_schedule_create_api(request, project_pk):
    """業者スケジュール作成API

    新しい業者スケジュールを作成する
    """
    try:
        project = get_object_or_404(Project, pk=project_pk)

        data = json.loads(request.body)

        # 必須フィールドの検証
        contractor_id = data.get('contractor_id')
        work_start_date = data.get('work_start_date')
        work_end_date = data.get('work_end_date')

        if not contractor_id:
            return JsonResponse({
                'success': False,
                'error': '業者を選択してください'
            }, status=400)

        if not work_start_date or not work_end_date:
            return JsonResponse({
                'success': False,
                'error': '作業開始日と終了日を入力してください'
            }, status=400)

        # 日付の検証
        try:
            start_date = datetime.strptime(work_start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(work_end_date, '%Y-%m-%d').date()

            if start_date > end_date:
                return JsonResponse({
                    'success': False,
                    'error': '終了日は開始日より後の日付を指定してください'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': '日付の形式が正しくありません'
            }, status=400)

        contractor = get_object_or_404(Contractor, pk=contractor_id)

        # 表示順序の設定（既存の最大値 + 1）
        max_order = ContractorSchedule.objects.filter(
            project=project
        ).aggregate(max_order=Max('order'))['max_order']
        order = (max_order or 0) + 1

        # スケジュール作成
        schedule = ContractorSchedule.objects.create(
            project=project,
            contractor=contractor,
            work_start_date=start_date,
            work_end_date=end_date,
            work_description=data.get('work_description', ''),
            notes=data.get('notes', ''),
            order=order
        )

        return JsonResponse({
            'success': True,
            'message': '業者スケジュールを追加しました',
            'schedule': {
                'id': schedule.id,
                'contractor_id': schedule.contractor.id,
                'contractor_name': schedule.contractor.name,
                'work_start_date': schedule.work_start_date.strftime('%Y-%m-%d'),
                'work_end_date': schedule.work_end_date.strftime('%Y-%m-%d'),
                'work_description': schedule.work_description,
                'notes': schedule.notes,
                'order': schedule.order,
                'duration_days': schedule.get_duration_days(),
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_schedule_update_api(request, pk):
    """業者スケジュール更新API

    既存の業者スケジュールを更新する
    """
    try:
        schedule = get_object_or_404(ContractorSchedule, pk=pk)

        data = json.loads(request.body)

        # 業者の更新
        if 'contractor_id' in data:
            contractor_id = data['contractor_id']
            if contractor_id:
                contractor = get_object_or_404(Contractor, pk=contractor_id)
                schedule.contractor = contractor

        # 日付の更新
        if 'work_start_date' in data and 'work_end_date' in data:
            try:
                start_date = datetime.strptime(data['work_start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(data['work_end_date'], '%Y-%m-%d').date()

                if start_date > end_date:
                    return JsonResponse({
                        'success': False,
                        'error': '終了日は開始日より後の日付を指定してください'
                    }, status=400)

                schedule.work_start_date = start_date
                schedule.work_end_date = end_date
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': '日付の形式が正しくありません'
                }, status=400)

        # その他のフィールドの更新
        if 'work_description' in data:
            schedule.work_description = data['work_description']

        if 'notes' in data:
            schedule.notes = data['notes']

        if 'order' in data:
            schedule.order = data['order']

        schedule.save()

        return JsonResponse({
            'success': True,
            'message': '業者スケジュールを更新しました',
            'schedule': {
                'id': schedule.id,
                'contractor_id': schedule.contractor.id,
                'contractor_name': schedule.contractor.name,
                'work_start_date': schedule.work_start_date.strftime('%Y-%m-%d'),
                'work_end_date': schedule.work_end_date.strftime('%Y-%m-%d'),
                'work_description': schedule.work_description,
                'notes': schedule.notes,
                'order': schedule.order,
                'duration_days': schedule.get_duration_days(),
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_schedule_delete_api(request, pk):
    """業者スケジュール削除API

    指定された業者スケジュールを削除する
    """
    try:
        schedule = get_object_or_404(ContractorSchedule, pk=pk)

        schedule.delete()

        return JsonResponse({
            'success': True,
            'message': '業者スケジュールを削除しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def contractor_schedule_reorder_api(request, project_pk):
    """業者スケジュール並び替えAPI

    業者スケジュールの表示順序を一括更新する
    """
    try:
        project = get_object_or_404(Project, pk=project_pk)

        data = json.loads(request.body)
        schedule_order = data.get('schedule_order', [])

        if not schedule_order:
            return JsonResponse({
                'success': False,
                'error': '並び替え情報が空です'
            }, status=400)

        with transaction.atomic():
            for index, schedule_id in enumerate(schedule_order):
                ContractorSchedule.objects.filter(
                    id=schedule_id,
                    project=project
                ).update(order=index)

        return JsonResponse({
            'success': True,
            'message': '表示順序を更新しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)
