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
from order_management.models import Project
from django.db import transaction
import re as regex_module

logger = logging.getLogger(__name__)


def _convert_management_numbers() -> int:
    """旧形式の管理番号を新形式 (XXXXXX) に変換

    変換ルール:
    - M25XXXX, P25XXXX → 作成日順に 000001 から連番
    - 25XXXXXX, 26XXXXXX (8桁) → 作成日順に 000001 から連番
    - 25-XXXXXX, 26-XXXXXX → 000001 から連番
    - XXXXXX (6桁) → 変換不要

    Returns:
        int: 変換した件数
    """
    try:
        with transaction.atomic():
            # 全案件を作成日時順に取得
            projects = Project.objects.all().order_by('created_at', 'id')

            # 新形式以外の案件を検出
            new_format_pattern = r'^\d{6}$'
            old_format_patterns = [
                r'^M25\d{4}$',      # M250001
                r'^P25\d{4}$',      # P250001
                r'^\d{8}$',         # 25000001, 26000001 など (8桁)
                r'^\d{2}-\d{6}$',   # 25-000001, 26-000001
            ]
            needs_conversion = []

            for proj in projects:
                if not proj.management_no:
                    continue
                # 新形式でない場合は変換対象
                if not regex_module.match(new_format_pattern, proj.management_no):
                    # 旧形式のいずれかにマッチするか確認
                    for pattern in old_format_patterns:
                        if regex_module.match(pattern, proj.management_no):
                            needs_conversion.append(proj)
                            break

            if not needs_conversion:
                return 0  # 変換不要

            # 作成日時順に連番を割り当て
            converted_count = 0
            for idx, proj in enumerate(projects, start=1):
                new_no = f'{idx:06d}'

                if proj.management_no != new_no:
                    proj.management_no = new_no
                    proj.save(update_fields=['management_no'])
                    converted_count += 1

            return converted_count

    except Exception as e:
        logger.error(f'管理番号変換エラー: {str(e)}')
        return 0


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
            clear_database = request.POST.get('clear_database') == 'true'

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
                    return _restore_from_zip(temp_file_path, clear_database=clear_database)

                # JSON形式の場合（後方互換性）
                else:
                    return _restore_from_json(temp_file_path, clear_database=clear_database)

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


def _restore_from_zip(zip_file_path: str, clear_database: bool = False) -> JsonResponse:
    """ZIPファイルからのリストア処理"""
    logger.info(f'ZIPファイルからのリストア開始: {zip_file_path}')

    # 0. データベースのクリア（clear_database=True の場合）
    if clear_database:
        logger.info('ステップ 0/5: データベースのクリア')
        try:
            from django.core.management import call_command
            call_command('flush', '--no-input', verbosity=0)
            logger.info('データベースをクリアしました')
        except Exception as e:
            logger.error(f'データベースクリアエラー: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': f'データベースのクリアに失敗しました: {str(e)}'
            }, status=500)

    # 1. バックアップファイルの検証
    logger.info('ステップ 1/5: バックアップファイルの検証')
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
    logger.info('ステップ 2/5: ZIPファイルの展開')
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
        logger.info('ステップ 3/5: データベースのインポート')
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

        # 3.5. 管理番号の自動変換
        logger.info('ステップ 3.5/5: 管理番号形式の変換')
        converted_count = _convert_management_numbers()
        logger.info(f'管理番号変換完了: {converted_count}件')

        # 4. メディアファイルの復元
        logger.info('ステップ 4/5: メディアファイルの復元')
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

        conversion_message = f'、{converted_count}件の管理番号を新形式に変換' if converted_count > 0 else ''

        return JsonResponse({
            'status': 'success',
            'message': 'データのインポートが完了しました',
            'details': f'{installed_count}個のオブジェクトがインポートされました{conversion_message}',
            'media_files': media_restored_count,
            'converted_management_numbers': converted_count,
            'warnings': error_text if error_text else None
        })


def _restore_from_json(json_file_path: str, clear_database: bool = False) -> JsonResponse:
    """JSONファイルからのリストア処理（後方互換性）"""
    logger.info(f'JSONファイルからのリストア開始: {json_file_path}')

    # 0. データベースのクリア（clear_database=True の場合）
    if clear_database:
        logger.info('データベースのクリア')
        try:
            from django.core.management import call_command
            call_command('flush', '--no-input', verbosity=0)
            logger.info('データベースをクリアしました')
        except Exception as e:
            logger.error(f'データベースクリアエラー: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': f'データベースのクリアに失敗しました: {str(e)}'
            }, status=500)

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


