"""データバックアップ・復元ビュー"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.contrib import messages
import json
import io
from datetime import datetime


@login_required
@require_http_methods(["GET"])
def export_data(request):
    """
    完全バックアップ - すべてのデータをJSON形式でエクスポート

    含まれるデータ:
    - ユーザー情報（User, Group, Permission）
    - 案件管理（Project, MaterialOrder, Invoice など）
    - 下請け管理（Contractor, Subcontract など）
    - ContentTypes（必須：Permissionなどの参照整合性のため）
    - その他すべてのアプリケーションデータ

    ⚠️ 注意: メディアファイル（画像、PDF等）は含まれません
    """
    try:
        # すべてのアプリケーションデータをエクスポート
        output = io.StringIO()
        error_output = io.StringIO()

        # dumpdataコマンドでデータベース全体をエクスポート
        # exclude: セッション、ログエントリのみを除外
        # contenttypes は Permission の参照整合性のために必須
        call_command(
            'dumpdata',
            exclude=['sessions', 'admin.logentry'],
            indent=2,
            output=output,
            stderr=error_output
        )

        # JSONデータを取得
        json_data = output.getvalue()

        # データの統計情報を取得（ログ用）
        import json as json_lib
        data_list = json_lib.loads(json_data)
        model_counts = {}
        for item in data_list:
            model = item.get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1

        # レスポンスを作成
        response = HttpResponse(
            json_data,
            content_type='application/json; charset=utf-8'
        )
        filename = f'complete_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # ログ出力（デバッグ用）
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'バックアップ作成: {len(data_list)}個のオブジェクト, {len(model_counts)}種類のモデル')

        return response

    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'エクスポートエラー: {str(e)}\n{traceback.format_exc()}')

        return JsonResponse({
            'status': 'error',
            'message': f'エクスポート中にエラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def import_data_view(request):
    """
    完全リストア - バックアップファイルからすべてのデータをインポート

    注意:
    - 既存のデータは保持されます（PKが重複する場合は更新される可能性があります）
    - クリーンインストールへのリストアに最適
    - 本番環境では事前にバックアップを取ることを推奨
    - ⚠️ メディアファイル（画像、PDF等）は別途復元が必要です
    """
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

            # ファイル名の検証
            if not uploaded_file.name.endswith('.json'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'JSONファイルのみ対応しています'
                }, status=400)

            # ファイルサイズの検証（100MB以下）
            if uploaded_file.size > 100 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ファイルサイズが大きすぎます（最大100MB）'
                }, status=400)

            # JSONデータの読み込みと検証
            try:
                file_content = uploaded_file.read().decode('utf-8')
                json_data = json.loads(file_content)

                # 基本的な形式チェック
                if not isinstance(json_data, list):
                    return JsonResponse({
                        'status': 'error',
                        'message': '無効なバックアップファイル形式です'
                    }, status=400)

                # バックアップファイルの内容を検証
                if len(json_data) == 0:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'バックアップファイルが空です'
                    }, status=400)

                # モデル数をカウント（ログ用）
                model_counts = {}
                for item in json_data:
                    model = item.get('model', 'unknown')
                    model_counts[model] = model_counts.get(model, 0) + 1

                # 重要なモデルが含まれているか確認
                has_users = any('user' in model for model in model_counts.keys())
                has_projects = any('project' in model for model in model_counts.keys())

                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'インポート準備: {len(json_data)}個のオブジェクト, {len(model_counts)}種類のモデル')
                logger.info(f'モデル内訳: {dict(list(model_counts.items())[:10])}...')

            except UnicodeDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ファイルのエンコーディングが正しくありません（UTF-8である必要があります）'
                }, status=400)
            except json.JSONDecodeError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'無効なJSONファイルです: {str(e)}'
                }, status=400)

            # 一時ファイルに保存してloaddataコマンドを実行
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                # loaddataコマンドでデータをインポート
                output = io.StringIO()
                error_output = io.StringIO()

                call_command(
                    'loaddata',
                    temp_file_path,
                    verbosity=2,
                    stdout=output,
                    stderr=error_output
                )

                # 成功メッセージ
                output_text = output.getvalue()
                error_text = error_output.getvalue()

                # インポートされたオブジェクト数を数える
                import re
                installed_match = re.search(r'Installed (\d+) object', output_text)
                installed_count = installed_match.group(1) if installed_match else len(json_data)

                # ログ出力
                logger = logging.getLogger(__name__)
                logger.info(f'インポート完了: {installed_count}個のオブジェクト')
                if error_text:
                    logger.warning(f'インポート警告: {error_text}')

                return JsonResponse({
                    'status': 'success',
                    'message': 'データのインポートが完了しました',
                    'details': f'{installed_count}個のオブジェクトがインポートされました',
                    'model_count': len(model_counts),
                    'warnings': error_text if error_text else None
                })

            finally:
                # 一時ファイルを削除
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'インポートエラー: {str(e)}\n{traceback.format_exc()}')

            return JsonResponse({
                'status': 'error',
                'message': f'インポート中にエラーが発生しました: {str(e)}',
                'details': 'サーバーログを確認してください'
            }, status=500)
