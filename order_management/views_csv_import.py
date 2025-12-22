"""
CSV一括インポート機能

受注側CSV・依頼側CSVをWebインターフェースからアップロードして
プロジェクトデータを一括インポートする機能
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from pathlib import Path
import tempfile
import os
import io
import threading
import uuid

from order_management.user_roles import role_required, UserRole
from order_management.utils.progress_tracker import ProgressTracker


def run_import_in_background(order_tmp_path, subcontract_tmp_path, dry_run, progress_file, result_holder):
    """
    バックグラウンドでCSVインポートを実行

    Args:
        order_tmp_path: 受注側CSVの一時ファイルパス
        subcontract_tmp_path: 依頼側CSVの一時ファイルパス
        dry_run: Dry-runモードかどうか
        progress_file: 進捗ファイルのパス
        result_holder: 結果を格納する辞書
    """
    tracker = ProgressTracker(progress_file)

    try:
        # 進捗更新: CSV読み込み開始
        tracker.add_log('=== CSVインポート開始 ===', 'info')
        tracker.add_log(f'受注側CSV: {order_tmp_path}', 'info')
        tracker.add_log(f'依頼側CSV: {subcontract_tmp_path}', 'info')
        tracker.add_log(f'Dry-runモード: {"ON" if dry_run else "OFF"}', 'info')

        tracker.update(
            status='processing',
            progress=10,
            message='CSVファイルを読み込んでいます...',
            step='reading_csv'
        )
        tracker.add_log('CSVファイルの読み込みを開始...', 'info')

        # キャンセルチェック
        if tracker.is_cancelled():
            tracker.add_log('ユーザーによってキャンセルされました', 'warning')
            result_holder['success'] = False
            result_holder['error'] = 'ユーザーによってキャンセルされました'
            return

        # コマンド実行（出力をキャプチャ）
        output = io.StringIO()

        # 進捗更新: データ検証
        tracker.update(
            status='processing',
            progress=25,
            message='データの検証を行っています...',
            step='validating'
        )
        tracker.add_log('データの整合性チェック中...', 'info')

        # キャンセルチェック
        if tracker.is_cancelled():
            tracker.add_log('ユーザーによってキャンセルされました', 'warning')
            result_holder['success'] = False
            result_holder['error'] = 'ユーザーによってキャンセルされました'
            return

        tracker.add_log('インポートコマンドを実行中...', 'info')
        tracker.update(
            status='processing',
            progress=40,
            message='プロジェクトデータをインポート中...',
            step='importing'
        )

        call_command(
            'import_project_csv',
            order_tmp_path,
            subcontract_tmp_path,
            dry_run=dry_run,
            verbosity=2,  # より詳細なログを出力
            stdout=output,
            progress_file=progress_file
        )

        # 出力を取得
        output_text = output.getvalue()

        # 進捗更新: 完了
        tracker.update(
            status='processing',
            progress=95,
            message='最終確認を行っています...',
            step='finalizing'
        )

        # 統計を抽出
        import re
        stats = {}

        tracker.add_log('インポート結果を解析中...', 'info')

        # プロジェクト数
        match = re.search(r'プロジェクト: (\d+)件作成', output_text)
        if match:
            stats['projects'] = int(match.group(1))
            tracker.add_log(f'✓ プロジェクト: {stats["projects"]}件作成', 'success')

        # 下請契約数
        match = re.search(r'下請契約: (\d+)件作成', output_text)
        if match:
            stats['subcontracts'] = int(match.group(1))
            tracker.add_log(f'✓ 下請契約: {stats["subcontracts"]}件作成', 'success')

        # スキップ数
        match = re.search(r'スキップ: (\d+)件', output_text)
        if match:
            stats['skipped'] = int(match.group(1))
            if stats['skipped'] > 0:
                tracker.add_log(f'⚠ スキップ: {stats["skipped"]}件', 'warning')

        # エラー数
        match = re.search(r'エラー: (\d+)件', output_text)
        if match:
            stats['errors'] = int(match.group(1))
            if stats['errors'] > 0:
                tracker.add_log(f'✗ エラー: {stats["errors"]}件', 'error')

        # 結果を保存
        result_holder['success'] = True
        result_holder['stats'] = stats
        result_holder['output'] = output_text
        result_holder['dry_run'] = dry_run

        tracker.add_log('=== インポート完了 ===', 'success')

        # 完了を記録（統計情報も含めて）
        tracker.complete(
            'インポートが完了しました',
            success=True,
            stats=stats,
            dry_run=dry_run
        )

    except Exception as e:
        result_holder['success'] = False
        result_holder['error'] = str(e)
        result_holder['output'] = output.getvalue() if 'output' in locals() else ''

        tracker.add_log(f'✗ エラーが発生しました: {str(e)}', 'error')
        tracker.error(f'エラー: {str(e)}')

    finally:
        # 一時ファイル削除
        try:
            os.unlink(order_tmp_path)
            os.unlink(subcontract_tmp_path)
        except:
            pass


@role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
def csv_import_view(request):
    """CSV一括インポート画面"""

    if request.method == 'POST':
        # ファイル取得
        order_csv_file = request.FILES.get('order_csv')
        subcontract_csv_file = request.FILES.get('subcontract_csv')
        dry_run = request.POST.get('dry_run') == 'on'

        # バリデーション
        if not order_csv_file or not subcontract_csv_file:
            messages.error(request, '両方のCSVファイルを選択してください。')
            return render(request, 'order_management/csv_import.html')

        # ファイルサイズチェック（100MB制限）
        max_size = 100 * 1024 * 1024  # 100MB
        if order_csv_file.size > max_size or subcontract_csv_file.size > max_size:
            messages.error(request, 'ファイルサイズが大きすぎます（最大100MB）。')
            return render(request, 'order_management/csv_import.html')

        # CSV拡張子チェック
        if not order_csv_file.name.endswith('.csv') or not subcontract_csv_file.name.endswith('.csv'):
            messages.error(request, 'CSVファイルのみアップロード可能です。')
            return render(request, 'order_management/csv_import.html')

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as order_tmp:
            for chunk in order_csv_file.chunks():
                order_tmp.write(chunk)
            order_tmp_path = order_tmp.name

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as subcontract_tmp:
            for chunk in subcontract_csv_file.chunks():
                subcontract_tmp.write(chunk)
            subcontract_tmp_path = subcontract_tmp.name

        # 進捗ファイルパスを生成（一意なID）
        import_id = str(uuid.uuid4())
        progress_file = os.path.join(tempfile.gettempdir(), f'csv_import_{import_id}.json')

        # セッションに進捗ファイルパスを保存
        request.session['csv_import_progress_file'] = progress_file
        request.session['csv_import_id'] = import_id

        # 結果を格納する辞書（スレッド間で共有）
        result_holder = {}

        # バックグラウンドスレッドでインポート実行
        import_thread = threading.Thread(
            target=run_import_in_background,
            args=(order_tmp_path, subcontract_tmp_path, dry_run, progress_file, result_holder)
        )
        import_thread.daemon = True
        import_thread.start()

        # 進捗ページにリダイレクト（インポート処理は裏で進行中）
        messages.info(request, 'CSVインポートを開始しました。処理が完了するまでお待ちください。')
        return redirect('order_management:csv_import')

    # GET: フォーム表示
    import_result = request.session.pop('import_result', None)

    context = {
        'import_result': import_result
    }

    return render(request, 'order_management/csv_import.html', context)


@role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
def csv_import_download_log(request):
    """インポートログのダウンロード"""

    output = request.session.get('import_result', {}).get('output', '')

    if not output:
        return HttpResponse('ログが見つかりません。', status=404)

    response = HttpResponse(output, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="import_log.txt"'

    return response


@role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
def csv_import_progress_api(request):
    """CSVインポート進捗取得API"""
    progress_file = request.session.get('csv_import_progress_file')

    if not progress_file:
        return JsonResponse({
            'status': 'idle',
            'progress': 0,
            'message': '',
            'step': ''
        })

    # 進捗ファイルから読み込み
    progress = ProgressTracker.read_progress(progress_file)

    # 完了・キャンセル・エラーの場合、進捗ファイルをクリーンアップ
    if progress and progress.get('status') in ['completed', 'cancelled', 'error']:
        try:
            ProgressTracker(progress_file).cleanup()
            # セッションからも削除
            request.session.pop('csv_import_progress_file', None)
            request.session.pop('csv_import_id', None)
        except:
            pass

    return JsonResponse(progress)


@role_required(UserRole.ACCOUNTING, UserRole.EXECUTIVE)
def csv_import_cancel_api(request):
    """CSVインポートキャンセルAPI"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POSTリクエストが必要です'}, status=400)

    progress_file = request.session.get('csv_import_progress_file')

    if not progress_file:
        return JsonResponse({'error': '進行中のインポートがありません'}, status=400)

    # キャンセルリクエストを送信
    tracker = ProgressTracker(progress_file)
    tracker.cancel()

    return JsonResponse({
        'success': True,
        'message': 'インポートをキャンセルしました'
    })
