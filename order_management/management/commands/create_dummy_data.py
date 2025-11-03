"""
ダミーデータ生成コマンド

Usage:
    python manage.py create_dummy_data
    python manage.py create_dummy_data --count 50
    python manage.py create_dummy_data --clear
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
from decimal import Decimal

from order_management.models import Project, UserProfile, Comment, Notification


class Command(BaseCommand):
    help = 'Generate dummy project data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of dummy projects to create (default: 30)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing projects before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('既存のプロジェクトデータを削除中...'))
            Project.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('削除完了'))

        # ユーザーとプロフィールの作成
        self.create_users()

        # ダミープロジェクトの作成
        self.stdout.write(f'{count}件のダミープロジェクトを作成中...')
        created_count = self.create_dummy_projects(count)

        self.stdout.write(self.style.SUCCESS(f'✓ {created_count}件のプロジェクトを作成しました'))

    def create_users(self):
        """テストユーザーとプロフィールを作成"""
        # スーパーユーザー（役員）
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=admin,
                defaults={'roles': ['executive', 'headquarters']}
            )
            self.stdout.write('✓ 役員ユーザー作成: admin/admin123')

        # 営業担当
        sales_users = ['tanaka', 'suzuki', 'sato']
        for username in sales_users:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@example.com',
                    password='password123',
                    first_name=username.capitalize(),
                    last_name='Sales'
                )
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'roles': ['headquarters']}
                )

        # 職人発注担当
        if not User.objects.filter(username='craftsman').exists():
            user = User.objects.create_user(
                'craftsman', 'craftsman@example.com', 'password123'
            )
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'roles': ['craftsman_order', 'headquarters']}
            )

        # 経理担当
        if not User.objects.filter(username='accounting').exists():
            user = User.objects.create_user(
                'accounting', 'accounting@example.com', 'password123'
            )
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'roles': ['accounting', 'headquarters']}
            )

    def create_dummy_projects(self, count):
        """ダミープロジェクトを生成"""

        # サンプルデータ
        client_names = [
            '大成建設', '鹿島建設', '清水建設', '竹中工務店', '大林組',
            '前田建設', '西松建設', '戸田建設', '安藤ハザマ', '熊谷組',
            '三井住友建設', '東急建設', '長谷工コーポレーション'
        ]

        site_bases = [
            '新宿オフィス', '渋谷商業施設', '横浜マンション', '品川オフィスビル',
            '池袋複合施設', '六本木タワー', '川崎工場', '千葉倉庫',
            '埼玉住宅', '神奈川店舗', '東京ホテル', '銀座ビル'
        ]

        work_types = [
            '電気工事', '空調工事', '給排水工事', '内装工事',
            '外装工事', '防水工事', '塗装工事', '足場工事'
        ]

        statuses = ['ネタ', '施工日待ち', '進行中', '完工', 'NG']
        status_weights = [15, 25, 35, 20, 5]  # 確率の重み付け

        managers = ['田中太郎', '鈴木次郎', '佐藤三郎', '高橋四郎']

        created = 0
        today = date.today()

        for i in range(count):
            # ランダムなデータ生成
            client = random.choice(client_names)
            site_name = f'{random.choice(site_bases)}{i+1}号棟'
            work_type = random.choice(work_types)
            status = random.choices(statuses, weights=status_weights)[0]
            manager = random.choice(managers)

            # 金額設定（100万〜5000万円）
            order_amount = Decimal(random.randint(100, 5000)) * Decimal('10000')

            # 工事期間の設定
            if status == 'ネタ':
                # ネタ：未定
                work_start_date = None
                work_end_date = None
            elif status == '施工日待ち':
                # 施工日待ち：1-4週間後開始
                days_until_start = random.randint(7, 28)
                work_start_date = today + timedelta(days=days_until_start)
                work_end_date = work_start_date + timedelta(days=random.randint(10, 60))
            elif status == '進行中':
                # 進行中：すでに開始、1-8週間後終了
                work_start_date = today - timedelta(days=random.randint(1, 30))
                work_end_date = today + timedelta(days=random.randint(7, 56))
            elif status == '完工':
                # 完工：過去に終了
                work_end_date = today - timedelta(days=random.randint(1, 90))
                work_start_date = work_end_date - timedelta(days=random.randint(10, 60))
            else:  # NG
                # NG：過去の日付
                work_start_date = today - timedelta(days=random.randint(30, 180))
                work_end_date = None

            # 入金日の設定
            if status in ['進行中', '完工']:
                payment_due_date = work_end_date + timedelta(days=random.randint(30, 60)) if work_end_date else None
            else:
                payment_due_date = work_end_date + timedelta(days=random.randint(30, 60)) if work_end_date else today + timedelta(days=random.randint(30, 90))

            try:
                project = Project.objects.create(
                    client_name=client,
                    site_name=site_name,
                    work_type=work_type,
                    order_amount=order_amount,
                    project_status=status,
                    project_manager=manager,
                    work_start_date=work_start_date,
                    work_end_date=work_end_date,
                    payment_due_date=payment_due_date,
                    notes=f'ダミーデータ #{i+1}',
                    created_at=timezone.now() - timedelta(days=random.randint(0, 90))
                )
                created += 1

                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  {i + 1}/{count} 作成完了...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ エラー: {str(e)}'))

        return created
