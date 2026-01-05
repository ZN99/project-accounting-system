from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import RatingCriteria
from .user_roles import has_role, UserRole


@login_required
@require_http_methods(["GET", "POST"])
def rating_criteria_view(request):
    """評価基準設定画面

    レーダーチャートの評価基準を表示・編集する
    """
    # 権限チェック（管理部・役員のみ）
    if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.SALES)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("評価基準の設定権限がありません")

    criteria = RatingCriteria.get_criteria()

    if request.method == "POST":
        try:
            # 累計売上基準
            criteria.total_sales_score_5 = request.POST.get('total_sales_score_5', 10000000)
            criteria.total_sales_score_4 = request.POST.get('total_sales_score_4', 5000000)
            criteria.total_sales_score_3 = request.POST.get('total_sales_score_3', 1000000)
            criteria.total_sales_score_2 = request.POST.get('total_sales_score_2', 500000)

            # 平均売上基準
            criteria.avg_sales_score_5 = request.POST.get('avg_sales_score_5', 1000000)
            criteria.avg_sales_score_4 = request.POST.get('avg_sales_score_4', 500000)
            criteria.avg_sales_score_3 = request.POST.get('avg_sales_score_3', 300000)
            criteria.avg_sales_score_2 = request.POST.get('avg_sales_score_2', 100000)

            # 平均粗利益率基準
            criteria.profit_margin_score_5 = request.POST.get('profit_margin_score_5', 40.0)
            criteria.profit_margin_score_4 = request.POST.get('profit_margin_score_4', 30.0)
            criteria.profit_margin_score_3 = request.POST.get('profit_margin_score_3', 20.0)
            criteria.profit_margin_score_2 = request.POST.get('profit_margin_score_2', 10.0)

            criteria.updated_by = request.user
            criteria.save()

            messages.success(request, '評価基準を更新しました')
            return redirect('order_management:rating_criteria')

        except Exception as e:
            messages.error(request, f'エラーが発生しました: {str(e)}')

    context = {
        'criteria': criteria,
    }

    return render(request, 'order_management/rating_criteria/rating_criteria.html', context)


@login_required
@require_http_methods(["POST"])
def rating_criteria_update_ajax(request):
    """評価基準AJAX更新

    評価基準を更新するためのAJAXエンドポイント
    """
    try:
        # 権限チェック（管理部・役員のみ）
        if not (has_role(request.user, UserRole.EXECUTIVE) or has_role(request.user, UserRole.SALES)):
            return JsonResponse({
                'success': False,
                'error': '評価基準の設定権限がありません'
            }, status=403)

        criteria = RatingCriteria.get_criteria()

        # 累計売上基準
        criteria.total_sales_score_5 = request.POST.get('total_sales_score_5', 10000000)
        criteria.total_sales_score_4 = request.POST.get('total_sales_score_4', 5000000)
        criteria.total_sales_score_3 = request.POST.get('total_sales_score_3', 1000000)
        criteria.total_sales_score_2 = request.POST.get('total_sales_score_2', 500000)

        # 平均売上基準
        criteria.avg_sales_score_5 = request.POST.get('avg_sales_score_5', 1000000)
        criteria.avg_sales_score_4 = request.POST.get('avg_sales_score_4', 500000)
        criteria.avg_sales_score_3 = request.POST.get('avg_sales_score_3', 300000)
        criteria.avg_sales_score_2 = request.POST.get('avg_sales_score_2', 100000)

        # 平均粗利益率基準
        criteria.profit_margin_score_5 = request.POST.get('profit_margin_score_5', 40.0)
        criteria.profit_margin_score_4 = request.POST.get('profit_margin_score_4', 30.0)
        criteria.profit_margin_score_3 = request.POST.get('profit_margin_score_3', 20.0)
        criteria.profit_margin_score_2 = request.POST.get('profit_margin_score_2', 10.0)

        criteria.updated_by = request.user
        criteria.save()

        return JsonResponse({
            'success': True,
            'message': '評価基準を更新しました'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)
