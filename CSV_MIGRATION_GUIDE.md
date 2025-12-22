# CSV データ移行手順書

**最終更新日**: 2025年12月22日

---

## 概要

このドキュメントは、バックアップデータ（JSON）ではなく、CSV形式のファイルからデータベースにデータを移行する手順を説明します。

---

## 前提条件

- Python 3.11以上がインストールされている
- プロジェクトの仮想環境がアクティブになっている
- データベースのマイグレーションが完了している

---

## 手順1: CSVファイルの準備

### 1.1 必要なCSVファイル

以下のモデルごとにCSVファイルを準備します：

```
csv_data/
├── users.csv                    # ユーザー
├── client_companies.csv         # 元請業者
├── contractors.csv              # 下請け業者
├── internal_workers.csv         # 社内職人
├── projects.csv                 # 案件
├── subcontracts.csv            # 下請け契約
├── payments.csv                # 支払い
└── material_orders.csv         # 資材発注
```

### 1.2 CSVファイルのフォーマット

#### users.csv
```csv
username,email,password,user_role,first_name,last_name,is_staff,is_superuser,is_active
admin,admin@example.com,pbkdf2_sha256$...,executive,管理,太郎,true,true,true
sales01,sales01@example.com,pbkdf2_sha256$...,sales,営業,花子,false,false,true
```

**注意**: パスワードは必ずハッシュ化された値を使用してください。

#### client_companies.csv
```csv
company_name,address,phone,payment_cycle,closing_day,payment_offset_months,payment_day,is_active
株式会社ABC建設,東京都渋谷区1-2-3,03-1234-5678,monthly_end,31,1,25,true
株式会社XYZ工務店,神奈川県横浜市4-5-6,045-9876-5432,monthly_20,20,2,10,true
```

#### contractors.csv
```csv
name,contractor_type,phone,email,address,specialties,payment_cycle,closing_day,payment_day,is_active
山田建設株式会社,company,090-1234-5678,yamada@example.com,東京都新宿区7-8-9,配管工事,monthly_end,31,25,true
田中太郎,individual,080-9876-5432,tanaka@example.com,埼玉県さいたま市10-11-12,電気工事,monthly_end,31,25,true
```

#### internal_workers.csv
```csv
name,department,phone,email,hire_date,is_active
佐藤次郎,construction,090-1111-2222,sato@example.com,2020-04-01,true
鈴木花子,sales,080-3333-4444,suzuki@example.com,2021-06-15,true
```

#### projects.csv
```csv
management_no,site_name,customer_id,order_date,order_amount,cost_amount,status,project_status,is_draft
A-2024-001,渋谷ビル改修工事,1,2024-01-15,5000000,3500000,active,受注確定,false
A-2024-002,横浜マンション新築,2,2024-02-20,8000000,6000000,active,受注確定,false
```

**注意**: `customer_id`は`client_companies.csv`のIDと対応させてください。

#### subcontracts.csv
```csv
project_id,contractor_id,internal_worker_id,worker_type,contract_amount,invoice_amount,payment_status,work_type
1,1,,external,500000,500000,unpaid,construction_start
2,,1,internal,0,0,paid,survey
```

#### payments.csv
```csv
project_id,payment_date,amount,payment_method,notes,is_deleted
1,2024-03-25,1000000,bank_transfer,第1回支払い,false
2,2024-04-10,2000000,bank_transfer,第1回支払い,false
```

#### material_orders.csv
```csv
project_id,order_date,supplier,item_name,quantity,unit_price,total_price,status
1,2024-02-01,ABC資材,セメント,100,5000,500000,ordered
2,2024-03-15,XYZ商事,鉄筋,200,8000,1600000,delivered
```

---

## 手順2: インポートスクリプトの作成

### 2.1 管理コマンドの作成

`order_management/management/commands/import_from_csv.py`を作成：

