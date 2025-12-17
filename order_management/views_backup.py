"""データバックアップ・復元ビュー（ZIP + メディアファイル対応）"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.contrib import messages
from django.conf import settings
import json
import io
import zipfile
import tempfile
import os
import shutil
from datetime import datetime
from pathlib import Path
import django
import logging

from order_management.services.backup_validator import validate_backup
from order_management.services.restore_validator import validate_restore

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def export_data(request):
    """
    完全バックアップ - すべてのデータをZIP形式でエクスポート

    含まれるデータ:
    - data.json: ユーザー情報、案件管理、下請け管理、資材発注、経理情報など全データベースデータ
    - metadata.json: バックアップのメタデータ（作成日時、バージョン、統計情報等）
    - media/: アップロードされた画像、PDF等の全メディアファイル

    ZIPファイル構造:
    backup_20250117_123456.zip
    ├── data.json          # 全データベースデータ
    ├── metadata.json      # バックアップメタデータ
    └── media/            # 全メディアファイル
    """
    try:
        logger.info('完全バックアップ（ZIP + media）を開始...')

        # 1. データベース整合性の検証
        logger.info('ステップ 1/5: データベース整合性検証')
        validation_result = validate_backup()

        if not validation_result['success']:
            logger.error(f'データベース検証エラー: {validation_result["errors"]}')
            return JsonResponse({
                'status': 'error',
                'message': 'データベースに整合性エラーがあります',
                'errors': validation_result['errors']
            }, status=400)

        # 2. JSONデータのエクスポート
        logger.info('ステップ 2/5: JSONデータのエクスポート')
        json_output = io.StringIO()
        error_output = io.StringIO()

        call_command(
            'dumpdata',
            exclude=['sessions', 'admin.logentry'],
            indent=2,
            stdout=json_output,  # output ではなく stdout を使用
            stderr=error_output
        )

        json_data = json_output.getvalue()
        data_list = json.loads(json_data)

        # 3. メタデータの生成
        logger.info('ステップ 3/5: メタデータの生成')
        metadata = {
            'backup_version': '1.0',
            'created_at': datetime.now().isoformat(),
            'django_version': django.get_version(),
            'database_engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'total_records': len(data_list),
            'models': validation_result['statistics'],
            'validation': {
                'fk_integrity': 'passed' if validation_result['success'] else 'failed',
                'orphaned_records': len([w for w in validation_result['warnings'] if '孤立レコード' in w]),
                'warnings': validation_result['warnings']
            }
        }

        # 4. メディアファイルの統計収集
        logger.info('ステップ 4/5: メディアファイルの統計収集')
        media_root = Path(settings.MEDIA_ROOT)
        media_files_count = 0
        media_total_size = 0

        if media_root.exists():
            for file_path in media_root.rglob('*'):
                if file_path.is_file():
                    media_files_count += 1
                    media_total_size += file_path.stat().st_size

        metadata['media_files'] = {
            'count': media_files_count,
            'total_size_mb': round(media_total_size / (1024 * 1024), 2)
        }

        # 5. ZIPファイルの作成
        logger.info('ステップ 5/5: ZIPファイルの作成')
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # data.json を追加
                zip_file.writestr('data.json', json_data)

                # metadata.json を追加
                zip_file.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))

                # media/ フォルダを追加
                if media_root.exists():
                    for file_path in media_root.rglob('*'):
                        if file_path.is_file():
                            arcname = f'media/{file_path.relative_to(media_root)}'
                            zip_file.write(file_path, arcname)

            temp_zip_path = temp_zip.name

        # ZIPファイルを読み込んでレスポンスとして返す
        with open(temp_zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()

        # 一時ファイルを削除
        os.unlink(temp_zip_path)

        # レスポンスを作成
        response = HttpResponse(
            zip_content,
            content_type='application/zip'
        )
        filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f'バックアップ作成完了: {len(data_list)}個のオブジェクト, メディアファイル{media_files_count}個')

        return response

    except Exception as e:
        import traceback
        logger.error(f'エクスポートエラー: {str(e)}\n{traceback.format_exc()}')

        return JsonResponse({
            'status': 'error',
            'message': f'エクスポート中にエラーが発生しました: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def import_data_view(request):
    """
    完全リストア - バックアップファイル（ZIP）からすべてのデータをインポート

    対応形式:
    - ZIP形式（data.json + metadata.json + media/）
    - JSON形式（後方互換性のためサポート）

    注意:
    - 既存のデータは保持されます（PKが重複する場合は更新される可能性があります）
    - クリーンインストールへのリストアに最適
    - 本番環境では事前にバックアップを取ることを推奨
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
            if not (uploaded_file.name.endswith('.zip') or uploaded_file.name.endswith('.json')):
                return JsonResponse({
                    'status': 'error',
                    'message': 'ZIPまたはJSONファイルのみ対応しています'
                }, status=400)

            # ファイルサイズの検証（500MB以下）
            max_size = 500 * 1024 * 1024
            if uploaded_file.size > max_size:
                return JsonResponse({
                    'status': 'error',
                    'message': f'ファイルサイズが大きすぎます（最大500MB）'
                }, status=400)

            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(mode='wb', suffix=os.path.splitext(uploaded_file.name)[1], delete=False) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            try:
                # ZIP形式の場合
                if uploaded_file.name.endswith('.zip'):
                    return _restore_from_zip(temp_file_path)

                # JSON形式の場合（後方互換性）
                else:
                    return _restore_from_json(temp_file_path)

            finally:
                # 一時ファイルを削除
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            import traceback
            logger.error(f'インポートエラー: {str(e)}\n{traceback.format_exc()}')

            return JsonResponse({
                'status': 'error',
                'message': f'インポート中にエラーが発生しました: {str(e)}',
                'details': 'サーバーログを確認してください'
            }, status=500)


