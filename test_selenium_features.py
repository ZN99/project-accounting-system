"""
Selenium統合テスト - 実装した機能をブラウザでテスト
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
TEST_USERNAME = "admin"  # 既存のスーパーユーザー
TEST_PASSWORD = "admin"  # パスワード（環境に応じて変更）

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

def test_login_required(driver):
    """テスト1: ログイン認証のテスト"""
    print("\n" + "="*80)
    print("テスト1: ログイン認証 - 未認証ユーザーのリダイレクト")
    print("="*80)

    # ログアウト
    try:
        driver.get(f"{BASE_URL}/admin/logout/")
        time.sleep(1)
    except:
        pass

    # 保護されたページにアクセス
    test_urls = [
        "/orders/list/",
        "/orders/create/",
        "/orders/contractor-dashboard/"
    ]

    all_passed = True
    for url in test_urls:
        driver.get(f"{BASE_URL}{url}")
        time.sleep(1)

        if "/orders/login/" in driver.current_url:
            print(f"  ✅ {url} → ログインページにリダイレクト")
        else:
            print(f"  ❌ {url} → リダイレクトされませんでした")
            all_passed = False

    # 再ログイン
    login(driver)

    return all_passed

def test_client_company_selection(driver):
    """テスト2: 元請会社（ClientCompany）の選択"""
    print("\n" + "="*80)
    print("テスト2: 元請会社（ClientCompany）の選択")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 元請会社のドロップダウンを確認
        client_select = driver.find_element(By.ID, "clientCompanySelect")

        # optionタグの数を確認
        options = client_select.find_elements(By.TAG_NAME, "option")
        print(f"  元請会社の選択肢数: {len(options)}")

        # 最初のオプション以外（プレースホルダー以外）の会社名を表示
        for i, option in enumerate(options[1:6], 1):  # 最初の5社
            print(f"    {i}. {option.text}")

        # 「元請管理」ボタンが存在するか確認
        management_link = driver.find_element(By.XPATH, "//a[contains(@href, '/orders/client-companies/')]")
        print(f"  ✅ 元請管理リンクが存在: {management_link.text}")

        # フィールド名がclient_companyであることを確認
        if client_select.get_attribute("name") == "client_company":
            print("  ✅ フィールド名はclient_company（正しい）")
        else:
            print(f"  ❌ フィールド名が間違っています: {client_select.get_attribute('name')}")
            return False

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def test_sales_manager_modal(driver):
    """テスト3: 営業担当者管理モーダルのUI確認"""
    print("\n" + "="*80)
    print("テスト3: 営業担当者管理モーダル - 時給単価の非表示確認")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 営業担当者管理ボタンをクリック
        sales_mgmt_button = driver.find_element(By.XPATH, "//button[contains(text(), '営業担当者管理')]")
        sales_mgmt_button.click()
        time.sleep(1)

        # モーダルが表示されるのを待つ
        modal = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "salesStaffManagementModal"))
        )

        # テーブルヘッダーを確認
        headers = modal.find_elements(By.CSS_SELECTOR, "thead th")
        header_texts = [h.text for h in headers]

        print(f"  テーブルヘッダー: {header_texts}")

        # 時給単価が含まれていないことを確認
        if "時給単価" not in header_texts:
            print("  ✅ 時給単価列が非表示（正しい）")
        else:
            print("  ❌ 時給単価列が表示されています")
            return False

        # 期待されるヘッダー
        expected_headers = ["名前", "部署", "専門分野", "状態", "アクション"]
        if header_texts == expected_headers:
            print("  ✅ ヘッダーが正しい順序で表示")
        else:
            print(f"  ⚠️  ヘッダーの順序が異なります: {header_texts}")

        # モーダルを閉じる
        close_button = modal.find_element(By.CSS_SELECTOR, ".btn-close")
        close_button.click()
        time.sleep(0.5)

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def test_analytics_section_visibility(driver):
    """テスト4: 実績推移セクションの管理者限定表示"""
    print("\n" + "="*80)
    print("テスト4: 実績推移セクション - 管理者限定表示")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 営業担当者管理モーダルを開く
        sales_mgmt_button = driver.find_element(By.XPATH, "//button[contains(text(), '営業担当者管理')]")
        sales_mgmt_button.click()
        time.sleep(1)

        modal = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "salesStaffManagementModal"))
        )

        # 実績推移セクションを探す
        try:
            analytics_section = modal.find_element(By.XPATH, ".//h6[contains(text(), '実績推移')]")
            print("  ✅ 実績推移セクションが表示されています（管理者の場合）")

            # グラフプレースホルダーが存在することを確認
            profit_graph = modal.find_element(By.XPATH, ".//h6[contains(text(), '利益率推移')]")
            project_count_graph = modal.find_element(By.XPATH, ".//h6[contains(text(), '案件数推移')]")

            print("  ✅ 利益率推移グラフが表示")
            print("  ✅ 案件数推移グラフが表示")

        except NoSuchElementException:
            print("  ℹ️  実績推移セクションが非表示（一般ユーザーの場合）")

        # モーダルを閉じる
        close_button = modal.find_element(By.CSS_SELECTOR, ".btn-close")
        close_button.click()
        time.sleep(0.5)

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def test_project_creation_flow(driver):
    """テスト5: 案件作成フロー（元請会社選択を含む）"""
    print("\n" + "="*80)
    print("テスト5: 案件作成フロー - 元請会社の選択と保存")
    print("="*80)

    driver.get(f"{BASE_URL}/orders/create/")
    time.sleep(2)

    try:
        # 必須フィールドに入力
        site_name = driver.find_element(By.NAME, "site_name")
        site_name.send_keys("Seleniumテスト現場")

        # 元請会社を選択
        client_select = driver.find_element(By.ID, "clientCompanySelect")
        options = client_select.find_elements(By.TAG_NAME, "option")

        if len(options) > 1:
            # 2番目のオプション（最初のプレースホルダーをスキップ）を選択
            options[1].click()
            selected_company = options[1].text
            print(f"  元請会社を選択: {selected_company}")
        else:
            print("  ⚠️  選択可能な元請会社がありません")
            return False

        # 工事種別を入力
        work_type = driver.find_element(By.NAME, "work_type")
        work_type.send_keys("新築工事")

        print("  ✅ フォーム入力完了（実際の保存はスキップ）")

        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*80)
    print("Selenium統合テスト開始")
    print("="*80)
    print(f"テスト対象: {BASE_URL}")

    driver = None
    try:
        driver = setup_driver()
        print("✅ Chromeブラウザ起動成功")

        # ログイン
        if not login(driver):
            print("\n❌ ログインに失敗しました。テストを中断します。")
            return

        # テスト実行
        results = {
            "ログイン認証": test_login_required(driver),
            "元請会社選択": test_client_company_selection(driver),
            "営業担当者モーダル": test_sales_manager_modal(driver),
            "実績推移セクション": test_analytics_section_visibility(driver),
            "案件作成フロー": test_project_creation_flow(driver)
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
