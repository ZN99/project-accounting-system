from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError, models
from .models import WorkType


@login_required
@require_http_methods(["GET"])
def work_type_list_ajax(request):
    """工事種別一覧取得API - AJAX用

    工事種別管理モーダルで工事種別一覧を取得する
    """
    try:
        work_types = WorkType.objects.all().order_by('display_order', 'name')

        work_types_data = []
        for work_type in work_types:
            work_types_data.append({
                'id': work_type.id,
                'name': work_type.name,
                'description': work_type.description or '',
                'is_active': work_type.is_active,
                'display_order': work_type.display_order,
                'created_at': work_type.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(work_type, 'created_at') else '',
            })

        return JsonResponse({
            'success': True,
            'work_types': work_types_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def work_type_create_ajax(request):
    """工事種別AJAX作成 - モーダルから作成

    案件登録中に工事種別を作成するためのAJAXエンドポイント
    """
    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        # バリデーション
        if not name:
            return JsonResponse({
                'success': False,
                'error': '種別名は必須です'
            }, status=400)

        # 既存チェック
        if WorkType.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'error': 'この種別名は既に登録されています'
            }, status=400)

        # 最大表示順を取得して末尾に追加
        max_order = WorkType.objects.aggregate(models.Max('display_order'))['display_order__max'] or 0

        # 作成
        work_type = WorkType.objects.create(
            name=name,
            description=description,
            display_order=max_order + 1,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'work_type': {
                'id': work_type.id,
                'name': work_type.name,
                'description': work_type.description or '',
                'is_active': work_type.is_active,
                'display_order': work_type.display_order,
            }
        })

    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'error': 'この種別名は既に登録されています'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def work_type_update_ajax(request):
    """工事種別AJAX更新

    工事種別を更新するためのAJAXエンドポイント
    """
    try:
        work_type_id = request.POST.get('id')
        if not work_type_id:
            return JsonResponse({
                'success': False,
                'error': 'IDが指定されていません'
            }, status=400)

        work_type = get_object_or_404(WorkType, pk=work_type_id)

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        # バリデーション
        if not name:
            return JsonResponse({
                'success': False,
                'error': '種別名は必須です'
            }, status=400)

        # 既存チェック（自分以外）
        if WorkType.objects.filter(name=name).exclude(pk=work_type_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'この種別名は既に登録されています'
            }, status=400)

        # 更新
        work_type.name = name
        work_type.description = description
        work_type.save()

        return JsonResponse({
            'success': True,
            'work_type': {
                'id': work_type.id,
                'name': work_type.name,
                'description': work_type.description or '',
                'is_active': work_type.is_active,
                'display_order': work_type.display_order,
            }
        })

    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'error': 'この種別名は既に登録されています'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def work_type_delete_ajax(request):
    """工事種別AJAX削除

    工事種別を削除するためのAJAXエンドポイント
    """
    try:
        work_type_id = request.POST.get('id')
        if not work_type_id:
            return JsonResponse({
                'success': False,
                'error': 'IDが指定されていません'
            }, status=400)

        work_type = get_object_or_404(WorkType, pk=work_type_id)

        # 使用中チェック（案件で使用されているかチェック）
        from .models import Project
        if Project.objects.filter(work_type=work_type.name).exists():
            return JsonResponse({
                'success': False,
                'error': 'この種別は案件で使用されているため削除できません。'
            }, status=400)

        work_type_name = work_type.name
        work_type.delete()

        return JsonResponse({
            'success': True,
            'message': f'工事種別「{work_type_name}」を削除しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def work_type_reorder_ajax(request):
    """工事種別AJAX並び替え

    工事種別の表示順を変更するためのAJAXエンドポイント
    """
    try:
        work_type_id = request.POST.get('id')
        direction = request.POST.get('direction')

        if not work_type_id or direction not in ['up', 'down']:
            return JsonResponse({
                'success': False,
                'error': '無効なパラメータです'
            }, status=400)

        work_type = get_object_or_404(WorkType, pk=work_type_id)

        # 全体の順番を取得
        work_types = list(WorkType.objects.all().order_by('display_order', 'name'))

        # 現在の位置を見つける
        current_index = next((i for i, wt in enumerate(work_types) if wt.id == work_type.id), None)

        if current_index is None:
            return JsonResponse({
                'success': False,
                'error': '工事種別が見つかりません'
            }, status=404)

        # 移動先のインデックスを計算
        if direction == 'up' and current_index > 0:
            # 上と入れ替え
            work_types[current_index], work_types[current_index - 1] = work_types[current_index - 1], work_types[current_index]
        elif direction == 'down' and current_index < len(work_types) - 1:
            # 下と入れ替え
            work_types[current_index], work_types[current_index + 1] = work_types[current_index + 1], work_types[current_index]
        else:
            # 移動できない
            return JsonResponse({
                'success': True,
                'message': 'これ以上移動できません'
            })

        # display_orderを更新
        for index, wt in enumerate(work_types):
            wt.display_order = index
            wt.save(update_fields=['display_order'])

        return JsonResponse({
            'success': True,
            'message': '並び替えを更新しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)
