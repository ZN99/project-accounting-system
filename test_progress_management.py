#!/usr/bin/env python
"""
進捗管理の統合テストスクリプト

テスト内容:
1. 編集完了ボタン（AJAX）での保存
2. 進捗更新ボタン（フォーム送信）での保存
3. 各種ステップタイプの動作確認
   - 日付ステップ
   - チェックボックスステップ
   - 複合ステップ（dynamic_field）
4. ステップ順序の保存
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()

from django.test import Client
from order_management.models import Project
from decimal import Decimal
import json

# テスト用クライアント
client = Client()

# ログイン（adminユーザーを想定）
client.login(username='admin', password='admin123')


def test_ajax_save():
    """編集完了ボタン（AJAX）のテスト"""
    print("\n" + "="*60)
    print("テスト1: 編集完了ボタン（AJAX）")
    print("="*60)

    # テスト用プロジェクトを作成
    project = Project.objects.create(
        site_name="テストプロジェクト1",
        work_type="テスト",
        client_name="テスト会社",
        order_amount=Decimal('1000000')
    )

    # ステップ順序と動的フィールドを送信
    test_data = {
        'ajax_save': 'true',
        'step_order': json.dumps([
            {'step': 'estimate', 'order': 0},
            {'step': 'contract', 'order': 1},
            {'step': 'work_start', 'order': 2}
        ]),
        'dynamic_field_test_field1': 'テスト値1',
        'dynamic_field_test_field2': 'テスト値2',
        'csrfmiddlewaretoken': client.cookies.get('csrftoken').value if client.cookies.get('csrftoken') else 'test'
    }

    response = client.post(
        f'/orders/{project.pk}/update-progress/',
        data=test_data,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )

    print(f"  ステータスコード: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"  レスポンス: {result}")

        # データが保存されたか確認
        project.refresh_from_db()
        print(f"  保存された step_order: {project.additional_items.get('step_order', 'なし')}")
        print(f"  保存された complex_step_fields: {project.additional_items.get('complex_step_fields', 'なし')}")

        # 検証
        if (project.additional_items.get('step_order') and
            project.additional_items.get('complex_step_fields', {}).get('test_field1') == 'テスト値1'):
            print("  ✓ AJAX保存成功")
            return True
        else:
            print("  ✗ AJAX保存失敗: データが正しく保存されていません")
            return False
    else:
        print(f"  ✗ AJAX保存失敗: {response.status_code}")
        return False


def test_form_submit():
    """進捗更新ボタン（フォーム送信）のテスト"""
    print("\n" + "="*60)
    print("テスト2: 進捗更新ボタン（フォーム送信）")
    print("="*60)

    # テスト用プロジェクトを作成
    project = Project.objects.create(
        site_name="テストプロジェクト2",
        work_type="テスト",
        client_name="テスト会社",
        order_amount=Decimal('2000000')
    )

    # フォームデータを送信
    test_data = {
        'estimate_issued_date': '2025-01-15',
        'contract_date': '2025-01-20',
        'work_start_date': '2025-02-01',
        'work_start_completed': 'on',
        'dynamic_field_form_test1': 'フォーム値1',
        'csrfmiddlewaretoken': client.cookies.get('csrftoken').value if client.cookies.get('csrftoken') else 'test'
    }

    response = client.post(
        f'/orders/{project.pk}/update-progress/',
        data=test_data,
        follow=True  # リダイレクトをフォロー
    )

    print(f"  ステータスコード: {response.status_code}")

    if response.status_code == 200:
        # データが保存されたか確認
        project.refresh_from_db()
        print(f"  見積発行日: {project.estimate_issued_date}")
        print(f"  契約日: {project.contract_date}")
        print(f"  着工日: {project.work_start_date}")
        print(f"  着工完了: {project.work_start_completed}")
        print(f"  保存された complex_step_fields: {project.additional_items.get('complex_step_fields', 'なし')}")

        # 検証
        if (str(project.estimate_issued_date) == '2025-01-15' and
            project.work_start_completed and
            project.additional_items.get('complex_step_fields', {}).get('form_test1') == 'フォーム値1'):
            print("  ✓ フォーム送信成功")
            return True
        else:
            print("  ✗ フォーム送信失敗: データが正しく保存されていません")
            return False
    else:
        print(f"  ✗ フォーム送信失敗: {response.status_code}")
        return False


def test_all_step_types():
    """すべてのステップタイプのテスト"""
    print("\n" + "="*60)
    print("テスト3: すべてのステップタイプ")
    print("="*60)

    # テスト用プロジェクトを作成
    project = Project.objects.create(
        site_name="テストプロジェクト3",
        work_type="テスト",
        client_name="テスト会社",
        order_amount=Decimal('3000000')
    )

    # 各種ステップを含むデータ
    test_data = {
        # 日付ステップ
        'estimate_issued_date': '2025-01-10',
        'contract_date': '2025-01-15',
        'work_start_date': '2025-02-01',
        'work_end_date': '2025-02-28',

        # チェックボックスステップ
        'work_start_completed': 'on',
        'work_end_completed': 'on',

        # 複合ステップフィールド
        'dynamic_field_witness_date': '2025-01-25',
        'dynamic_field_witness_result': '合格',
        'dynamic_field_survey_notes': 'テスト調査メモ',
        'dynamic_field_payment_method': '銀行振込',

        # ステップ順序
        'step_order': json.dumps([
            {'step': 'estimate', 'order': 0},
            {'step': 'contract', 'order': 1},
            {'step': 'survey', 'order': 2},
            {'step': 'work_start', 'order': 3},
            {'step': 'work_end', 'order': 4},
            {'step': 'payment', 'order': 5}
        ]),

        'csrfmiddlewaretoken': client.cookies.get('csrftoken').value if client.cookies.get('csrftoken') else 'test'
    }

    response = client.post(
        f'/orders/{project.pk}/update-progress/',
        data=test_data,
        follow=True
    )

    print(f"  ステータスコード: {response.status_code}")

    if response.status_code == 200:
        # データが保存されたか確認
        project.refresh_from_db()

        print("\n  【日付ステップ】")
        print(f"    見積発行日: {project.estimate_issued_date}")
        print(f"    契約日: {project.contract_date}")
        print(f"    着工日: {project.work_start_date}")
        print(f"    完工日: {project.work_end_date}")

        print("\n  【チェックボックスステップ】")
        print(f"    着工完了: {project.work_start_completed}")
        print(f"    完工完了: {project.work_end_completed}")

        print("\n  【複合ステップフィールド】")
        complex_fields = project.additional_items.get('complex_step_fields', {})
        print(f"    立会日: {complex_fields.get('witness_date')}")
        print(f"    立会結果: {complex_fields.get('witness_result')}")
        print(f"    調査メモ: {complex_fields.get('survey_notes')}")
        print(f"    支払方法: {complex_fields.get('payment_method')}")

        print("\n  【ステップ順序】")
        step_order = project.additional_items.get('step_order', [])
        print(f"    ステップ数: {len(step_order)}")
        for step in step_order:
            print(f"      {step['order']}: {step['step']}")

        # 検証
        all_ok = (
            str(project.estimate_issued_date) == '2025-01-10' and
            str(project.work_end_date) == '2025-02-28' and
            project.work_start_completed and
            project.work_end_completed and
            complex_fields.get('witness_result') == '合格' and
            complex_fields.get('payment_method') == '銀行振込' and
            len(step_order) == 6
        )

        if all_ok:
            print("\n  ✓ すべてのステップタイプ保存成功")
            return True
        else:
            print("\n  ✗ すべてのステップタイプ保存失敗")
            return False
    else:
        print(f"  ✗ 保存失敗: {response.status_code}")
        return False


def cleanup():
    """テストデータのクリーンアップ"""
    print("\n" + "="*60)
    print("クリーンアップ")
    print("="*60)

    deleted_count = Project.objects.filter(site_name__startswith="テストプロジェクト").delete()[0]
    print(f"  削除したプロジェクト数: {deleted_count}")


if __name__ == '__main__':
    print("\n" + "#"*60)
    print("# 進捗管理 統合テスト")
    print("#"*60)

    try:
        results = []

        # テスト実行
        results.append(("AJAX保存", test_ajax_save()))
        results.append(("フォーム送信", test_form_submit()))
        results.append(("すべてのステップタイプ", test_all_step_types()))

        # 結果サマリー
        print("\n" + "="*60)
        print("テスト結果サマリー")
        print("="*60)

        for name, result in results:
            status = "✓ 成功" if result else "✗ 失敗"
            print(f"  {name}: {status}")

        total = len(results)
        passed = sum(1 for _, r in results if r)
        print(f"\n  合計: {passed}/{total} 成功")

        if passed == total:
            print("\n  🎉 すべてのテストが成功しました！")
            exit_code = 0
        else:
            print("\n  ⚠️  一部のテストが失敗しました")
            exit_code = 1

    finally:
        # クリーンアップ
        cleanup()

    sys.exit(exit_code)