```python
# order_management/management/commands/import_from_csv.py

import csv
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from order_management.models import (
    ClientCompany, Project, Payment, MaterialOrder
)
from subcontract_management.models import (
    Contractor, InternalWorker, Subcontract
)

User = get_user_model()


class Command(BaseCommand):
    help = 'CSVファイルからデータをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-dir',
            type=str,
            default='csv_data',
            help='CSVファイルが格納されているディレクトリ'
        )

    def handle(self, *args, **options):
        csv_dir = options['csv_dir']

        self.stdout.write(self.style.SUCCESS('=== CSVインポート開始 ===\n'))

        # インポート順序（外部キー制約を考慮）
        self.import_users(csv_dir)
        self.import_client_companies(csv_dir)
        self.import_contractors(csv_dir)
        self.import_internal_workers(csv_dir)
        self.import_projects(csv_dir)
        self.import_subcontracts(csv_dir)
        self.import_payments(csv_dir)
        self.import_material_orders(csv_dir)

        self.stdout.write(self.style.SUCCESS('\n=== CSVインポート完了 ==='))

    def import_users(self, csv_dir):
        """ユーザーのインポート"""
        self.stdout.write('ユーザーをインポート中...')

        with open(f'{csv_dir}/users.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                user, created = User.objects.get_or_create(
                    username=row['username'],
                    defaults={
                        'email': row['email'],
                        'password': row['password'],
                        'user_role': row['user_role'],
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'is_staff': row['is_staff'].lower() == 'true',
                        'is_superuser': row['is_superuser'].lower() == 'true',
                        'is_active': row['is_active'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件のユーザーをインポート'))

    def import_client_companies(self, csv_dir):
        """元請業者のインポート"""
        self.stdout.write('元請業者をインポート中...')

        with open(f'{csv_dir}/client_companies.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                company, created = ClientCompany.objects.get_or_create(
                    company_name=row['company_name'],
                    defaults={
                        'address': row['address'],
                        'phone': row['phone'],
                        'payment_cycle': row['payment_cycle'],
                        'closing_day': int(row['closing_day']) if row['closing_day'] else None,
                        'payment_offset_months': int(row['payment_offset_months']) if row['payment_offset_months'] else None,
                        'payment_day': int(row['payment_day']) if row['payment_day'] else None,
                        'is_active': row['is_active'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の元請業者をインポート'))

    def import_contractors(self, csv_dir):
        """下請け業者のインポート"""
        self.stdout.write('下請け業者をインポート中...')

        with open(f'{csv_dir}/contractors.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                contractor, created = Contractor.objects.get_or_create(
                    name=row['name'],
                    defaults={
                        'contractor_type': row['contractor_type'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'address': row['address'],
                        'specialties': row['specialties'],
                        'payment_cycle': row['payment_cycle'],
                        'closing_day': int(row['closing_day']) if row['closing_day'] else None,
                        'payment_day': int(row['payment_day']) if row['payment_day'] else None,
                        'is_active': row['is_active'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の下請け業者をインポート'))

    def import_internal_workers(self, csv_dir):
        """社内職人のインポート"""
        self.stdout.write('社内職人をインポート中...')

        with open(f'{csv_dir}/internal_workers.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                worker, created = InternalWorker.objects.get_or_create(
                    name=row['name'],
                    defaults={
                        'department': row['department'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'hire_date': datetime.strptime(row['hire_date'], '%Y-%m-%d').date() if row['hire_date'] else None,
                        'is_active': row['is_active'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の社内職人をインポート'))

    def import_projects(self, csv_dir):
        """案件のインポート"""
        self.stdout.write('案件をインポート中...')

        with open(f'{csv_dir}/projects.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                customer = ClientCompany.objects.get(id=int(row['customer_id']))

                project, created = Project.objects.get_or_create(
                    management_no=row['management_no'],
                    defaults={
                        'site_name': row['site_name'],
                        'customer': customer,
                        'order_date': datetime.strptime(row['order_date'], '%Y-%m-%d').date() if row['order_date'] else None,
                        'order_amount': Decimal(row['order_amount']) if row['order_amount'] else Decimal('0'),
                        'cost_amount': Decimal(row['cost_amount']) if row['cost_amount'] else Decimal('0'),
                        'status': row['status'],
                        'project_status': row['project_status'],
                        'is_draft': row['is_draft'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の案件をインポート'))

    def import_subcontracts(self, csv_dir):
        """下請け契約のインポート"""
        self.stdout.write('下請け契約をインポート中...')

        with open(f'{csv_dir}/subcontracts.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                project = Project.objects.get(id=int(row['project_id']))
                contractor = Contractor.objects.get(id=int(row['contractor_id'])) if row['contractor_id'] else None
                internal_worker = InternalWorker.objects.get(id=int(row['internal_worker_id'])) if row['internal_worker_id'] else None

                subcontract, created = Subcontract.objects.get_or_create(
                    project=project,
                    contractor=contractor,
                    internal_worker=internal_worker,
                    work_type=row['work_type'],
                    defaults={
                        'worker_type': row['worker_type'],
                        'contract_amount': Decimal(row['contract_amount']) if row['contract_amount'] else Decimal('0'),
                        'invoice_amount': Decimal(row['invoice_amount']) if row['invoice_amount'] else Decimal('0'),
                        'payment_status': row['payment_status'],
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の下請け契約をインポート'))

    def import_payments(self, csv_dir):
        """支払いのインポート"""
        self.stdout.write('支払いをインポート中...')

        with open(f'{csv_dir}/payments.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                project = Project.objects.get(id=int(row['project_id']))

                payment, created = Payment.objects.get_or_create(
                    project=project,
                    payment_date=datetime.strptime(row['payment_date'], '%Y-%m-%d').date(),
                    amount=Decimal(row['amount']),
                    defaults={
                        'payment_method': row['payment_method'],
                        'notes': row['notes'],
                        'is_deleted': row['is_deleted'].lower() == 'true',
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の支払いをインポート'))

    def import_material_orders(self, csv_dir):
        """資材発注のインポート"""
        self.stdout.write('資材発注をインポート中...')

        with open(f'{csv_dir}/material_orders.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                project = Project.objects.get(id=int(row['project_id']))

                order, created = MaterialOrder.objects.get_or_create(
                    project=project,
                    order_date=datetime.strptime(row['order_date'], '%Y-%m-%d').date(),
                    supplier=row['supplier'],
                    item_name=row['item_name'],
                    defaults={
                        'quantity': int(row['quantity']),
                        'unit_price': Decimal(row['unit_price']),
                        'total_price': Decimal(row['total_price']),
                        'status': row['status'],
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の資材発注をインポート'))
```

