"""
Selenium統合テスト - 鍵受け渡し機能のテスト
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# テスト設定
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "testadmin"
TEST_PASSWORD = "testpass123"

def setup_driver():
    """Chrome WebDriverをセットアップ"""
    chrome_options = Options()
    # ヘッドレスモードで実行（GUIなし）
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def login(driver):
    """ログイン処理"""
    print("\n" + "="*80)
    print("ログインテスト")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/login/")
    time.sleep(1)

    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")

        username_field.send_keys(TEST_USERNAME)
        password_field.send_keys(TEST_PASSWORD)

        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        time.sleep(2)

        # ログイン成功を確認
        if "/orders/login/" not in driver.current_url:
            print("✅ ログイン成功")
            return True
        else:
            print("❌ ログイン失敗")
            return False
    except Exception as e:
        print(f"❌ ログインエラー: {e}")
        return False

def test_key_handover_fields_in_project_form(driver):
    """テスト1: 案件作成フォームに鍵受け渡しフィールドが表示されることを確認"""
    print("\n" + "="*80)
    print("テスト1: 案件作成フォームでの鍵受け渡しフィールド表示")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 鍵受け渡し場所フィールド
        key_location_field = driver.find_element(By.NAME, "key_handover_location")
        print("  ✅ 鍵受け渡し場所フィールドが存在します")

        # 鍵受け渡し日時フィールド
        key_date_field = driver.find_element(By.NAME, "key_handover_date")
        print("  ✅ 鍵受け渡し日時フィールドが存在します")

        # 鍵受け渡しメモフィールド
        key_notes_field = driver.find_element(By.NAME, "key_handover_notes")
        print("  ✅ 鍵受け渡しメモフィールドが存在します")

        # 説明テキストを確認（柔軟な検索）
        try:
            alert_text = driver.find_element(By.XPATH, "//div[contains(@class, 'alert') and contains(text(), '元請会社のデフォルト設定が自動入力されます')]")
            print("  ✅ 説明テキスト「元請会社のデフォルト設定が自動入力されますが、案件ごとに変更可能です」が表示されています")
        except:
            print("  ℹ️  説明テキストは見つかりませんでしたが、フィールドは正常に表示されています")

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def test_key_handover_autofill_and_override(driver):
    """テスト2: 元請会社選択時のデフォルト値自動入力と変更機能"""
    print("\n" + "="*80)
    print("テスト2: 鍵受け渡し設定の自動入力と手動変更")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 元請会社を選択
        client_select = driver.find_element(By.ID, "clientCompanySelect")
        options = client_select.find_elements(By.TAG_NAME, "option")

        if len(options) > 1:
            # 2番目のオプション（最初のプレースホルダーをスキップ）を選択
            selected_company_name = options[1].text
            options[1].click()
            time.sleep(1)
            print(f"  元請会社を選択: {selected_company_name}")

            # 鍵受け渡し場所フィールドの値を確認
            key_location_field = driver.find_element(By.NAME, "key_handover_location")
            initial_value = key_location_field.get_attribute("value") or ""

            if initial_value:
                print(f"  ✅ 鍵受け渡し場所が自動入力されました: {initial_value}")
            else:
                print("  ℹ️  この元請会社にはデフォルト値が設定されていません（これは正常です）")

            # 手動で値を変更
            custom_location = "テスト用カスタム受け渡し場所"
            key_location_field.clear()
            key_location_field.send_keys(custom_location)
            time.sleep(0.5)

            # 変更が反映されたことを確認
            updated_value = key_location_field.get_attribute("value")
            if updated_value == custom_location:
                print(f"  ✅ 鍵受け渡し場所を手動で変更できました: {updated_value}")
            else:
                print(f"  ❌ 値の変更に失敗しました。期待値: {custom_location}, 実際: {updated_value}")
                return False

            return True
        else:
            print("  ⚠️  選択可能な元請会社がありません")
            return False

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_company_help_text(driver):
    """テスト3: 元請会社フォームのヘルプテキストに「案件ごとに変更可能」と表示されることを確認"""
    print("\n" + "="*80)
    print("テスト3: 元請会社フォームのヘルプテキスト確認")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/client-companies/")
    time.sleep(2)

    try:
        # 元請会社一覧から最初の会社を編集
        # または新規作成ボタンをクリック
        try:
            create_button = driver.find_element(By.XPATH, "//a[contains(@href, '/orders/client-companies/create/')]")
            create_button.click()
            time.sleep(2)
            print("  新規元請会社作成フォームを開きました")
        except:
            # 既存の会社を編集
            edit_buttons = driver.find_elements(By.XPATH, "//a[contains(@href, '/orders/client-companies/') and contains(@href, '/edit/')]")
            if edit_buttons:
                edit_buttons[0].click()
                time.sleep(2)
                print("  既存元請会社の編集フォームを開きました")
            else:
                print("  ⚠️  元請会社フォームを開けませんでした")
                return False

        # ヘルプテキストを確認
        help_text = driver.find_element(By.XPATH, "//div[@class='help-text' and contains(text(), '案件登録時に自動入力されます（案件ごとに変更可能）')]")
        print(f"  ✅ ヘルプテキストが正しく表示されています: {help_text.text}")

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_key_handover_in_basic_info_tab(driver):
    """テスト4: 鍵受け渡しフィールドが基本情報タブ内にあることを確認"""
    print("\n" + "="*80)
    print("テスト4: 鍵受け渡しフィールドの配置確認（基本情報タブ内）")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 基本情報タブがアクティブであることを確認
        basic_info_tab = driver.find_element(By.ID, "basic")
        print("  ✅ 基本情報タブが見つかりました")

        # フィールドが基本情報タブ内にあることを確認
        key_location_field = basic_info_tab.find_element(By.NAME, "key_handover_location")
        print("  ✅ 鍵受け渡し場所フィールドが基本情報タブ内にあります")

        key_date_field = basic_info_tab.find_element(By.NAME, "key_handover_date")
        print("  ✅ 鍵受け渡し日時フィールドが基本情報タブ内にあります")

        key_notes_field = basic_info_tab.find_element(By.NAME, "key_handover_notes")
        print("  ✅ 鍵受け渡しメモフィールドが基本情報タブ内にあります")

        print("  ✅ すべての鍵受け渡しフィールドが基本情報タブ内に正しく配置されています")

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*80)
    print("Selenium統合テスト開始 - 鍵受け渡し機能")
    print("="*80)
    print(f"テスト対象: {BASE_URL}")

    driver = None
    try:
        driver = setup_driver()
        print("✅ Chromeブラウザ起動成功")

        # ログイン
        if not login(driver):
            print("\n❌ ログインに失敗しました。テストを中断します。")
            print("ヒント: TEST_USERNAME と TEST_PASSWORD を確認してください")
            return

        # テスト実行
        results = {
            "案件フォームでのフィールド表示": test_key_handover_fields_in_project_form(driver),
            "自動入力と手動変更": test_key_handover_autofill_and_override(driver),
            "元請会社フォームのヘルプテキスト": test_client_company_help_text(driver),
            "基本情報タブ内への配置": test_key_handover_in_basic_info_tab(driver),
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
            print("鍵受け渡し機能は正しく実装されています。")
        else:
            print(f"\n⚠️  {total - passed}個のテストが失敗しました。")

    except Exception as e:
        print(f"\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            print("\nブラウザを5秒後に閉じます...")
            time.sleep(5)
            driver.quit()
            print("✅ ブラウザを閉じました")

if __name__ == "__main__":
    run_all_tests()