@login_required
@require_http_methods(["GET", "POST"])
def selective_restore_view(request):
    """
    選択的リストアビュー - バックアップから特定のモデルのみを復元

    機能:
    - バックアップファイル内のモデル一覧を表示
    - 復元するモデルを選択（チェックボックス）
    - 選択されたモデルのみをインポート

    使用例:
    - 下請け業者の追加項目設定のみを復元
    - プロジェクトデータのみを復元
    """
    if request.method == 'GET':
        return render(request, 'order_management/selective_restore.html')

    elif request.method == 'POST':
        try:
            # アクションタイプの判定
            action = request.POST.get('action', 'analyze')

            if action == 'analyze':
                # バックアップファイルの分析
                return _analyze_backup_file(request)
            elif action == 'restore':
                # 選択されたモデルの復元
                return _selective_restore(request)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '無効なアクションです'
                }, status=400)

        except Exception as e:
            import traceback
            logger.error(f'選択的リストアエラー: {str(e)}\n{traceback.format_exc()}')

            return JsonResponse({
                'status': 'error',
                'message': f'エラーが発生しました: {str(e)}'
            }, status=500)


def _analyze_backup_file(request) -> JsonResponse:
    """バックアップファイルを分析してモデル一覧を返す"""
    uploaded_file = request.FILES.get('backup_file')

    if not uploaded_file:
        return JsonResponse({
            'status': 'error',
            'message': 'ファイルが選択されていません'
        }, status=400)

    if not (uploaded_file.name.endswith('.zip') or uploaded_file.name.endswith('.json')):
        return JsonResponse({
            'status': 'error',
            'message': 'ZIPまたはJSONファイルのみ対応しています'
        }, status=400)

    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='wb', suffix=os.path.splitext(uploaded_file.name)[1], delete=False) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name

    try:
        # バックアップファイルからデータを読み込み
        if uploaded_file.name.endswith('.zip'):
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                    zip_file.extractall(temp_dir)

                data_json_path = os.path.join(temp_dir, 'data.json')

                with open(data_json_path, 'r', encoding='utf-8') as json_file:
                    data_list = json.load(json_file)
        else:
            # JSON形式
            with open(temp_file_path, 'r', encoding='utf-8') as json_file:
                data_list = json.load(json_file)

        # モデルごとの統計を集計
        model_stats = {}
        for item in data_list:
            model_name = item.get('model')
            if model_name:
                if model_name not in model_stats:
                    model_stats[model_name] = {
                        'count': 0,
                        'app_label': model_name.split('.')[0],
                        'model_name': model_name.split('.')[1] if '.' in model_name else model_name
                    }
                model_stats[model_name]['count'] += 1

        # カテゴリー別に整理
        categorized_models = {
            'subcontract_custom_fields': [],  # 下請け業者追加項目
            'project_data': [],               # 案件データ
            'contractor_data': [],            # 業者データ
            'settings': [],                   # 設定データ
            'other': []                       # その他
        }

        for model_name, stats in model_stats.items():
            # 表示用の名前を生成
            display_name = stats['model_name'].replace('_', ' ').title()

            model_info = {
                'model': model_name,
                'name': display_name,  # フロントエンドが期待する表示名
                'count': stats['count'],
                'app_label': stats['app_label'],
                'model_name': stats['model_name']
            }

            # カテゴリー振り分け
            if 'contractorfield' in model_name.lower():
                categorized_models['subcontract_custom_fields'].append(model_info)
            elif 'project' in model_name.lower():
                categorized_models['project_data'].append(model_info)
            elif 'contractor' in model_name.lower() or 'internalworker' in model_name.lower():
                categorized_models['contractor_data'].append(model_info)
            elif 'settings' in model_name.lower() or 'template' in model_name.lower():
                categorized_models['settings'].append(model_info)
            else:
                categorized_models['other'].append(model_info)

        # セッションに一時ファイルパスを保存（後で復元時に使用）
        request.session['temp_backup_file'] = temp_file_path
        request.session['backup_filename'] = uploaded_file.name

        return JsonResponse({
            'status': 'success',
            'message': 'バックアップファイルを分析しました',
            'total_objects': len(data_list),
            'total_models': len(model_stats),
            'models': categorized_models,  # フロントエンドが期待するキー名
            'backup_file_path': temp_file_path,  # フロントエンドが期待するキー名
            'backup_filename': uploaded_file.name
        })

    except Exception as e:
        # エラー時は一時ファイルを削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise


def _selective_restore(request) -> JsonResponse:
    """選択されたモデルのみを復元"""
    temp_file_path = request.session.get('temp_backup_file')

    if not temp_file_path or not os.path.exists(temp_file_path):
        return JsonResponse({
            'status': 'error',
            'message': 'バックアップファイルが見つかりません。再度アップロードしてください。'
        }, status=400)

    # 選択されたモデルを取得（チェックボックスから複数選択される）
    selected_models_list = request.POST.getlist('models')

    if not selected_models_list:
        return JsonResponse({
            'status': 'error',
            'message': '復元するモデルを選択してください'
        }, status=400)

    try:
        # バックアップファイルからデータを読み込み
        if temp_file_path.endswith('.zip'):
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                    zip_file.extractall(temp_dir)

                data_json_path = os.path.join(temp_dir, 'data.json')

                with open(data_json_path, 'r', encoding='utf-8') as json_file:
                    all_data = json.load(json_file)
        else:
            with open(temp_file_path, 'r', encoding='utf-8') as json_file:
                all_data = json.load(json_file)

        # 選択されたモデルのデータのみをフィルタリング
        filtered_data = [
            item for item in all_data
            if item.get('model') in selected_models_list
        ]

        if not filtered_data:
            return JsonResponse({
                'status': 'error',
                'message': '選択されたモデルのデータが見つかりませんでした'
            }, status=400)

        # フィルタリングされたデータを一時JSONファイルに保存
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_json:
            json.dump(filtered_data, temp_json, ensure_ascii=False, indent=2)
            filtered_json_path = temp_json.name

        try:
            # loaddataコマンドで選択されたデータのみをインポート
            output = io.StringIO()
            error_output = io.StringIO()

            call_command(
                'loaddata',
                filtered_json_path,
                verbosity=2,
                stdout=output,
                stderr=error_output
            )

            output_text = output.getvalue()
            error_text = error_output.getvalue()

            # インポートされたオブジェクト数を数える
            import re
            installed_match = re.search(r'Installed (\d+) object', output_text)
            installed_count = installed_match.group(1) if installed_match else len(filtered_data)

            logger.info(f'選択的リストア完了: {installed_count}個のオブジェクトを復元 (モデル: {", ".join(selected_models_list)})')

            return JsonResponse({
                'status': 'success',
                'message': '選択されたデータの復元が完了しました',
                'details': f'{installed_count}個のオブジェクトを復元しました',
                'restored_models': selected_models_list,
                'warnings': error_text if error_text else None
            })

        finally:
            # 一時JSONファイルを削除
            if os.path.exists(filtered_json_path):
                os.unlink(filtered_json_path)

    finally:
        # 元の一時バックアップファイルを削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        # セッションをクリア
        request.session.pop('temp_backup_file', None)
        request.session.pop('backup_filename', None)