---

## 手順3: CSVデータのエクスポート（既存データがある場合）

既存のデータベースからCSVファイルを作成する場合のスクリプト：

```python
# order_management/management/commands/export_to_csv.py

import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from order_management.models import (
    ClientCompany, Project, Payment, MaterialOrder
)
from subcontract_management.models import (
    Contractor, InternalWorker, Subcontract
)

User = get_user_model()


class Command(BaseCommand):
    help = 'データをCSVファイルにエクスポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='csv_export',
            help='CSVファイルの出力先ディレクトリ'
        )

    def handle(self, *args, **options):
        import os
        output_dir = options['output_dir']

        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)

        self.stdout.write(self.style.SUCCESS('=== CSVエクスポート開始 ===\n'))

        self.export_users(output_dir)
        self.export_client_companies(output_dir)
        self.export_contractors(output_dir)
        self.export_internal_workers(output_dir)
        self.export_projects(output_dir)
        self.export_subcontracts(output_dir)
        self.export_payments(output_dir)
        self.export_material_orders(output_dir)

        self.stdout.write(self.style.SUCCESS(f'\n=== CSVエクスポート完了 ==='))
        self.stdout.write(self.style.SUCCESS(f'出力先: {output_dir}/'))

    def export_users(self, output_dir):
        """ユーザーのエクスポート"""
        self.stdout.write('ユーザーをエクスポート中...')

        with open(f'{output_dir}/users.csv', 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['username', 'email', 'password', 'user_role', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for user in User.objects.all():
                writer.writerow({
                    'username': user.username,
                    'email': user.email,
                    'password': user.password,
                    'user_role': user.user_role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'is_active': user.is_active,
                })

        count = User.objects.count()
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件のユーザーをエクスポート'))

    def export_client_companies(self, output_dir):
        """元請業者のエクスポート"""
        self.stdout.write('元請業者をエクスポート中...')

        with open(f'{output_dir}/client_companies.csv', 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['company_name', 'address', 'phone', 'payment_cycle', 'closing_day', 'payment_offset_months', 'payment_day', 'is_active']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for company in ClientCompany.objects.all():
                writer.writerow({
                    'company_name': company.company_name,
                    'address': company.address or '',
                    'phone': company.phone or '',
                    'payment_cycle': company.payment_cycle or '',
                    'closing_day': company.closing_day or '',
                    'payment_offset_months': company.payment_offset_months or '',
                    'payment_day': company.payment_day or '',
                    'is_active': company.is_active,
                })

        count = ClientCompany.objects.count()
        self.stdout.write(self.style.SUCCESS(f'  ✓ {count}件の元請業者をエクスポート'))

    # 他のエクスポートメソッドも同様に実装...
```

