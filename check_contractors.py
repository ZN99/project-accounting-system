#!/usr/bin/env python
"""業者データの確認スクリプト"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()

from subcontract_management.models import Contractor

print(f'\n{"="*80}')
print(f'業者データベースの確認')
print(f'{"="*80}\n')

total = Contractor.objects.count()
print(f'総業者数: {total}\n')

if total > 0:
    print('登録されている業者:')
    for c in Contractor.objects.all()[:20]:
        print(f'  - {c.name} (ID: {c.id}, Active: {c.is_active}, Type: {c.contractor_type})')
else:
    print('⚠️  業者が1件も登録されていません！')

print(f'\n{"="*80}\n')