@login_required
@require_http_methods(["GET", "POST"])
def delete_all_data_view(request):
    """
    全データ削除ビュー - データベースの全データを削除（ユーザーテーブルは保持）

    注意:
    - 削除前に自動バックアップを作成
    - 削除対象のプレビューを表示
    - 確認コードの入力が必要
    - ユーザーテーブル（auth.User）は保持される
    """
    from django.apps import apps

    if request.method == 'GET':
        # 削除対象のプレビューを取得
        try:
            deletion_preview = {}

            # 削除対象のモデルを取得（authアプリのUserは除く）
            for app_config in apps.get_app_configs():
                if app_config.name in ['order_management', 'subcontract_management']:
                    for model in app_config.get_models():
                        model_label = f'{app_config.label}.{model._meta.model_name}'
                        try:
                            count = model.objects.count()
                            if count > 0:
                                deletion_preview[model_label] = count
                        except Exception:
                            deletion_preview[model_label] = 0

            # レコード数でソート
            deletion_preview = dict(sorted(deletion_preview.items(), key=lambda x: x[1], reverse=True))
            total_records = sum(deletion_preview.values())

            return render(request, 'order_management/delete_all_data.html', {
                'deletion_preview': deletion_preview,
                'total_records': total_records
            })

        except Exception as e:
            import traceback
            logger.error(f'削除プレビューエラー: {str(e)}\n{traceback.format_exc()}')

            return render(request, 'order_management/delete_all_data.html', {
                'error': f'削除対象の取得中にエラーが発生しました: {str(e)}',
                'deletion_preview': {},
                'total_records': 0
            })

    elif request.method == 'POST':
        try:
            # 確認コードの検証
            confirmation_code = request.POST.get('confirmation_code', '').strip()

            if confirmation_code != 'DELETE':
                return JsonResponse({
                    'status': 'error',
                    'message': '確認コードが正しくありません。"DELETE" と入力してください。'
                }, status=400)

            # 1. 削除前の自動バックアップを作成
            logger.info('削除前の自動バックアップを作成中...')

            try:
                backups_dir = Path('./backups')
                backups_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backups_dir / f'pre_delete_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'

                # backup_data コマンドを呼び出し
                call_command(
                    'backup_data',
                    output=str(backup_path),
                    verbosity=0
                )

                logger.info(f'バックアップ作成完了: {backup_path}')

            except Exception as e:
                logger.error(f'バックアップ作成エラー: {str(e)}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'削除前のバックアップ作成に失敗しました: {str(e)}',
                    'details': 'データの安全性を確保するため、削除をキャンセルしました'
                }, status=500)

            # 2. データ削除の実行
            logger.info('データ削除を開始...')

            deleted_counts = {}

            # 削除順序（FK制約を考慮）
            deletion_order = [
                # order_management
                ('order_management', 'CommentAttachment'),
                ('order_management', 'CommentReadStatus'),
                ('order_management', 'Comment'),
                ('order_management', 'Notification'),
                ('order_management', 'ProjectFile'),
                ('order_management', 'ProjectChecklist'),
                ('order_management', 'InvoiceItem'),
                ('order_management', 'Invoice'),
                ('order_management', 'MaterialOrderItem'),
                ('order_management', 'MaterialOrder'),
                ('order_management', 'ApprovalLog'),
                ('order_management', 'ContractorReview'),
                ('order_management', 'ProjectProgressStep'),
                ('order_management', 'CashFlowTransaction'),
                ('order_management', 'FixedCost'),
                ('order_management', 'VariableCost'),
                ('order_management', 'ProjectProgress'),
                ('order_management', 'Report'),
                ('order_management', 'SeasonalityIndex'),
                ('order_management', 'ForecastScenario'),

                # subcontract_management
                ('subcontract_management', 'ProjectProfitAnalysis'),
                ('subcontract_management', 'Subcontract'),

                # order_management (FK依存がないもの)
                ('order_management', 'Project'),
                ('order_management', 'ContactPerson'),
                ('order_management', 'ClientCompany'),
                ('order_management', 'WorkType'),
                ('order_management', 'ChecklistTemplate'),
                ('order_management', 'ProgressStepTemplate'),
                ('order_management', 'RatingCriteria'),
                ('order_management', 'CompanySettings'),
                ('order_management', 'UserProfile'),
                ('order_management', 'Contractor'),  # Legacy model

                # subcontract_management
                ('subcontract_management', 'ContractorFieldDefinition'),
                ('subcontract_management', 'ContractorFieldCategory'),
                ('subcontract_management', 'Contractor'),
                ('subcontract_management', 'InternalWorker'),
            ]

            # 順番に削除
            for app_label, model_name in deletion_order:
                try:
                    Model = apps.get_model(app_label, model_name)
                    count = Model.objects.count()

                    if count > 0:
                        Model.objects.all().delete()
                        deleted_counts[f'{app_label}.{model_name}'] = count

                except LookupError:
                    # モデルが存在しない場合はスキップ
                    pass
                except Exception as e:
                    logger.warning(f'{app_label}.{model_name} の削除に失敗: {str(e)}')

            total_deleted = sum(deleted_counts.values())

            logger.info(f'データ削除完了: {total_deleted}件のレコードを削除')

            return JsonResponse({
                'status': 'success',
                'message': f'データの削除が完了しました',
                'details': f'{total_deleted}件のレコードを削除しました',
                'backup_path': str(backup_path),
                'deleted_counts': deleted_counts
            })

        except Exception as e:
            import traceback
            logger.error(f'削除処理エラー: {str(e)}\n{traceback.format_exc()}')

            return JsonResponse({
                'status': 'error',
                'message': f'削除処理中にエラーが発生しました: {str(e)}',
                'details': 'サーバーログを確認してください'
            }, status=500)
