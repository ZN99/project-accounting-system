"""完全リストアコマンド（CLI）

使用方法:
    python manage.py restore_data backup_20250117_123456.zip
    python manage.py restore_data backup.zip --dry-run
    python manage.py restore_data backup.zip --force
    python manage.py restore_data backup.zip -v 2
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.db import transaction
import json
import zipfile
import tempfile
import os
import shutil
import re
from pathlib import Path

from order_management.services.restore_validator import validate_restore
from order_management.models import Project


class Command(BaseCommand):
    help = 'バックアップファイル（ZIP）から完全リストアを実行します'

    def _convert_management_numbers(self, verbosity):
        """旧形式の管理番号を新形式に変換

        変換ルール:
        - M25XXXX, P25XXXX → 作成日順に 000001 から連番
        - 25XXXXXX, 26XXXXXX (8桁) → 作成日順に 000001 から連番
        - 25-XXXXXX, 26-XXXXXX → 000001 から連番（年プレフィックス削除）
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
                    if not re.match(new_format_pattern, proj.management_no):
                        # 旧形式のいずれかにマッチするか確認
                        for pattern in old_format_patterns:
                            if re.match(pattern, proj.management_no):
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

                        # 進捗表示
                        if verbosity >= 2 and converted_count % 50 == 0:
                            self.stdout.write(f'    変換中: {converted_count}件')

                return converted_count

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'    管理番号変換エラー: {str(e)}'))
            return 0

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='リストアするZIPファイルのパス'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際にはインポートせず、検証のみ実行'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='警告を無視して強制的にリストア'
        )

        parser.add_argument(
            '--clear',
            action='store_true',
            help='リストア前にデータベースをクリア（既存データを削除）'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        backup_file_path = options['backup_file']
        dry_run = options['dry_run']
        force = options['force']
        clear_db = options['clear']

        # ファイルの存在確認
        if not os.path.exists(backup_file_path):
            raise CommandError(f'ファイルが見つかりません: {backup_file_path}')

        try:
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING('完全リストアを開始します...'))
                if dry_run:
                    self.stdout.write(self.style.WARNING('（DRY-RUNモード: 実際にはインポートされません）'))
                if clear_db:
                    self.stdout.write(self.style.WARNING('（データベースクリアモード: 既存データを削除します）'))

            # 0. データベースのクリア（--clear オプション指定時）
            if clear_db and not dry_run:
                if verbosity >= 1:
                    self.stdout.write('\nステップ 0/4: データベースのクリア')

                # 確認プロンプト（--force がない場合）
                if not force:
                    response = input('\n⚠️  警告: すべての既存データが削除されます。続行しますか？ [y/N]: ')
                    if response.lower() != 'y':
                        self.stdout.write(self.style.ERROR('リストアを中止しました'))
                        return

                # flush_databaseコマンドを実行（ContentTypeも含めてクリア）
                if verbosity >= 1:
                    self.stdout.write('  データベースをクリアしています...')

                call_command('flush', '--no-input', verbosity=0)

                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS('  ✓ データベースをクリアしました'))

            # 1. バックアップファイルの検証
            if verbosity >= 1:
                self.stdout.write('\nステップ 1/4: バックアップファイルの検証')

            validation_result = validate_restore(backup_file_path)

            if not validation_result['success']:
                self.stdout.write(self.style.ERROR('❌ バックアップファイルに問題があります'))
                for error in validation_result['errors']:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))
                raise CommandError('バックアップファイル検証に失敗しました')

            if validation_result['warnings']:
                self.stdout.write(self.style.WARNING('\n⚠️  警告:'))
                for warning in validation_result['warnings'][:10]:  # 最初の10件のみ表示
                    self.stdout.write(self.style.WARNING(f'  - {warning}'))

                if not force and not dry_run:
                    response = input('\n警告がありますが、続行しますか？ [y/N]: ')
                    if response.lower() != 'y':
                        self.stdout.write(self.style.ERROR('リストアを中止しました'))
                        return

            # メタデータの表示
            metadata = validation_result.get('metadata', {})
            if verbosity >= 1 and metadata:
                self.stdout.write(self.style.SUCCESS('\nバックアップ情報:'))
                self.stdout.write(f'  作成日時: {metadata.get("created_at", "不明")}')
                self.stdout.write(f'  Djangoバージョン: {metadata.get("django_version", "不明")}')
                self.stdout.write(f'  総レコード数: {metadata.get("total_records", 0)}件')
                media_info = metadata.get('media_files', {})
                self.stdout.write(f'  メディアファイル: {media_info.get("count", 0)}個 ({media_info.get("total_size_mb", 0):.2f} MB)')

            if dry_run:
                self.stdout.write(self.style.SUCCESS('\n✅ DRY-RUN: バックアップファイルは正常です'))
                self.stdout.write(self.style.SUCCESS('実際のリストアを実行するには --dry-run オプションを外してください'))
                return

            # 2. ZIPファイルの展開
            if verbosity >= 1:
                self.stdout.write('\nステップ 2/4: ZIPファイルの展開')

            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_file_path, 'r') as zip_file:
                    zip_file.extractall(temp_dir)

                data_json_path = os.path.join(temp_dir, 'data.json')
                metadata_json_path = os.path.join(temp_dir, 'metadata.json')
                media_dir_path = os.path.join(temp_dir, 'media')

                # metadata.json を読み込み
                with open(metadata_json_path, 'r', encoding='utf-8') as meta_file:
                    metadata = json.load(meta_file)

                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS('  ✓ ZIPファイルを展開しました'))

                # 3. データベースのインポート
                if verbosity >= 1:
                    self.stdout.write('\nステップ 3/4: データベースのインポート')

                call_command(
                    'loaddata',
                    data_json_path,
                    verbosity=verbosity
                )

                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS('  ✓ データベースのインポートが完了しました'))

                # 3.5. 管理番号の自動変換
                if verbosity >= 1:
                    self.stdout.write('\nステップ 3.5/4: 管理番号形式の変換')

                converted_count = self._convert_management_numbers(verbosity)

                if verbosity >= 1:
                    if converted_count > 0:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {converted_count}件の管理番号を新形式に変換しました'))
                    else:
                        self.stdout.write(self.style.SUCCESS('  ✓ 管理番号はすでに新形式です'))

                # 4. メディアファイルの復元
                if verbosity >= 1:
                    self.stdout.write('\nステップ 4/4: メディアファイルの復元')

                media_restored_count = 0

                if os.path.exists(media_dir_path):
                    media_root = Path(settings.MEDIA_ROOT)
                    media_root.mkdir(parents=True, exist_ok=True)

                    media_files = list(Path(media_dir_path).rglob('*'))
                    total_files = len([f for f in media_files if f.is_file()])

                    for i, file_path in enumerate(media_files):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(media_dir_path)
                            destination = media_root / relative_path
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, destination)
                            media_restored_count += 1

                            # 進捗表示（100ファイルごと）
                            if verbosity >= 2 and (i + 1) % 100 == 0:
                                self.stdout.write(f'  処理中: {media_restored_count}/{total_files}ファイル')

                    if verbosity >= 1:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ メディアファイル {media_restored_count}個を復元しました'))
                else:
                    if verbosity >= 1:
                        self.stdout.write(self.style.WARNING('  ⊘ メディアファイルは含まれていません'))

            # 完了メッセージ
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS('\n✅ リストアが完了しました！'))
                self.stdout.write(self.style.SUCCESS(f'\nデータベースレコード: {metadata.get("total_records", 0)}件'))
                self.stdout.write(self.style.SUCCESS(f'メディアファイル: {media_restored_count}個'))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f'\n❌ エラーが発生しました: {str(e)}'))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise CommandError(f'リストアに失敗しました: {str(e)}')
