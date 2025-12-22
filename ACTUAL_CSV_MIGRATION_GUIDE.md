# 実際のCSVファイルからのデータ移行手順書

**最終更新日**: 2025年12月22日

---

## 対象CSVファイル

このガイドは、以下の実際のCSVファイルからデータを移行する手順を説明します：

1. **`新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv`** - 案件・元請業者情報
2. **`新_工事受注FMT_202507  - 依頼側FMT.csv`** - 下請け業者・支払い情報

---

## 📌 推奨方法: Webインターフェースから実行

**最も簡単で安全な方法です！**

1. **Webブラウザでアクセス**
   ```
   http://localhost:8000/orders/csv-import/
   ```

2. **CSVファイルをアップロード**
   - 「受注側CSV」ファイルを選択: `新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv`
   - 「依頼側CSV」ファイルを選択: `新_工事受注FMT_202507  - 依頼側FMT.csv`

3. **Dry-runでテスト実行**
   - 「Dry-run（テスト実行）」にチェック
   - 「インポート実行」ボタンをクリック
   - 結果を確認（データは保存されません）

4. **本番実行**
   - 問題がなければ、Dry-runのチェックを外す
   - 再度「インポート実行」ボタンをクリック
   - 完了メッセージと統計情報を確認

**メリット:**
- ✅ コマンドライン不要
- ✅ ファイルをドラッグ&ドロップで簡単アップロード
- ✅ 実行結果がわかりやすく表示される
- ✅ エラーが発生しても詳細なログが確認できる
- ✅ 経理・役員のみがアクセス可能（セキュア）

**アクセス権限:**
- 経理ユーザー（`user_role='accounting'`）
- 役員ユーザー（`user_role='executive'`）

---

## コマンドライン実行（上級者向け）

### クイックスタート

```bash
# 1. CSVファイルの場所を確認
ls -la backups/*.csv

# 2. DRY RUNでテスト実行（データは保存されません）
python manage.py import_project_csv \
  "backups/新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv" \
  "backups/新_工事受注FMT_202507  - 依頼側FMT.csv" \
  --dry-run

# 3. 問題がなければ本番実行
python manage.py import_project_csv \
  "backups/新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv" \
  "backups/新_工事受注FMT_202507  - 依頼側FMT.csv"
```

---

## 詳細手順

### 前提条件

```bash
# プロジェクトディレクトリに移動
cd /Users/zainkhalid/Dev/project-accounting-system

# 仮想環境が有効であることを確認（pyenv使用の場合）
python --version  # Python 3.11以上である必要があります

# マイグレーションが最新であることを確認
python manage.py migrate
```

### 手順1: CSVファイルの配置確認

```bash
# バックアップディレクトリ内のCSVファイルを確認
ls -la backups/*.csv

# 以下の2ファイルが存在することを確認：
# - 新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv
# - 新_工事受注FMT_202507  - 依頼側FMT.csv
```

### 手順2: DRY RUN（テスト実行）

実際にデータベースに保存せず、処理内容を確認：

```bash
python manage.py import_project_csv \
  "backups/新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv" \
  "backups/新_工事受注FMT_202507  - 依頼側FMT.csv" \
  --dry-run
```

**出力例**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CSV一括インポート開始
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ DRY-RUNモード（データは保存されません）

📂 CSV読み込み中...
  ✓ 受注側CSV: 150行読み込み
  ✓ 依頼側CSV: 180行読み込み

🔗 管理番号でグループ化中...
  ✓ グループ化完了: 150件

📥 インポート処理中... (0/150)

[1/150] 1: 丸山シャンテ104 クロス張り替え
  [DRY-RUN] Project作成: M250001 - 丸山シャンテ104 クロス張り替え
    [DRY-RUN] Subcontract作成: 株式会社Sways - ¥35,020

[2/150] 2: 横浜マンション新築
  [DRY-RUN] Project作成: M250002 - 横浜マンション新築
    [DRY-RUN] Subcontract作成: ABC建設 - ¥120,000

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
インポート統計
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
プロジェクト: 150件作成
元請業者: 25件作成, 0件既存
下請業者: 45件作成, 0件既存
下請契約: 180件作成
スキップ: 0件
エラー: 0件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠ DRY-RUNモードのため、データは保存されていません
```

### 手順3: 本番実行

DRY RUNで問題がなければ、実際にデータをインポート：

```bash
python manage.py import_project_csv \
  "backups/新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv" \
  "backups/新_工事受注FMT_202507  - 依頼側FMT.csv"
