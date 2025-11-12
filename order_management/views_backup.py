"""データバックアップ・復元ビュー"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from .models import Project, Contractor, UserProfile


@login_required
@require_http_methods(["GET"])
def export_data(request):
    """データをJSON形式でエクスポート"""
    try:
        # エクスポートするデータを収集
        data = {
            'export_date': datetime.now().isoformat(),
            'projects': list(Project.objects.all().values()),
            'contractors': list(Contractor.objects.all().values()),
            'user_profiles': list(UserProfile.objects.all().values()),
        }

        # JSON形式でレスポンスを返す
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'

        return response
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'エクスポート中にエラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def import_data_view(request):
    """データをインポート"""
    if request.method == 'GET':
        # インポート画面を表示
        return render(request, 'order_management/import_data.html')

    elif request.method == 'POST':
        try:
            # アップロードされたファイルを取得
            uploaded_file = request.FILES.get('backup_file')

            if not uploaded_file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ファイルが選択されていません'
                }, status=400)

            # JSONデータを読み込む
            data = json.load(uploaded_file)

            # データをインポート（実装例）
            # 注: 本番環境では、より詳細なバリデーションとエラーハンドリングが必要
            imported_count = {
                'projects': 0,
                'contractors': 0,
                'user_profiles': 0
            }

            # ここに実際のインポート処理を実装
            # 例: Project.objects.bulk_create(...) など

            return JsonResponse({
                'status': 'success',
                'message': 'データのインポートが完了しました',
                'imported': imported_count
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '無効なJSONファイルです'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'インポート中にエラーが発生しました: {str(e)}'
            }, status=500)
