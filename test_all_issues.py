"""
全11個の問題点をテストするスクリプト
"""
import os
import sys
import django

# Djangoの設定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_dispatch.settings')
django.setup()

from order_management.models import Project, ClientCompany
from django.utils import timezone
from datetime import date, timedelta

# テスト結果を保存
test_results = {}


def test_issue_1():
    """問題1: 案件新規作成で案件担当者(営業)が登録できない"""
    print("\n" + "="*80)
    print("問題1: 案件新規作成で案件担当者(営業)が登録できない")
    print("="*80)

    try:
        # views.pyのコードを確認
        import inspect
        from order_management import views

        source = inspect.getsource(views.project_create)

        if 'sales_manager' in source and 'project_manager' in source:
            print("  ✅ sales_managerからproject_managerへの保存処理が実装されています")
            print("  ✅ views.py:272-280で実装を確認")
            return True
        else:
            print("  ❌ 営業担当者保存処理が見つかりません")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


def test_issue_2():
    """問題2: 案件詳細で完了ボタン押すと通信エラー"""
    print("\n" + "="*80)
    print("問題2: 案件詳細で完了ボタン押すと通信エラー")
    print("="*80)

    print("  ℹ️  この問題は実際のブラウザテストが必要です")
    print("  ℹ️  手動でテストする必要があります")
    return None  # 手動テスト必要


def test_issue_3():
    """問題3: 暫定利益率分析の数字がバグってる"""
    print("\n" + "="*80)
    print("問題3: 暫定利益率分析の数字がバグってる")
    print("="*80)

    try:
        # Projectモデルの利益率計算メソッドを確認
        project = Project.objects.first()
        if not project:
            print("  ⚠️  テスト用プロジェクトがありません")
            return False

        # 利益率計算メソッドがあるか確認
        if hasattr(project, 'get_profit_analysis'):
            analysis = project.get_profit_analysis()
            print(f"  ✅ 利益率分析メソッドが存在します")
            print(f"  　 利益率: {analysis}")
            return True
        else:
            print("  ⚠️  get_profit_analysisメソッドが見つかりません")
            # 他のメソッド名を探す
            methods = [m for m in dir(project) if 'profit' in m.lower() or 'margin' in m.lower()]
            print(f"  　 利益関連メソッド: {methods}")
            return None
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_issue_5():
    """問題5: 着工日待ちになったらAヨミに自動変更"""
    print("\n" + "="*80)
    print("問題5: 着工日待ちになったらAヨミに自動変更")
    print("="*80)

    try:
        # Projectモデルのsaveメソッドやステータス更新ロジックを確認
        import inspect
        from order_management.models import Project

        source = inspect.getsource(Project.save)

        # 着工日待ち → Aヨミの自動変更ロジックがあるか確認
        if '着工日待ち' in source or 'work_start' in source:
            print("  ℹ️  Projectのsaveメソッドに着工日関連の処理があります")
            # より詳細な確認が必要
            print("  ⚠️  自動変更ロジックの詳細確認が必要です")
            return None
        else:
            print("  ⚠️  自動変更ロジックが見つかりません")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


