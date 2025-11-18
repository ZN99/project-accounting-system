"""
NAVバーの動作を検証するSeleniumテストスクリプト
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class NavBarTester:
    def __init__(self):
        # Chrome WebDriverを初期化
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "http://localhost:8000"

    def login(self):
        """ログイン処理"""
        print("\n📝 ログイン中...")
        self.driver.get(f"{self.base_url}/orders/list/")
        time.sleep(2)

    def test_subnav_display(self, section_name, expected_subnav_id):
        """サブナビの表示テスト"""
        print(f"\n🔍 テスト: {section_name}のサブナビ表示")

        try:
            # メインナビボタンを探す
            main_nav_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f'a.nav-btn[data-section="{expected_subnav_id}"]'))
            )
            print(f"  ✓ メインナビボタン見つかりました")

            # クリック前のURL
            current_url_before = self.driver.current_url

            # メインナビボタンをクリック
            main_nav_btn.click()
            time.sleep(1)

            # サブナビが表示されているか確認
            subnav = self.driver.find_element(By.ID, f"subnav-{expected_subnav_id}")
            is_visible = "active" in subnav.get_attribute("class")

            if is_visible:
                print(f"  ✓ サブナビが表示されました")
            else:
                print(f"  ✗ サブナビが表示されませんでした")
                return False

            # アクティブクラスが適用されているか確認
            if "active" in main_nav_btn.get_attribute("class"):
                print(f"  ✓ メインナビボタンにactiveクラスが適用されています")
            else:
                print(f"  ⚠ メインナビボタンにactiveクラスがありません")

            # ページ遷移を待つ
            time.sleep(2)

            # ページが変わったか確認
            current_url_after = self.driver.current_url
            if current_url_after != current_url_before:
                print(f"  ✓ ページ遷移: {current_url_before} → {current_url_after}")

                # ページ遷移後もサブナビが表示されているか確認
                time.sleep(1)
                subnav_after = self.driver.find_element(By.ID, f"subnav-{expected_subnav_id}")
                is_visible_after = "active" in subnav_after.get_attribute("class")

                if is_visible_after:
                    print(f"  ✓ ページ遷移後もサブナビが表示されています")
                else:
                    print(f"  ✗ ページ遷移後にサブナビが非表示になりました")
                    return False
            else:
                print(f"  ⚠ ページ遷移が発生しませんでした")

            return True

        except TimeoutException:
            print(f"  ✗ タイムアウト: 要素が見つかりませんでした")
            return False
        except Exception as e:
            print(f"  ✗ エラー: {str(e)}")
            return False

    def test_subnav_items(self, section_name, subnav_id, expected_items_count):
        """サブナビの項目数テスト"""
        print(f"\n📊 テスト: {section_name}のサブナビ項目数")

        try:
            subnav = self.driver.find_element(By.ID, f"subnav-{subnav_id}")
            items = subnav.find_elements(By.CLASS_NAME, "subnav-item")
            actual_count = len(items)

            if actual_count == expected_items_count:
                print(f"  ✓ 項目数が正しい: {actual_count}個")
                return True
            else:
                print(f"  ✗ 項目数が不正: 期待{expected_items_count}個、実際{actual_count}個")
                return False

        except Exception as e:
            print(f"  ✗ エラー: {str(e)}")
            return False

    def run_all_tests(self):
        """すべてのテストを実行"""
        print("\n" + "="*60)
        print("🚀 NAVバー総合テスト開始")
        print("="*60)

        results = {}

        # ログイン
        self.login()
        time.sleep(2)

        # テストケース定義
        test_cases = [
            ("案件管理", "projects", 3),
            ("元請検索", "clients", 3),
            ("下請け検索", "contractors", 3),
            ("カレンダー", "calendar", 3),
            ("経理", "accounting", 12),
            ("システム管理", "system", 4),
        ]

        # 各カテゴリをテスト
        for section_name, subnav_id, item_count in test_cases:
            # サブナビ表示テスト
            display_result = self.test_subnav_display(section_name, subnav_id)
            results[f"{section_name}_display"] = display_result

            # サブナビ項目数テスト
            if display_result:
                items_result = self.test_subnav_items(section_name, subnav_id, item_count)
                results[f"{section_name}_items"] = items_result

            time.sleep(1)

        # 結果サマリー
        print("\n" + "="*60)
        print("📊 テスト結果サマリー")
        print("="*60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")

        print(f"\n合計: {passed}/{total} テスト合格")
        print(f"成功率: {(passed/total)*100:.1f}%")

        return passed == total

    def cleanup(self):
        """クリーンアップ"""
        print("\n🧹 ブラウザを閉じています...")
        self.driver.quit()

if __name__ == "__main__":
    tester = NavBarTester()
    try:
        success = tester.run_all_tests()
        if success:
            print("\n✅ すべてのテストが成功しました！")
        else:
            print("\n❌ 一部のテストが失敗しました")
    finally:
        tester.cleanup()