```

**自動的に以下が実行されます：**
- ✅ バックアップ作成（既存データの保護）
- ✅ 元請業者の自動作成
- ✅ 下請け業者の自動作成
- ✅ 案件データのインポート
- ✅ 下請け契約のインポート
- ✅ 管理番号の自動変換（1 → M250001）

### 手順4: データ検証

インポート後、データを確認：

```bash
# Djangoシェルを起動
python manage.py shell
```

```python
from order_management.models import ClientCompany, Project
from subcontract_management.models import Contractor, Subcontract

# データ数を確認
print(f"元請業者: {ClientCompany.objects.count()}件")
print(f"下請け業者: {Contractor.objects.count()}件")
print(f"案件: {Project.objects.count()}件")
print(f"下請け契約: {Subcontract.objects.count()}件")

# 最初の案件を確認
project = Project.objects.filter(management_no__startswith='M25').first()
if project:
    print(f"\n最初の案件:")
    print(f"  管理No: {project.management_no}")
    print(f"  現場名: {project.site_name}")
    print(f"  元請業者: {project.client_company.company_name if project.client_company else 'なし'}")
    print(f"  受注金額: ¥{project.order_amount:,}")
```

または、ブラウザで確認：
```
http://localhost:8000/orders/list/
```

---

## オプション

### バックアップをスキップ

既にバックアップを取得している場合：

```bash
python manage.py import_project_csv \
  <受注側CSV> <依頼側CSV> \
  --no-backup
```

### 詳細ログを表示

処理内容を詳しく確認：

```bash
python manage.py import_project_csv \
  <受注側CSV> <依頼側CSV> \
  --verbosity=2
