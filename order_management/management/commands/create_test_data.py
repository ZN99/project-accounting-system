"""
テストデータ生成コマンド

網羅的なテストデータをJSON形式で生成し、バックアップから復元可能な形式で出力します。

使用方法:
    python manage.py create_test_data --output test_data.json
"""

from django.core.management.base import BaseCommand
from django.core import serializers
from django.contrib.auth import get_user_model
from order_management.models import (
    ClientCompany, Project, ProjectProgressStep, ProgressStepTemplate
)
from subcontract_management.models import Contractor, Subcontract
from decimal import Decimal
from datetime import date, timedelta
import random
import json

User = get_user_model()


class Command(BaseCommand):
    help = '網羅的なテストデータをJSON形式で生成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='test_data_comprehensive.json',
            help='出力ファイルパス'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存データをクリアしてから生成'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        clear_data = options['clear']

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('テストデータ生成開始'))
        self.stdout.write('=' * 70)

        if clear_data:
            self.stdout.write(self.style.WARNING('\n既存データをクリア中...'))
            self._clear_data()

        # データ生成
        client_companies = self._create_client_companies()
        contractors = self._create_contractors()
        projects = self._create_projects(client_companies)
        progress_steps = self._create_progress_steps(projects)
        subcontracts = self._create_subcontracts(projects, contractors)

        # JSON出力
        self._export_to_json(
            output_file,
            client_companies,
            contractors,
            projects,
            progress_steps,
            subcontracts
        )

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'✅ テストデータ生成完了: {output_file}'))
        self.stdout.write('=' * 70)

    def _clear_data(self):
        """既存データをクリア"""
        Subcontract.objects.all().delete()
        ProjectProgressStep.objects.all().delete()
        Project.objects.all().delete()
        ClientCompany.objects.all().delete()
        Contractor.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  ✓ 既存データをクリアしました'))

    def _create_client_companies(self):
        """元請会社8社を作成"""
        self.stdout.write('\n📊 元請会社を作成中...')

        companies_data = [
            {
                'company_name': 'K2プラネット株式会社',
                'address': '東京都港区六本木1-2-3',
                'payment_cycle': '月1回',
                'closing_day': 31,
                'payment_day': 31,
                'payment_offset_months': 1,
                'managed_units': 100,
            },
            {
                'company_name': '大成建設株式会社',
                'address': '東京都新宿区西新宿2-1-1',
                'payment_cycle': '月1回',
                'closing_day': 20,
                'payment_day': 20,
                'payment_offset_months': 1,
                'managed_units': 200,
            },
            {
                'company_name': '鹿島建設株式会社',
                'address': '東京都港区元赤坂1-3-1',
                'payment_cycle': '月1回',
                'closing_day': 31,
                'payment_day': 5,
                'payment_offset_months': 2,
                'managed_units': 150,
            },
            {
                'company_name': '清水建設株式会社',
                'address': '東京都中央区京橋2-16-1',
                'payment_cycle': '月1回',
                'closing_day': 20,
                'payment_day': 31,
                'payment_offset_months': 1,
                'managed_units': 180,
            },
            {
                'company_name': '竹中工務店',
                'address': '大阪府大阪市中央区本町4-1-13',
                'payment_cycle': '月1回',
                'closing_day': 31,
                'payment_day': 25,
                'payment_offset_months': 1,
                'managed_units': 120,
            },
            {
                'company_name': '株式会社フジタ',
                'address': '東京都渋谷区千駄ヶ谷4-25-2',
                'payment_cycle': '月1回',
                'closing_day': 31,
                'payment_day': 31,
                'payment_offset_months': 1,
                'managed_units': 90,
            },
            {
                'company_name': '戸田建設株式会社',
                'address': '東京都中央区京橋1-7-1',
                'payment_cycle': '月2回',
                'closing_day': 15,
                'payment_day': 10,
                'payment_offset_months': 1,
                'managed_units': 110,
            },
            {
                'company_name': '三井住友建設株式会社',
                'address': '東京都中央区佃2-1-6',
                'payment_cycle': '月1回',
                'closing_day': 31,
                'payment_day': 20,
                'payment_offset_months': 1,
                'managed_units': 130,
            },
        ]

        companies = []
        for data in companies_data:
            company, created = ClientCompany.objects.get_or_create(
                company_name=data['company_name'],
                defaults=data
            )
            companies.append(company)
            status = '作成' if created else '既存'
            self.stdout.write(f'  {status}: {company.company_name}')

        self.stdout.write(self.style.SUCCESS(f'  ✓ 元請会社: {len(companies)}社作成完了'))
        return companies

    def _create_contractors(self):
        """下請け業者8社を作成"""
        self.stdout.write('\n👷 下請け業者を作成中...')

        contractors_data = [
            {
                'name': 'プロプラ',
                'address': 'さいたま市大宮区大門町2-1-1',
                'phone': '048-1234-5678',
                'email': 'info@propra.co.jp',
                'contractor_type': 'partner',
                'specialties': 'クリーニング',
                'closing_day': 31,
                'hourly_rate': Decimal('3000'),
            },
            {
                'name': '株式会社Sways',
                'address': 'ふじみ野市うれし野2-10-1',
                'phone': '049-2345-6789',
                'email': 'contact@sways.co.jp',
                'contractor_type': 'partner',
                'specialties': 'クロス',
                'closing_day': 31,
                'hourly_rate': Decimal('3500'),
            },
            {
                'name': '山田電気工事',
                'address': '川越市脇田町105-1',
                'phone': '049-3456-7890',
                'email': 'yamada@example.com',
                'contractor_type': 'partner',
                'specialties': '電気工事',
                'closing_day': 15,
                'hourly_rate': Decimal('4000'),
            },
            {
                'name': '鈴木設備工業',
                'address': '所沢市日吉町12-34',
                'phone': '04-4567-8901',
                'email': 'suzuki@example.com',
                'contractor_type': 'partner',
                'specialties': '配管・設備',
                'closing_day': 20,
                'hourly_rate': Decimal('3800'),
            },
            {
                'name': '田中塗装',
                'address': '入間市豊岡1-16-1',
                'phone': '04-5678-9012',
                'email': 'tanaka@example.com',
                'contractor_type': 'partner',
                'specialties': '塗装',
                'closing_day': 31,
                'hourly_rate': Decimal('3200'),
            },
            {
                'name': '佐藤建材',
                'address': '狭山市入間川1-3-1',
                'phone': '04-6789-0123',
                'email': 'sato@example.com',
                'contractor_type': 'supplier',
                'specialties': '建材供給',
                'closing_day': 31,
                'hourly_rate': Decimal('0'),
            },
            {
                'name': '高橋左官工業',
                'address': '川口市栄町3-8-15',
                'phone': '048-7890-1234',
                'email': 'takahashi@example.com',
                'contractor_type': 'partner',
                'specialties': '左官',
                'closing_day': 31,
                'hourly_rate': Decimal('3500'),
            },
            {
                'name': '伊藤解体工業',
                'address': '蕨市塚越2-5-20',
                'phone': '048-8901-2345',
                'email': 'ito@example.com',
                'contractor_type': 'partner',
                'specialties': '解体',
                'closing_day': 31,
                'hourly_rate': Decimal('4500'),
            },
        ]

        contractors = []
        for data in contractors_data:
            contractor, created = Contractor.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            contractors.append(contractor)
            status = '作成' if created else '既存'
            self.stdout.write(f'  {status}: {contractor.name} ({contractor.specialties})')

        self.stdout.write(self.style.SUCCESS(f'  ✓ 下請け業者: {len(contractors)}社作成完了'))
        return contractors

    def _create_projects(self, client_companies):
        """案件20件を作成"""
        self.stdout.write('\n🏗️  案件を作成中...')

        work_types = ['クロス', 'クリーニング', '電気工事', '配管工事', '塗装', '左官', '解体', '建材納入']
        statuses = ['受注確定', 'ネタ', 'A', 'B']
        managers = ['生田', '田中', '鈴木', '佐藤', '高橋']

        projects = []
        base_date = date.today()

        for i in range(1, 21):
            # ランダムだが一貫性のあるデータ
            work_type = random.choice(work_types)
            client = random.choice(client_companies)
            manager = random.choice(managers)
            status = random.choice(statuses)

            # 金額を決定
            order_amount = Decimal(random.randint(50, 500)) * Decimal('1000')

            # 日付を決定（過去・現在・未来を混在）
            days_offset = random.randint(-30, 60)
            payment_due_date = base_date + timedelta(days=days_offset + 30)

            project_data = {
                'management_no': f'M2500{i:02d}',
                'site_name': f'{self._generate_site_name(work_type)} {i}',
                'site_address': f'{self._generate_address(i)}',
                'work_type': work_type,
                'project_status': status,
                'order_amount': order_amount,
                'client_company': client,
                'project_manager': manager,
                'payment_due_date': payment_due_date,
                'is_draft': False,
                'parking_fee': Decimal(random.choice([0, 500, 1000, 2000])),
                'expense_item_1': '交通費' if random.random() > 0.5 else '',
                'expense_amount_1': Decimal(random.randint(0, 5000)),
                'expense_item_2': '資材費' if random.random() > 0.7 else '',
                'expense_amount_2': Decimal(random.randint(0, 10000)),
                'invoice_issued': random.random() > 0.5,
                'construction_status': random.choice(['not_started', 'waiting', 'in_progress', 'completed']),
            }

            project, created = Project.objects.get_or_create(
                management_no=project_data['management_no'],
                defaults=project_data
            )
            projects.append(project)
            status_icon = '作成' if created else '既存'
            self.stdout.write(
                f'  {status_icon}: {project.management_no} - {project.site_name} '
                f'(¥{project.order_amount:,})'
            )

        self.stdout.write(self.style.SUCCESS(f'  ✓ 案件: {len(projects)}件作成完了'))
        return projects

    def _create_progress_steps(self, projects):
        """進捗ステップを作成"""
        self.stdout.write('\n📈 進捗ステップを作成中...')

        # テンプレート取得
        templates = {
            template.name: template
            for template in ProgressStepTemplate.objects.all()
        }

        if not templates:
            self.stdout.write(self.style.WARNING('  ⚠️  ProgressStepTemplateが存在しません'))
            return []

        steps = []
        base_date = date.today()

        for project in projects:
            # 各案件にランダムな進捗ステップを作成
            # 着工日と完工日だけ作成
            days_offset = random.randint(-30, 60)
            work_start_date = base_date + timedelta(days=days_offset)
            work_end_date = work_start_date + timedelta(days=random.randint(1, 14))

            step_configs = [
                ('着工日', work_start_date, days_offset < -7),
                ('完工日', work_end_date, days_offset < -14),
            ]

            order = 0
            for step_name, scheduled_date, is_completed in step_configs:
                if step_name not in templates:
                    continue

                template = templates[step_name]
                value = {'scheduled_date': scheduled_date.isoformat() if scheduled_date else ''}

                step, created = ProjectProgressStep.objects.get_or_create(
                    project=project,
                    template=template,
                    defaults={
                        'order': order,
                        'is_active': True,
                        'is_completed': is_completed,
                        'completed_date': scheduled_date if is_completed else None,
                        'value': value,
                    }
                )
                steps.append(step)
                order += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 進捗ステップ: {len(steps)}件作成完了'))
        return steps

    def _create_subcontracts(self, projects, contractors):
        """下請け契約を作成"""
        self.stdout.write('\n📝 下請け契約を作成中...')

        subcontracts = []

        for project in projects:
            # 各案件に1-3社の下請けを割り当て
            num_contractors = random.randint(1, min(3, len(contractors)))
            selected_contractors = random.sample(contractors, num_contractors)

            for contractor in selected_contractors:
                # 契約金額（案件受注金額の60-80%を下請け数で分割）
                total_cost = project.order_amount * Decimal(random.uniform(0.6, 0.8))
                contract_amount = total_cost / Decimal(num_contractors)
                billed_amount = contract_amount
                payment_due_date = project.payment_due_date

                # 支払い状況（30%の確率で既に支払い済み）
                is_paid = random.random() > 0.7

                subcontract_data = {
                    'project': project,
                    'contractor': contractor,
                    'contract_amount': contract_amount,
                    'billed_amount': billed_amount,
                    'payment_due_date': payment_due_date,
                    'payment_date': payment_due_date if is_paid else None,
                    'payment_status': 'paid' if is_paid else 'unpaid',
                    'step': 'construction_start',
                }

                subcontract, created = Subcontract.objects.get_or_create(
                    project=project,
                    contractor=contractor,
                    defaults=subcontract_data
                )
                subcontracts.append(subcontract)

        self.stdout.write(self.style.SUCCESS(f'  ✓ 下請け契約: {len(subcontracts)}件作成完了'))
        return subcontracts

    def _export_to_json(self, output_file, client_companies, contractors, projects, progress_steps, subcontracts):
        """データをJSON形式でエクスポート"""
        self.stdout.write(f'\n💾 JSON出力中: {output_file}')

        # 全オブジェクトをリストに集約
        all_objects = []
        all_objects.extend(client_companies)
        all_objects.extend(contractors)
        all_objects.extend(projects)
        all_objects.extend(progress_steps)
        all_objects.extend(subcontracts)

        # Djangoのserializerを使用
        json_data = serializers.serialize('json', all_objects, indent=2, use_natural_foreign_keys=False)

        # ファイルに書き込み
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_data)

        # メタデータも出力
        metadata = {
            'backup_version': '1.0',
            'created_at': date.today().isoformat(),
            'total_records': len(all_objects),
            'models': {
                'client_companies': len(client_companies),
                'contractors': len(contractors),
                'projects': len(projects),
                'progress_steps': len(progress_steps),
                'subcontracts': len(subcontracts),
            }
        }

        metadata_file = output_file.replace('.json', '_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f'  ✓ データ出力: {output_file}'))
        self.stdout.write(self.style.SUCCESS(f'  ✓ メタデータ: {metadata_file}'))

    def _generate_site_name(self, work_type):
        """工種に応じた現場名を生成"""
        prefixes = ['マンション', 'ビル', 'アパート', '戸建て', 'オフィス', '店舗', '工場', '倉庫']
        locations = ['新宿', '渋谷', '大宮', '浦和', '川越', '所沢', '池袋', '横浜']

        prefix = random.choice(prefixes)
        location = random.choice(locations)

        return f'{location}{prefix}{work_type}'

    def _generate_address(self, index):
        """ランダムな住所を生成"""
        cities = [
            'さいたま市浦和区',
            'さいたま市大宮区',
            '川越市',
            '所沢市',
            'ふじみ野市',
            '入間市',
            '狭山市',
            '川口市',
        ]
        city = random.choice(cities)
        return f'{city}東仲町{index}-{index}'
