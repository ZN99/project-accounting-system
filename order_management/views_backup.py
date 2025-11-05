"""
データバックアップ・復元機能

案件管理システムの全データをJSON形式でエクスポート・インポートする機能を提供します。
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.core import serializers
from django.apps import apps
import json
from datetime import datetime
import traceback


def is_staff_user(user):
    """スタッフユーザーかチェック"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_user)
def export_data(request):
    """
    全データをJSON形式でエクスポート
    """
    try:
        # エクスポートするモデルのリスト
        models_to_export = [
            'order_management.Project',
            'order_management.Contractor',
            'subcontract_management.InternalWorker',
            'subcontract_management.Subcontract',
        ]

        export_data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0',
            'data': {}
        }

        # 各モデルのデータをシリアライズ
        for model_name in models_to_export:
            try:
                Model = apps.get_model(model_name)
                model_key = model_name.split('.')[-1].lower()

                # データをシリアライズ
                data = serializers.serialize('python', Model.objects.all())
                export_data['data'][model_key] = data

            except Exception as e:
                export_data['data'][model_key] = []
                export_data[f'{model_key}_error'] = str(e)

        # JSON形式でダウンロード
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'project_accounting_backup_{timestamp}.json'

        response = HttpResponse(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f'エクスポートエラー: {str(e)}')
        return redirect('order_management:dashboard')


@login_required
@user_passes_test(is_staff_user)
def import_data_view(request):
    """
    データインポート画面
    """
    if request.method == 'POST':
        try:
            # アップロードされたファイルを取得
            if 'backup_file' not in request.FILES:
                messages.error(request, 'ファイルが選択されていません。')
                return redirect('order_management:import_data')

            backup_file = request.FILES['backup_file']

            # JSONファイルかチェック
            if not backup_file.name.endswith('.json'):
                messages.error(request, 'JSONファイルを選択してください。')
                return redirect('order_management:import_data')

            # ファイルを読み込む
            file_content = backup_file.read().decode('utf-8')
            import_data = json.loads(file_content)

            # バージョンチェック
            if 'version' not in import_data:
                messages.error(request, '無効なバックアップファイル形式です。')
                return redirect('order_management:import_data')

            # インポートモード（上書き or 追加）
            import_mode = request.POST.get('import_mode', 'add')

            # データをインポート
            with transaction.atomic():
                imported_counts = {}

                # モデルの順序（外部キー制約を考慮）
                import_order = [
                    ('contractor', 'order_management.Contractor'),
                    ('internalworker', 'subcontract_management.InternalWorker'),
                    ('project', 'order_management.Project'),
                    ('subcontract', 'subcontract_management.Subcontract'),
                ]

                for model_key, model_name in import_order:
                    if model_key in import_data.get('data', {}):
                        Model = apps.get_model(model_name)
                        model_data = import_data['data'][model_key]

                        count = 0
                        for item in model_data:
                            pk = item['pk']
                            fields = item['fields']

                            if import_mode == 'overwrite':
                                # 上書きモード
                                Model.objects.update_or_create(
                                    pk=pk,
                                    defaults=fields
                                )
                            else:
                                # 追加モード（既存データはスキップ）
                                if not Model.objects.filter(pk=pk).exists():
                                    obj = Model(**fields)
                                    obj.pk = pk
                                    obj.save()

                            count += 1

                        imported_counts[model_key] = count

            # 成功メッセージ
            summary = ', '.join([f'{k}: {v}件' for k, v in imported_counts.items()])
            messages.success(
                request,
                f'データのインポートが完了しました。({summary})'
            )

            return redirect('order_management:dashboard')

        except json.JSONDecodeError:
            messages.error(request, 'JSONファイルの解析に失敗しました。')
            return redirect('order_management:import_data')
        except Exception as e:
            messages.error(request, f'インポートエラー: {str(e)}\n{traceback.format_exc()}')
            return redirect('order_management:import_data')

    return render(request, 'order_management/import_data.html')
