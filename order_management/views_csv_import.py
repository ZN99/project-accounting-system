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

from order_management.user_roles import executive_required, UserRole


@executive_required
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
        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as order_tmp:
                for chunk in order_csv_file.chunks():
                    order_tmp.write(chunk)
                order_tmp_path = order_tmp.name

            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as subcontract_tmp:
                for chunk in subcontract_csv_file.chunks():
                    subcontract_tmp.write(chunk)
                subcontract_tmp_path = subcontract_tmp.name

            # コマンド実行（出力をキャプチャ）
            output = io.StringIO()

            try:
                call_command(
                    'import_project_csv',
                    order_tmp_path,
                    subcontract_tmp_path,
                    dry_run=dry_run,
                    verbosity=1,
                    stdout=output
                )

                # 出力を取得
                output_text = output.getvalue()

                # 統計を抽出
                import re
                stats = {}

                # プロジェクト数
                match = re.search(r'プロジェクト: (\d+)件作成', output_text)
                if match:
                    stats['projects'] = int(match.group(1))

                # 下請契約数
                match = re.search(r'下請契約: (\d+)件作成', output_text)
                if match:
                    stats['subcontracts'] = int(match.group(1))

                # スキップ数
                match = re.search(r'スキップ: (\d+)件', output_text)
                if match:
                    stats['skipped'] = int(match.group(1))

                # エラー数
                match = re.search(r'エラー: (\d+)件', output_text)
                if match:
                    stats['errors'] = int(match.group(1))

                # セッションに結果を保存
                request.session['import_result'] = {
                    'success': True,
                    'stats': stats,
                    'output': output_text,
                    'dry_run': dry_run
                }

                if dry_run:
                    messages.success(request, f'✅ Dry-run完了: プロジェクト{stats.get("projects", 0)}件、下請契約{stats.get("subcontracts", 0)}件（データは保存されていません）')
                else:
                    messages.success(request, f'✅ インポート完了: プロジェクト{stats.get("projects", 0)}件、下請契約{stats.get("subcontracts", 0)}件作成')

                return redirect('csv_import')

            except Exception as e:
                request.session['import_result'] = {
                    'success': False,
                    'error': str(e),
                    'output': output.getvalue()
                }
                messages.error(request, f'❌ インポートエラー: {str(e)}')
                return redirect('csv_import')

        finally:
            # 一時ファイル削除
            try:
                os.unlink(order_tmp_path)
                os.unlink(subcontract_tmp_path)
            except:
                pass

    # GET: フォーム表示
    import_result = request.session.pop('import_result', None)

    context = {
        'import_result': import_result
    }

    return render(request, 'order_management/csv_import.html', context)


@executive_required
def csv_import_download_log(request):
    """インポートログのダウンロード"""

    output = request.session.get('import_result', {}).get('output', '')

    if not output:
        return HttpResponse('ログが見つかりません。', status=404)

    response = HttpResponse(output, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="import_log.txt"'

    return response