---

## 手順4: 実行方法

### 4.1 CSVからインポート

```bash
# CSVファイルを配置
mkdir csv_data
# csv_data/ ディレクトリに各CSVファイルを配置

# インポート実行
python manage.py import_from_csv --csv-dir=csv_data
```

### 4.2 既存データをCSVにエクスポート

```bash
# データをエクスポート
python manage.py export_to_csv --output-dir=csv_export

# エクスポートされたファイルを確認
ls csv_export/
```

---

## 手順5: データの検証

インポート後、以下のコマンドでデータを確認：

```bash
# Djangoシェルで確認
python manage.py shell

# 各モデルのデータ数を確認
>>> from django.contrib.auth import get_user_model
>>> from order_management.models import ClientCompany, Project
>>> from subcontract_management.models import Contractor, InternalWorker
>>>
>>> User = get_user_model()
>>> print(f"ユーザー: {User.objects.count()}件")
>>> print(f"元請業者: {ClientCompany.objects.count()}件")
>>> print(f"下請け業者: {Contractor.objects.count()}件")
>>> print(f"社内職人: {InternalWorker.objects.count()}件")
>>> print(f"案件: {Project.objects.count()}件")
```

---

## トラブルシューティング

### エラー1: 外部キー制約エラー

**症状**: `IntegrityError: FOREIGN KEY constraint failed`

**原因**: 参照先のデータが存在しない

**解決策**:
1. インポート順序を確認（親テーブル → 子テーブル）
2. CSV内のIDが正しいか確認
3. 参照先データが先にインポートされているか確認

### エラー2: 重複データエラー

**症状**: `IntegrityError: UNIQUE constraint failed`

**原因**: 既に同じデータが存在する

**解決策**:
1. `get_or_create()`を使用して重複を防ぐ
2. 既存データを削除してからインポート
3. `update_or_create()`を使用して更新

### エラー3: 日付フォーマットエラー

**症状**: `ValueError: time data does not match format`

**原因**: CSVの日付フォーマットが不正

**解決策**:
1. 日付は`YYYY-MM-DD`形式で統一
2. 空の日付は空文字列ではなくNoneを使用

---

## 応用: カスタムフィールドのインポート

カスタムフィールドがある場合のインポート方法：

```python
def import_contractors_with_custom_fields(self, csv_dir):
    """カスタムフィールド付き下請け業者のインポート"""

    with open(f'{csv_dir}/contractors.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # 基本フィールド
            contractor, created = Contractor.objects.get_or_create(
                name=row['name'],
                defaults={
                    'contractor_type': row['contractor_type'],
                    # ... 他のフィールド
                }
            )

            # カスタムフィールド（JSONFieldに保存）
            custom_fields = {}
            for key, value in row.items():
                if key.startswith('custom_'):
                    custom_fields[key.replace('custom_', '')] = value

            if custom_fields:
                contractor.custom_fields = custom_fields
                contractor.save()
```

---

## まとめ

CSV移行の利点:
- ✅ 人間が読みやすく編集しやすい
- ✅ Excel等で編集可能
- ✅ バージョン管理が容易
- ✅ 部分的なインポートが可能
- ✅ データの検証がしやすい

注意点:
- ⚠️ 外部キーの順序に注意
- ⚠️ データ型の整合性を確認
- ⚠️ 文字エンコーディングはUTF-8を使用
- ⚠️ インポート前にバックアップを取得

---

## 参考リンク

- [Django管理コマンド](https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/)
- [Pythonのcsv模块](https://docs.python.org/ja/3/library/csv.html)
- [データベースバックアップ手順](./BACKUP_GUIDE.md)
