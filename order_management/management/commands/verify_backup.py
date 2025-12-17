"""バックアップファイル検証コマンド（CLI）

使用方法:
    python manage.py verify_backup backup_20250117_123456.zip
    python manage.py verify_backup backup.zip --detailed
    python manage.py verify_backup backup.zip -v 2
"""

from django.core.management.base import BaseCommand, CommandError
import os

from order_management.services.restore_validator import validate_restore


class Command(BaseCommand):
    help = 'バックアップファイル（ZIP）の整合性を検証します'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='検証するZIPファイルのパス'
        )

        parser.add_argument(
            '--detailed',
            action='store_true',
            help='詳細な検証レポートを表示'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        backup_file_path = options['backup_file']
        detailed = options['detailed']

        # ファイルの存在確認
        if not os.path.exists(backup_file_path):
            raise CommandError(f'ファイルが見つかりません: {backup_file_path}')

        try:
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING(f'バックアップファイルの検証を開始します: {backup_file_path}\n'))

            # バックアップファイルの検証
            validation_result = validate_restore(backup_file_path)

            # 成功/失敗の判定
            if validation_result['success']:
                self.stdout.write(self.style.SUCCESS('✅ バックアップファイルは正常です'))
            else:
                self.stdout.write(self.style.ERROR('❌ バックアップファイルに問題があります'))

            # メタデータの表示
            metadata = validation_result.get('metadata', {})
            if metadata:
                self.stdout.write(self.style.SUCCESS('\n📦 バックアップ情報:'))
                self.stdout.write(f'  バックアップバージョン: {metadata.get("backup_version", "不明")}')
                self.stdout.write(f'  作成日時: {metadata.get("created_at", "不明")}')
                self.stdout.write(f'  Djangoバージョン: {metadata.get("django_version", "不明")}')
                self.stdout.write(f'  データベースエンジン: {metadata.get("database_engine", "不明")}')
                self.stdout.write(f'  総レコード数: {metadata.get("total_records", 0):,}件')

                media_info = metadata.get('media_files', {})
                self.stdout.write(f'  メディアファイル: {media_info.get("count", 0):,}個 ({media_info.get("total_size_mb", 0):.2f} MB)')

                # モデル別統計（詳細モード）
                if detailed:
                    models = metadata.get('models', {})
                    if models:
                        self.stdout.write(self.style.SUCCESS('\n📊 モデル別レコード数:'))
                        # レコード数でソート
                        sorted_models = sorted(models.items(), key=lambda x: x[1], reverse=True)
                        for model, count in sorted_models[:20]:  # 上位20件のみ表示
                            self.stdout.write(f'  {model}: {count:,}件')
                        if len(sorted_models) > 20:
                            self.stdout.write(f'  ...他 {len(sorted_models) - 20}モデル')

                # 検証結果（詳細モード）
                if detailed:
                    validation_info = metadata.get('validation', {})
                    if validation_info:
                        self.stdout.write(self.style.SUCCESS('\n🔍 データベース整合性:'))
                        self.stdout.write(f'  FK整合性: {validation_info.get("fk_integrity", "不明")}')
                        self.stdout.write(f'  孤立レコード: {validation_info.get("orphaned_records", 0)}件')

            # 情報メッセージの表示
            if validation_result['info'] and detailed:
                self.stdout.write(self.style.SUCCESS('\nℹ️  情報:'))
                for info in validation_result['info'][:10]:  # 最初の10件のみ表示
                    self.stdout.write(f'  {info}')

            # 警告メッセージの表示
            if validation_result['warnings']:
                self.stdout.write(self.style.WARNING('\n⚠️  警告:'))
                display_warnings = validation_result['warnings'][:10] if not detailed else validation_result['warnings']
                for warning in display_warnings:
                    self.stdout.write(self.style.WARNING(f'  {warning}'))
                if not detailed and len(validation_result['warnings']) > 10:
                    self.stdout.write(self.style.WARNING(f'  ...他 {len(validation_result["warnings"]) - 10}件の警告'))
                    self.stdout.write(self.style.WARNING('  （全ての警告を表示するには --detailed オプションを使用してください）'))

            # エラーメッセージの表示
            if validation_result['errors']:
                self.stdout.write(self.style.ERROR('\n❌ エラー:'))
                for error in validation_result['errors']:
                    self.stdout.write(self.style.ERROR(f'  {error}'))

            # まとめ
            self.stdout.write('')
            if validation_result['success']:
                if validation_result['warnings']:
                    self.stdout.write(self.style.WARNING(
                        f'✓ 検証完了: {len(validation_result["warnings"])}件の警告がありますが、リストア可能です'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS('✓ 検証完了: 問題はありません'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'✗ 検証失敗: {len(validation_result["errors"])}件のエラーがあります'
                ))
                raise CommandError('バックアップファイルに問題があります')

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f'\n❌ エラーが発生しました: {str(e)}'))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise CommandError(f'検証に失敗しました: {str(e)}')
