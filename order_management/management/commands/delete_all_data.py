"""全データベースデータ削除コマンド（CLI）

使用方法:
    python manage.py delete_all_data
    python manage.py delete_all_data --force
    python manage.py delete_all_data --no-backup
    python manage.py delete_all_data -v 2

⚠️ 警告: このコマンドは全てのデータベースデータを削除します！
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from django.apps import apps
from django.contrib.auth.models import User
from datetime import datetime
from pathlib import Path
import io


class Command(BaseCommand):
    help = '⚠️  全データベースデータを削除します（ユーザーテーブルは保持）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='確認なしで強制的に削除'
        )

        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='削除前の自動バックアップをスキップ'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        force = options['force']
        no_backup = options['no_backup']

        try:
            # 警告メッセージ
            if verbosity >= 1:
                self.stdout.write(self.style.ERROR('\n' + '='*60))
                self.stdout.write(self.style.ERROR('⚠️  警告: 全データベースデータ削除'))
                self.stdout.write(self.style.ERROR('='*60))
                self.stdout.write(self.style.WARNING('\nこのコマンドは以下のデータを削除します：'))

            # 削除対象のプレビュー
            deletion_stats = self._get_deletion_preview()

            if verbosity >= 1:
                self.stdout.write('')
                for model_label, count in deletion_stats.items():
                    if count > 0:
                        self.stdout.write(f'  - {model_label}: {count}件')

                total_records = sum(deletion_stats.values())
                self.stdout.write(self.style.WARNING(f'\n合計: {total_records}件のレコードが削除されます'))
                self.stdout.write(self.style.SUCCESS('\n✓ ユーザーテーブル（auth.User）は保持されます'))

            # 確認コードの入力
            if not force:
                self.stdout.write(self.style.ERROR('\n本当に削除しますか？'))
                self.stdout.write('削除を実行するには "DELETE" と入力してください:')
                confirmation = input('> ').strip()

                if confirmation != 'DELETE':
                    self.stdout.write(self.style.ERROR('\n削除をキャンセルしました'))
                    return

            # 自動バックアップの作成
            if not no_backup:
                if verbosity >= 1:
                    self.stdout.write(self.style.WARNING('\n削除前の自動バックアップを作成中...'))

                try:
                    backups_dir = Path('./backups')
                    backups_dir.mkdir(parents=True, exist_ok=True)
                    backup_path = backups_dir / f'pre_delete_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'

                    # backup_data コマンドを呼び出し
                    call_command(
                        'backup_data',
                        output=str(backup_path),
                        verbosity=0 if verbosity < 2 else 1
                    )

                    if verbosity >= 1:
                        self.stdout.write(self.style.SUCCESS(f'✓ バックアップ作成完了: {backup_path}'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'\n❌ バックアップ作成エラー: {str(e)}'))
                    if not force:
                        response = input('\nバックアップに失敗しましたが、続行しますか？ [y/N]: ')
                        if response.lower() != 'y':
                            self.stdout.write(self.style.ERROR('削除をキャンセルしました'))
                            return

            # データ削除の実行
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING('\nデータ削除を開始します...'))

            deleted_counts = self._delete_all_data(verbosity)

            # 完了メッセージ
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS('\n✅ データ削除が完了しました！'))
                self.stdout.write(self.style.SUCCESS(f'\n削除されたレコード数:'))
                for model_label, count in sorted(deleted_counts.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        self.stdout.write(f'  - {model_label}: {count}件')

                total_deleted = sum(deleted_counts.values())
                self.stdout.write(self.style.SUCCESS(f'\n合計: {total_deleted}件のレコードを削除しました'))

                if not no_backup:
                    self.stdout.write(self.style.SUCCESS(f'\nバックアップファイル: {backup_path}'))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f'\n❌ エラーが発生しました: {str(e)}'))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise CommandError(f'データ削除に失敗しました: {str(e)}')

    def _get_deletion_preview(self):
        """削除対象のプレビューを取得"""
        deletion_stats = {}

        # 削除対象のモデルを取得（authアプリのUserは除く）
        for app_config in apps.get_app_configs():
            if app_config.name in ['order_management', 'subcontract_management']:
                for model in app_config.get_models():
                    model_label = f'{app_config.label}.{model._meta.model_name}'
                    try:
                        count = model.objects.count()
                        deletion_stats[model_label] = count
                    except Exception:
                        deletion_stats[model_label] = 0

        return deletion_stats

    def _delete_all_data(self, verbosity):
        """全データを削除（Userテーブルは保持）"""
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
                    if verbosity >= 2:
                        self.stdout.write(f'  削除中: {app_label}.{model_name} ({count}件)')

                    Model.objects.all().delete()
                    deleted_counts[f'{app_label}.{model_name}'] = count

            except LookupError:
                # モデルが存在しない場合はスキップ
                if verbosity >= 2:
                    self.stdout.write(f'  スキップ: {app_label}.{model_name} (モデルが存在しません)')
            except Exception as e:
                if verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f'  警告: {app_label}.{model_name} の削除に失敗: {str(e)}'))

        return deleted_counts
