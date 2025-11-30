"""
今月の出金/入金管理のテストデータを生成する管理コマンド
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from order_management.models import Project, ClientCompany
from subcontract_management.models import Subcontract, Contractor


class Command(BaseCommand):
    help = '今月の出金/入金管理のテストデータを生成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存のテストデータをクリアしてから生成',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        year = now.year
        month = now.month

        self.stdout.write(f"\n{year}年{month}月のテストデータを生成します...\n")

        # 既存のクライアント企業と業者を取得、なければ作成
        client_company = self._get_or_create_client_company()
        contractors = self._get_or_create_contractors(3)

        # プロジェクトを作成
        projects = self._create_projects(client_company, year, month, count=5)

        # 各プロジェクトにSubcontractを作成
        for project in projects:
            self._create_subcontracts_for_project(project, contractors, year, month)

        self.stdout.write(self.style.SUCCESS(f"\n✅ テストデータの生成が完了しました！"))
        self.stdout.write(f"   プロジェクト: {len(projects)}件")
        self.stdout.write(f"   業者: {len(contractors)}社")
        self.stdout.write(f"\n📊 今月の出金/入金管理ページで確認してください:")
        self.stdout.write(f"   http://localhost:8000/orders/payment-management/\n")

    def _get_or_create_client_company(self):
        """テスト用のクライアント企業を取得または作成"""
        client, created = ClientCompany.objects.get_or_create(
            company_name='テスト建設株式会社',
            defaults={
                'address': '東京都新宿区西新宿1-1-1',
                'closing_day': 25,
                'payment_offset_months': 1,
                'payment_day': 5,
            }
        )
        if created:
            self.stdout.write(f"  ✓ クライアント企業を作成: {client.company_name}")
        else:
            self.stdout.write(f"  ✓ クライアント企業を使用: {client.company_name}")
        return client

    def _get_or_create_contractors(self, count):
        """テスト用の業者を取得または作成"""
        contractors = []
        contractor_names = [
            '鈴木建設', '佐藤電気工事', '田中設備',
            '高橋塗装', '伊藤内装', '渡辺左官'
        ]

        for i in range(min(count, len(contractor_names))):
            contractor, created = Contractor.objects.get_or_create(
                name=contractor_names[i],
                defaults={
                    'contact_person': f'{contractor_names[i]}担当者',
                    'phone': f'03-{1000+i}-{5000+i}',
                    'closing_day': 25,
                    'payment_offset_months': 1,
                    'payment_day': 5,
                }
            )
            if created:
                self.stdout.write(f"  ✓ 業者を作成: {contractor.name}")
            else:
                self.stdout.write(f"  ✓ 業者を使用: {contractor.name}")
            contractors.append(contractor)

        return contractors

    def _create_projects(self, client_company, year, month, count=5):
        """テスト用のプロジェクトを作成"""
        projects = []
        project_names = [
            '新宿オフィスビル改修工事',
            '渋谷商業施設内装工事',
            '品川マンション電気設備工事',
            '六本木ビル外壁塗装工事',
            '池袋店舗改装工事',
        ]

        # 今月の日付範囲
        start_of_month = datetime(year, month, 1).date()
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_of_month = datetime(year, month + 1, 1).date() - timedelta(days=1)

        for i in range(min(count, len(project_names))):
            # ランダムな日付を生成
            days_in_month = (end_of_month - start_of_month).days
            random_day = random.randint(5, min(days_in_month, 25))
            payment_due_date = start_of_month + timedelta(days=random_day)

            # プロジェクトの金額
            billing_amount = Decimal(random.choice([2000000, 3000000, 5000000, 8000000, 10000000]))

            # 80%の確率で入金済み
            if random.random() < 0.8:
                incoming_payment_status = 'received'
            else:
                incoming_payment_status = 'pending'

            project = Project.objects.create(
                site_name=project_names[i],
                client_company=client_company,
                order_amount=billing_amount,
                billing_amount=billing_amount,
                work_start_date=start_of_month,
                work_end_date=end_of_month,
                incoming_payment_status=incoming_payment_status,
                payment_due_date=payment_due_date,
                current_stage='construction',
                project_status='in_progress',
            )
            projects.append(project)

            status_label = '入金済み' if incoming_payment_status == 'received' else '入金待ち'
            self.stdout.write(f"  ✓ プロジェクト作成: {project.site_name} - {status_label} ¥{billing_amount:,}")

        return projects

    def _create_subcontracts_for_project(self, project, contractors, year, month):
        """プロジェクトに対してSubcontractを作成"""
        # 今月の日付範囲
        start_of_month = datetime(year, month, 1).date()
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_of_month = datetime(year, month + 1, 1).date() - timedelta(days=1)

        # 各プロジェクトに2-3件のSubcontractを作成
        num_subcontracts = random.randint(2, 3)

        for i in range(num_subcontracts):
            contractor = random.choice(contractors)

            # 契約金額
            contract_amount = Decimal(random.choice([500000, 800000, 1000000, 1500000, 2000000]))

            # ランダムな日付
            days_in_month = (end_of_month - start_of_month).days
            random_day = random.randint(1, min(days_in_month, 28))
            date_in_month = start_of_month + timedelta(days=random_day)

            # 支払いステータスをランダムに設定
            status_choice = random.random()
            if status_choice < 0.4:
                # 40%: 出金済み
                payment_status = 'paid'
                payment_date = date_in_month
                payment_due_date = date_in_month
                billed_amount = contract_amount
            elif status_choice < 0.6:
                # 20%: 出金予定（未払い）
                payment_status = 'pending'
                payment_date = None
                payment_due_date = date_in_month
                billed_amount = contract_amount
            elif status_choice < 0.75:
                # 15%: 出金予定（処理中）
                payment_status = 'processing'
                payment_date = None
                payment_due_date = date_in_month
                billed_amount = contract_amount
            else:
                # 25%: 未入力（被請求額または出金予定日が未設定）
                payment_status = 'pending'
                payment_date = None
                # ランダムで被請求額または出金予定日を未設定にする
                missing_choice = random.random()
                if missing_choice < 0.5:
                    # 被請求額のみ未設定
                    billed_amount = None
                    payment_due_date = date_in_month
                elif missing_choice < 0.8:
                    # 出金予定日のみ未設定
                    billed_amount = contract_amount
                    payment_due_date = None
                else:
                    # 両方未設定
                    billed_amount = None
                    payment_due_date = None

            subcontract = Subcontract.objects.create(
                project=project,
                site_name=f"{project.site_name} - {contractor.name}工事",
                contractor=contractor,
                worker_type='external',
                contract_amount=contract_amount,
                billed_amount=billed_amount,
                payment_status=payment_status,
                payment_date=payment_date,
                payment_due_date=payment_due_date,
            )

            if payment_status in ['paid', 'pending', 'processing'] and billed_amount is not None:
                status_label = {
                    'paid': '出金済み',
                    'pending': '未払い',
                    'processing': '処理中',
                }.get(payment_status, payment_status)
                self.stdout.write(
                    f"    → Subcontract: {contractor.name} - {status_label} ¥{billed_amount:,}"
                )
            else:
                missing_fields = []
                if billed_amount is None:
                    missing_fields.append('被請求額')
                if payment_due_date is None:
                    missing_fields.append('出金予定日')
                self.stdout.write(
                    f"    → Subcontract: {contractor.name} - 未入力 ({', '.join(missing_fields)})"
                )