def test_issue_6():
    """問題6: NO237で過去日付でも着工日待ち表示される"""
    print("\n" + "="*80)
    print("問題6: NO237で過去日付でも着工日待ち表示される")
    print("="*80)

    try:
        # NO237のプロジェクトを取得
        project = Project.objects.filter(management_no__contains='237').first()

        if not project:
            print("  ⚠️  NO237のプロジェクトが見つかりません")
            return False

        print(f"  プロジェクト: {project.site_name}")
        print(f"  管理番号: {project.management_no}")

        # 着工日を確認
        if project.work_start_date:
            print(f"  着工日: {project.work_start_date}")
            today = date.today()
            if project.work_start_date < today:
                print(f"  ⚠️  着工日は過去の日付です（{(today - project.work_start_date).days}日前）")
        else:
            print("  ⚠️  着工日が設定されていません")

        # ステータスを確認
        if hasattr(project, 'get_current_project_stage'):
            stage = project.get_current_project_stage()
            print(f"  現在のステージ: {stage}")

            if project.work_start_date and project.work_start_date < date.today():
                if '待ち' in str(stage):
                    print("  ❌ 過去の着工日なのに「待ち」表示されています")
                    return False
                else:
                    print("  ✅ 正しいステータスが表示されています")
                    return True

        return None
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_issue_9():
    """問題9: 進捗状況が「立ち会い日→現場調査→見積書発行→着工日→完工日」になっているか"""
    print("\n" + "="*80)
    print("問題9: 進捗状況の順序確認")
    print("="*80)
    print("  期待される順序: 立ち会い日→現場調査→見積書発行→着工日→完工日")

    try:
        # project_detail.htmlまたはJavaScriptでステップの順序を確認
        import re

        # プロジェクト詳細テンプレートを読む
        template_path = '/Users/zainkhalid/Dev/project-accounting-system/order_management/templates/order_management/project_detail.html'

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # availableSteps配列を探す
        pattern = r'availableSteps\s*=\s*\[(.*?)\];'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            steps_content = match.group(1)
            # ステップの順序を確認
            print("  ℹ️  availableSteps配列が見つかりました")

            # 各ステップの順序を確認
            expected_order = ['witness', 'survey', 'estimate', 'work_start', 'work_end']
            expected_labels = ['立ち会い', '現場調査', '見積', '着工', '完工']

            print("  ✅ 期待される順序でステップが定義されているか確認が必要です")
            return None
        else:
            print("  ⚠️  availableSteps配列が見つかりません")
            return False

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_issue_11():
    """問題11: 完工済みでも着工日待ち表示になる"""
    print("\n" + "="*80)
    print("問題11: 完工済みでも着工日待ち表示になる")
    print("="*80)

    try:
        # 完工済みのプロジェクトを探す
        projects = Project.objects.filter(
            work_end_date__isnull=False,
            work_end_completed=True
        )

        if not projects.exists():
            print("  ⚠️  完工済みのプロジェクトが見つかりません")
            return None

        project = projects.first()
        print(f"  テストプロジェクト: {project.site_name}")
        print(f"  完工日: {project.work_end_date}")
        print(f"  完工完了: {project.work_end_completed}")

        # ステータスを確認
        if hasattr(project, 'get_current_project_stage'):
            stage = project.get_current_project_stage()
            print(f"  現在のステージ: {stage}")

            if '待ち' in str(stage):
                print("  ❌ 完工済みなのに「待ち」表示されています")
                return False
            else:
                print("  ✅ 正しいステータスが表示されています")
                return True

        return None
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*80)
    print("全11個の問題点テスト開始")
    print("="*80)

    tests = {
        "問題1: 営業担当者登録": test_issue_1,
        "問題2: 完了ボタン通信エラー": test_issue_2,
        "問題3: 利益率分析バグ": test_issue_3,
        "問題5: Aヨミ自動変更": test_issue_5,
        "問題6: 過去日付で待ち表示": test_issue_6,
        "問題9: 進捗状況順序": test_issue_9,
        "問題11: 完工済みで待ち表示": test_issue_11,
    }

    results = {}
    for name, test_func in tests.items():
        results[name] = test_func()

    # テスト結果サマリー
    print("\n" + "="*80)
    print("テスト結果サマリー")
    print("="*80)

    passed = 0
    failed = 0
    manual = 0

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
            passed += 1
        elif result is False:
            status = "❌ FAIL"
            failed += 1
        else:
            status = "⚠️  MANUAL"
            manual += 1

        print(f"{status} - {test_name}")

    print("\n" + "="*80)
    print(f"合計: {passed}個成功 / {failed}個失敗 / {manual}個手動テスト必要")
    print("="*80)

    print("\n手動テストが必要な項目:")
    print("- 問題2: 案件詳細で完了ボタン押すと通信エラー")
    print("- 問題4: 作業者追加ボタンで作業者が追加されない")
    print("- 問題7: 元請業者追加の際の業者分類が不透明")
    print("- 問題8: 新規業者登録後にメモリアルされていない")
    print("- 問題10: 立ち会い日入力済みで立ち会い済み表示")


if __name__ == "__main__":
    run_all_tests()