def _restore_from_zip(zip_file_path: str) -> JsonResponse:
    """ZIPファイルからのリストア処理"""
    logger.info(f'ZIPファイルからのリストア開始: {zip_file_path}')

    # 1. バックアップファイルの検証
    logger.info('ステップ 1/4: バックアップファイルの検証')
    validation_result = validate_restore(zip_file_path)

    if not validation_result['success']:
        logger.error(f'バックアップファイル検証エラー: {validation_result["errors"]}')
        return JsonResponse({
            'status': 'error',
            'message': 'バックアップファイルに問題があります',
            'errors': validation_result['errors'],
            'warnings': validation_result['warnings']
        }, status=400)

    # 2. ZIPファイルの展開
    logger.info('ステップ 2/4: ZIPファイルの展開')
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
            zip_file.extractall(temp_dir)

        data_json_path = os.path.join(temp_dir, 'data.json')
        metadata_json_path = os.path.join(temp_dir, 'metadata.json')
        media_dir_path = os.path.join(temp_dir, 'media')

        # metadata.json を読み込み
        with open(metadata_json_path, 'r', encoding='utf-8') as meta_file:
            metadata = json.load(meta_file)

        # 3. データベースのインポート
        logger.info('ステップ 3/4: データベースのインポート')
        output = io.StringIO()
        error_output = io.StringIO()

        call_command(
            'loaddata',
            data_json_path,
            verbosity=2,
            stdout=output,
            stderr=error_output
        )

        output_text = output.getvalue()
        error_text = error_output.getvalue()

        # インポートされたオブジェクト数を数える
        import re
        installed_match = re.search(r'Installed (\d+) object', output_text)
        installed_count = installed_match.group(1) if installed_match else metadata.get('total_records', 0)

        # 4. メディアファイルの復元
        logger.info('ステップ 4/4: メディアファイルの復元')
        media_restored_count = 0

        if os.path.exists(media_dir_path):
            media_root = Path(settings.MEDIA_ROOT)
            media_root.mkdir(parents=True, exist_ok=True)

            for file_path in Path(media_dir_path).rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(media_dir_path)
                    destination = media_root / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, destination)
                    media_restored_count += 1

        logger.info(f'リストア完了: {installed_count}個のオブジェクト, メディアファイル{media_restored_count}個')

        return JsonResponse({
            'status': 'success',
            'message': 'データのインポートが完了しました',
            'details': f'{installed_count}個のオブジェクトがインポートされました',
            'media_files': media_restored_count,
            'warnings': error_text if error_text else None
        })


def _restore_from_json(json_file_path: str) -> JsonResponse:
    """JSONファイルからのリストア処理（後方互換性）"""
    logger.info(f'JSONファイルからのリストア開始: {json_file_path}')

    # JSONデータの読み込みと検証
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        json_data = json.load(json_file)

    # 基本的な形式チェック
    if not isinstance(json_data, list):
        return JsonResponse({
            'status': 'error',
            'message': '無効なバックアップファイル形式です'
        }, status=400)

    # loaddataコマンドでデータをインポート
    output = io.StringIO()
    error_output = io.StringIO()

    call_command(
        'loaddata',
        json_file_path,
        verbosity=2,
        stdout=output,
        stderr=error_output
    )

    output_text = output.getvalue()
    error_text = error_output.getvalue()

    # インポートされたオブジェクト数を数える
    import re
    installed_match = re.search(r'Installed (\d+) object', output_text)
    installed_count = installed_match.group(1) if installed_match else len(json_data)

    logger.info(f'JSONリストア完了: {installed_count}個のオブジェクト')

    return JsonResponse({
        'status': 'success',
        'message': 'データのインポートが完了しました（メディアファイルは含まれません）',
        'details': f'{installed_count}個のオブジェクトがインポートされました',
        'warnings': '⚠️ メディアファイルは復元されていません。ZIPバックアップを使用してください。'
    })
