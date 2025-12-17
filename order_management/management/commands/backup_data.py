"""完全バックアップコマンド（CLI）

使用方法:
    python manage.py backup_data
    python manage.py backup_data --output /path/to/backup.zip
    python manage.py backup_data --no-media
    python manage.py backup_data -v 2
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
import json
import zipfile
import io
from datetime import datetime
from pathlib import Path
import django

from order_management.services.backup_validator import validate_backup


class Command(BaseCommand):
    help = '完全バックアップを作成します（JSON + メディアファイル → ZIP）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            '-o',
            type=str,
            help='出力先のZIPファイルパス（デフォルト: ./backups/backup_YYYYMMDD_HHMMSS.zip）'
        )

        parser.add_argument(
            '--no-media',
            action='store_true',
            help='メディアファイルを除外してバックアップ（JSONのみ）'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        include_media = not options['no_media']

        # 出力先パスの決定
        if options['output']:
            output_path = Path(options['output'])
        else:
            backups_dir = Path('./backups')
            backups_dir.mkdir(parents=True, exist_ok=True)
            output_path = backups_dir / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'

        try:
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING('完全バックアップを開始します...'))

            # 1. データベース整合性の検証
            if verbosity >= 1:
                self.stdout.write('ステップ 1/5: データベース整合性検証')

            validation_result = validate_backup()

            if not validation_result['success']:
                self.stdout.write(self.style.ERROR('❌ データベースに整合性エラーがあります'))
                for error in validation_result['errors']:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))
                raise CommandError('データベース検証に失敗しました')

            if validation_result['warnings'] and verbosity >= 2:
                self.stdout.write(self.style.WARNING('⚠️  警告:'))
                for warning in validation_result['warnings'][:5]:  # 最初の5件のみ表示
                    self.stdout.write(self.style.WARNING(f'  - {warning}'))

            # 2. JSONデータのエクスポート
            if verbosity >= 1:
                self.stdout.write('ステップ 2/5: JSONデータのエクスポート')

            json_output = io.StringIO()
            call_command(
                'dumpdata',
                exclude=['sessions', 'admin.logentry'],
                indent=2,
                stdout=json_output,  # output ではなく stdout を使用
                verbosity=0
            )

            json_data = json_output.getvalue()
            data_list = json.loads(json_data)

            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {len(data_list)}個のオブジェクトをエクスポート'))

            # 3. メタデータの生成
            if verbosity >= 1:
                self.stdout.write('ステップ 3/5: メタデータの生成')

            metadata = {
                'backup_version': '1.0',
                'created_at': datetime.now().isoformat(),
                'django_version': django.get_version(),
                'database_engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
                'total_records': len(data_list),
                'models': validation_result['statistics'],
                'validation': {
                    'fk_integrity': 'passed',
                    'orphaned_records': len([w for w in validation_result['warnings'] if '孤立レコード' in w]),
                    'warnings': validation_result['warnings']
                }
            }

            # 4. メディアファイルの統計収集
            if verbosity >= 1:
                self.stdout.write('ステップ 4/5: メディアファイルの統計収集')

            media_root = Path(settings.MEDIA_ROOT)
            media_files_count = 0
            media_total_size = 0
            media_file_paths = []

            if include_media and media_root.exists():
                for file_path in media_root.rglob('*'):
                    if file_path.is_file():
                        media_files_count += 1
                        media_total_size += file_path.stat().st_size
                        media_file_paths.append(file_path)

            metadata['media_files'] = {
                'count': media_files_count,
                'total_size_mb': round(media_total_size / (1024 * 1024), 2),
                'included': include_media
            }

            if verbosity >= 1:
                if include_media:
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ メディアファイル: {media_files_count}個（合計 {metadata["media_files"]["total_size_mb"]:.2f} MB）'
                    ))
                else:
                    self.stdout.write(self.style.WARNING('  ⊘ メディアファイルは除外されました'))

            # 5. ZIPファイルの作成
            if verbosity >= 1:
                self.stdout.write('ステップ 5/5: ZIPファイルの作成')

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # data.json を追加
                zip_file.writestr('data.json', json_data)

                # metadata.json を追加
                zip_file.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))

                # media/ フォルダを追加
                if include_media and media_file_paths:
                    for i, file_path in enumerate(media_file_paths):
                        arcname = f'media/{file_path.relative_to(media_root)}'
                        zip_file.write(file_path, arcname)

                        # 進捗表示（100ファイルごと）
                        if verbosity >= 2 and (i + 1) % 100 == 0:
                            self.stdout.write(f'  処理中: {i + 1}/{media_files_count}ファイル')

            # 完了メッセージ
            zip_size_mb = output_path.stat().st_size / (1024 * 1024)

            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS('\n✅ バックアップが完了しました！'))
                self.stdout.write(self.style.SUCCESS(f'\n出力先: {output_path}'))
                self.stdout.write(self.style.SUCCESS(f'ファイルサイズ: {zip_size_mb:.2f} MB'))
                self.stdout.write(self.style.SUCCESS(f'データベースレコード: {len(data_list)}件'))
                if include_media:
                    self.stdout.write(self.style.SUCCESS(f'メディアファイル: {media_files_count}個'))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f'\n❌ エラーが発生しました: {str(e)}'))
            if verbosity >= 2:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise CommandError(f'バックアップに失敗しました: {str(e)}')
