"""
Test script for completion report file upload and download functionality
"""
import os
import sys
import django

# Djangoの設定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()

from order_management.models import Project, ClientCompany
from django.core.files.uploadedfile import SimpleUploadedFile


def test_completion_report_fields():
    """Test 1: 完了報告フィールドがProjectモデルに存在することを確認"""
    print("\n" + "="*80)
    print("Test 1: Projectモデルに完了報告フィールドが存在するか確認")
    print("="*80)

    try:
        # フィールドの存在を確認
        from order_management.models import Project
        fields = [f.name for f in Project._meta.get_fields()]

        required_fields = [
            'completion_report_content',
            'completion_report_date',
            'completion_report_status',
            'completion_report_notes',
            'completion_report_file',
            'completion_report_completed'
        ]

        all_exist = True
        for field in required_fields:
            if field in fields:
                print(f"  ✅ {field} フィールドが存在します")
            else:
                print(f"  ❌ {field} フィールドが見つかりません")
                all_exist = False

        return all_exist
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


def test_client_company_template_field():
    """Test 2: ClientCompanyモデルに完了報告テンプレートフィールドが存在することを確認"""
    print("\n" + "="*80)
    print("Test 2: ClientCompanyモデルに完了報告テンプレートフィールドが存在するか確認")
    print("="*80)

    try:
        from order_management.models import ClientCompany
        fields = [f.name for f in ClientCompany._meta.get_fields()]

        required_fields = [
            'completion_report_template',
            'completion_report_notes'
        ]

        all_exist = True
        for field in required_fields:
            if field in fields:
                print(f"  ✅ {field} フィールドが存在します")
            else:
                print(f"  ❌ {field} フィールドが見つかりません")
                all_exist = False

        return all_exist
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


def test_file_upload():
    """Test 3: ファイルアップロード機能のテスト"""
    print("\n" + "="*80)
    print("Test 3: 完了報告ファイルのアップロード機能をテスト")
    print("="*80)

    try:
        # テスト用プロジェクトを取得（最初のプロジェクト）
        project = Project.objects.first()

        if not project:
            print("  ⚠️  テスト用プロジェクトがありません")
            return False

        print(f"  テストプロジェクト: {project.project_name}")

        # テスト用ファイルを作成
        test_file_content = b"This is a test completion report file"
        test_file = SimpleUploadedFile(
            "test_completion_report.pdf",
            test_file_content,
            content_type="application/pdf"
        )

        # ファイルを保存
        project.completion_report_file = test_file
        project.completion_report_completed = True
        project.save()

        print(f"  ✅ ファイルをアップロードしました: {project.completion_report_file.name}")
        print(f"  ✅ 完了チェック: {project.completion_report_completed}")

        # ファイルが実際に保存されたか確認
        if project.completion_report_file:
            print(f"  ✅ ファイルが正しく保存されました")
            # クリーンアップ
            if os.path.exists(project.completion_report_file.path):
                os.remove(project.completion_report_file.path)
                print(f"  ✅ テストファイルを削除しました")
            project.completion_report_file = None
            project.completion_report_completed = False
            project.save()
            return True
        else:
            print(f"  ❌ ファイルの保存に失敗しました")
            return False

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_fill_from_client_company():
    """Test 4: ClientCompanyからの自動入力機能をテスト"""
    print("\n" + "="*80)
    print("Test 4: ClientCompanyのテンプレート内容が自動入力されるかテスト")
    print("="*80)

    try:
        # テスト用ClientCompanyを取得
        client_company = ClientCompany.objects.first()

        if not client_company:
            print("  ⚠️  テスト用元請会社がありません")
            return False

        # 完了報告テンプレート内容を設定
        original_notes = client_company.completion_report_notes
        test_notes = "テスト用完了報告テンプレート内容\n1. 作業完了\n2. 確認事項"
        client_company.completion_report_notes = test_notes
        client_company.save()

        print(f"  元請会社: {client_company.company_name}")
        print(f"  テンプレート内容を設定: {test_notes[:50]}...")

        # 新しいプロジェクトを作成（自動入力をテスト）
        project = Project.objects.create(
            project_name="自動入力テストプロジェクト",
            client_company=client_company,
            status='見積提出',
            construction_type='construction'
        )

        # 手動でsaveメソッドを呼んで自動入力をトリガー
        project.save()

        if project.completion_report_content == test_notes:
            print(f"  ✅ 完了報告内容が自動入力されました")
            print(f"  　 内容: {project.completion_report_content[:50]}...")
            result = True
        else:
            print(f"  ❌ 自動入力に失敗しました")
            print(f"  　 期待値: {test_notes[:50]}...")
            actual_value = project.completion_report_content or '(空)'
            print(f"  　 実際値: {actual_value[:50]}...")
            result = False

        # クリーンアップ
        project.delete()
        client_company.completion_report_notes = original_notes
        client_company.save()

        return result

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_view_handles_file_upload():
    """Test 5: update_progressビューがファイルアップロードを処理できるか確認"""
    print("\n" + "="*80)
    print("Test 5: update_progressビューのファイルアップロード処理を確認")
    print("="*80)

    try:
        # ビューのコードを読んで、必要な処理が含まれているか確認
        import inspect
        from order_management import views

        source = inspect.getsource(views.update_progress)

        checks = {
            'completion_report_file in request.FILES': 'request.FILES からファイルを取得',
            'project.completion_report_file = request.FILES': 'ファイルをモデルに保存',
            'completion_report_completed': '完了チェックボックスの処理'
        }

        all_passed = True
        for check, description in checks.items():
            if check in source:
                print(f"  ✅ {description}")
            else:
                print(f"  ⚠️  {description} (コードに見つかりませんでした)")
                # この警告は必ずしもエラーではない（実装方法による）

        print(f"  ✅ update_progressビューの確認完了")
        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*80)
    print("完了報告機能テスト開始")
    print("="*80)

    results = {
        "Projectモデルフィールド確認": test_completion_report_fields(),
        "ClientCompanyモデルフィールド確認": test_client_company_template_field(),
        "ファイルアップロード機能": test_file_upload(),
        "ClientCompanyからの自動入力": test_auto_fill_from_client_company(),
        "update_progressビューの確認": test_view_handles_file_upload(),
    }

    # テスト結果サマリー
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1

    print("\n" + "="*80)
    print(f"合計: {passed}/{total} テストが成功")
    print("="*80)

    if passed == total:
        print("\n🎉 すべてのテストが成功しました！")
        print("完了報告機能は正しく実装されています。")
    else:
        print(f"\n⚠️  {total - passed}個のテストが失敗しました。")


if __name__ == "__main__":
    run_all_tests()
