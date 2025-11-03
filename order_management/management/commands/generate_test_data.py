"""
テストデータ自動生成コマンド
デプロイ時に自動実行されるテストデータ生成スクリプト
"""
import os
import django
from django.core.management.base import BaseCommand
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()


class Command(BaseCommand):
    help = 'デプロイ時にテストデータを自動生成（約50件の案件）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='生成する案件数（デフォルト: 50）'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*50}'))
        self.stdout.write(self.style.SUCCESS(f'テストデータ自動生成を開始します'))
        self.stdout.write(self.style.SUCCESS(f'生成件数: {count}件'))
        self.stdout.write(self.style.SUCCESS(f'{"="*50}\n'))

        try:
            with transaction.atomic():
                # 既存のスクリプトを実行
                self._run_existing_scripts(count)
                
            self.stdout.write(self.style.SUCCESS('\n✅ テストデータの生成が完了しました！'))
            self.stdout.write(self.style.SUCCESS(f'合計 {count}件の案件データを生成しました。'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ エラーが発生しました: {str(e)}'))
            raise

    def _run_existing_scripts(self, count):
        """既存のcreate_*.pyスクリプトを実行"""
        import subprocess
        import sys
        
        scripts = [
            'create_realistic_data.py',
            'create_material_data.py',
            'create_payment_data.py',
            'create_survey_data.py',
        ]
        
        for script in scripts:
            script_path = os.path.join(os.getcwd(), script)
            if os.path.exists(script_path):
                self.stdout.write(f'🔄 {script} を実行中...')
                try:
                    subprocess.run(
                        [sys.executable, script_path],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {script} 完了'))
                except subprocess.CalledProcessError as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {script} スキップ: {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ {script} が見つかりません'))
