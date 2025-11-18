#!/usr/bin/env python
"""テスト用業者データの作成スクリプト"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()

from subcontract_management.models import Contractor

print(f'\n{"="*80}')
print(f'テスト用業者データの作成')
print(f'{"="*80}\n')

# テスト用業者を作成
test_contractors = [
    {
        'name': 'テスト協力会社１',
        'address': '東京都渋谷区テスト1-2-3',
        'phone': '03-1234-5678',
        'email': 'test1@example.com',
        'contact_person': '山田太郎',
        'contractor_type': 'company',
        'specialties': '建築工事、内装工事',
        'hourly_rate': 3000,
        'is_active': True
    },
    {
        'name': 'テスト職人２',
        'address': '神奈川県横浜市テスト2-3-4',
        'phone': '045-2345-6789',
        'email': 'test2@example.com',
        'contact_person': '佐藤花子',
        'contractor_type': 'individual',
        'specialties': '電気工事',
        'hourly_rate': 4000,
        'is_active': True
    },
    {
        'name': 'テスト配管会社３',
        'address': '千葉県千葉市テスト3-4-5',
        'phone': '043-3456-7890',
        'email': 'test3@example.com',
        'contact_person': '鈴木次郎',
        'contractor_type': 'company',
        'specialties': '配管工事、給排水工事',
        'hourly_rate': 3500,
        'is_active': True
    }
]

created_count = 0
for data in test_contractors:
    contractor, created = Contractor.objects.get_or_create(
        name=data['name'],
        defaults=data
    )
    if created:
        created_count += 1
        print(f'✓ {contractor.name} を作成しました（{contractor.get_contractor_type_display()}）')
    else:
        print(f'  {contractor.name} は既に存在します')

print(f'\n作成数: {created_count}/{len(test_contractors)}')
print(f'総業者数: {Contractor.objects.count()}')
print(f'\n{"="*80}\n')