```

---

## データマッピング

### CSV → データベース変換ルール

#### 管理番号

```
CSV: 1    → アプリ: M250001
CSV: 123  → アプリ: M250123
CSV: 5678 → アプリ: M255678
```

#### 受注ヨミ → プロジェクトステータス

```
受注 → 受注確定
NG   → NG
(空) → 立ち会い待ち
```

#### 出金状況 → 支払ステータス

```
済   → paid（支払済み）
未定 → unpaid（未払い）
(空) → unpaid（未払い）
```

#### 金額フォーマット

```
¥35,020 → 35020
35,020  → 35020
空欄    → 0
```

#### 日付フォーマット

```
2025/07/03  → 2025-07-03
2025-07-03  → 2025-07-03
2025年7月3日 → 2025-07-03
```

---

## トラブルシューティング

### Q1: "FileNotFoundError" エラーが出る

**原因**: CSVファイルが見つからない

**解決策**:
```bash
# CSVファイルの場所を確認
ls -la backups/*.csv

# ファイル名にスペースが含まれる場合は必ず引用符で囲む
python manage.py import_project_csv \
  "backups/新_工事受注FMT_202507  - 受注側FMT_現場別（見積り受注で記載）.csv" \
  "backups/新_工事受注FMT_202507  - 依頼側FMT.csv"
```

### Q2: "UnicodeDecodeError" エラーが出る

**原因**: 文字コードの問題

**解決策**:
- スクリプトは自動的に文字コードを検出します（UTF-8, Shift-JIS, CP932対応）
- エラーが出る場合は、CSVファイルをUTF-8で保存し直してください

```bash
# 文字コード確認
file -I backups/*.csv

# UTF-8に変換（必要な場合）
iconv -f SHIFT-JIS -t UTF-8 元のファイル.csv > 新しいファイル.csv
```

### Q3: 重複データが作成される

**動作**:
- **案件（Project）**: 管理番号が重複している場合は**スキップ**
- **元請業者（ClientCompany）**: 会社名が同じ場合は既存のものを使用
- **下請け業者（Contractor）**: 業者名が同じ場合は既存のものを使用

**確認方法**:
```python
# 重複データを確認
from order_management.models import Project
duplicates = Project.objects.values('management_no').annotate(count=Count('id')).filter(count__gt=1)
print(f"重複案件: {duplicates.count()}件")
```

### Q4: エラーが発生してインポートが止まった

**解決策**:
1. エラーメッセージを確認
2. 該当するCSV行を修正
3. `--dry-run`で再度テスト
4. 問題がなければ本番実行

```bash
# 詳細なエラーログを表示
python manage.py import_project_csv <受注側CSV> <依頼側CSV> --dry-run --verbosity=2
```

### Q5: データベースをクリーンな状態に戻したい

**警告**: 全データが削除されます！

```bash
# データベースを完全リセット
python manage.py flush

# マイグレーションを再実行
python manage.py migrate

# 再度インポート
python manage.py import_project_csv <受注側CSV> <依頼側CSV>
```

---

## インポート仕様の詳細

### 自動作成されるデータ

#### 元請業者（ClientCompany）
- 会社名（company_name）
- 住所（address）

#### 下請け業者（Contractor）
- 業者名（name）
- 住所（address）
- 業者種別（contractor_type）: "partner"に設定

#### 案件（Project）
- 管理番号（management_no）: M25xxxx形式に自動変換
- 現場名（site_name）
- 現場住所（site_address）
- 工事種別（work_type）
- 受注金額（order_amount）
- プロジェクトステータス（project_status）
- 支払期日（payment_due_date）
- 契約日（contract_date）
- 駐車場代（parking_fee）
- 金額差分（amount_difference）
- 案件担当（project_manager）
- 請求書発行フラグ（invoice_issued）
- 諸経費項目①②（expense_item_1, expense_item_2）
- 諸経費金額①②（expense_amount_1, expense_amount_2）

#### 下請け契約（Subcontract）
- プロジェクト（project）
- 下請け業者（contractor）
- 契約金額（contract_amount）
- 請求額（billed_amount）
- 支払予定日（payment_due_date）
- 支払日（payment_date）
- 支払ステータス（payment_status）
- 部材費項目①②③（material_item_1, material_item_2, material_item_3）
- 部材費金額①②③（material_cost_1, material_cost_2, material_cost_3）

### スキップされるケース

- 現場名が空の行
- 既に同じ管理番号の案件が存在する場合
- 下請け業者名が空の場合

---

## ベストプラクティス

### インポート前

- ✅ **必ずDRY RUNを実行**して内容を確認
- ✅ **バックアップを取得**（自動バックアップが有効ですが、手動でも推奨）
- ✅ **CSVファイルをExcelで開いて内容を確認**
- ✅ **テスト環境で先に試す**（可能な場合）

```bash
# 手動バックアップ
python manage.py backup_data
```

### インポート中

- ⏸️ エラーが出た場合は**エラーメッセージを保存**
- ⏸️ 大量データの場合は**進捗状況をメモ**

### インポート後

- ✅ **Webインターフェースで確認**
- ✅ **データ数を比較**（CSV行数 vs データベース件数）
- ✅ **金額の合計を確認**
- ✅ **いくつかの案件を詳細確認**

---

## まとめ

### インポートの流れ

```
1. CSVファイルを配置
   └─ backups/ ディレクトリに2つのCSVファイル

2. DRY RUNで確認
   └─ python manage.py import_project_csv <受注側CSV> <依頼側CSV> --dry-run

3. 本番実行
   └─ python manage.py import_project_csv <受注側CSV> <依頼側CSV>

4. データ検証
   └─ Djangoシェルまたはブラウザで確認

5. 必要に応じて修正
   └─ エラーがあればCSVを修正して再実行
```

### 注意事項

- ⚠️ ファイル名にスペースが含まれるため、必ず**引用符で囲む**
- ⚠️ **DRY RUNを必ず実行**してから本番実行
- ⚠️ 管理番号は自動的に**M25xxxx形式に変換**されます
- ⚠️ 同じ管理番号の案件は**スキップ**されます（上書きしません）
- ⚠️ エンコーディングは自動検出されますが、**UTF-8推奨**

### 参考情報

- [既存のインポートスクリプト](./order_management/management/commands/import_project_csv.py)
- [Django管理コマンド公式ドキュメント](https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/)
- [バックアップガイド](./BACKUP_GUIDE.md)

---

**最終更新**: 2025年12月22日
**スクリプト**: `order_management/management/commands/import_project_csv.py`
