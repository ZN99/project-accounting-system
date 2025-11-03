# 案件管理・経理管理システム

建設業向けの案件管理と経理管理に特化したDjangoアプリケーションです。

## 主な機能

### 案件管理 (order_management)
- **案件一覧・詳細管理**: 案件の進捗状況、ステータス管理
- **顧客管理**: 顧客情報の登録・管理
- **進捗管理**: 複雑なステップワークフロー対応
- **見積書管理**: 見積書の作成・管理
- **発注管理**: 資材発注の管理
- **支払管理**: 支払い記録の管理

### 経理管理
- **会計ダッシュボード**: 入金・支払いの可視化
- **通帳ビュー (Passbook)**: 入出金の時系列表示
- **レシート管理**: レシート記録と一覧
- **キャッシュフロー分析**: 資金繰りの予測と分析
- **レポート機能**: 財務レポートの生成

### 下請け管理 (subcontract_management)
- **下請け業者管理**: 業者情報の登録・管理
- **内部作業員管理**: 社内スタッフの管理
- **下請け契約管理**: 契約の記録と追跡

## 技術スタック

- **Django 4.2.6**: Webフレームワーク
- **Python 3.11+**: プログラミング言語
- **SQLite**: データベース (開発環境)
- **Bootstrap 4**: UIフレームワーク
- **jQuery 3.7.0**: フロントエンドライブラリ

## セットアップ

### 1. 必要なパッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. データベースのマイグレーション

```bash
python manage.py migrate
```

### 3. スーパーユーザーの作成

```bash
python manage.py createsuperuser
```

### 4. 開発サーバーの起動

```bash
python manage.py runserver
```

ブラウザで http://localhost:8000/ にアクセスしてください。

## 主要なURL

- `/orders/login/` - ログイン画面
- `/orders/dashboard/` - ダッシュボード
- `/orders/list/` - 案件一覧
- `/orders/accounting/` - 会計ダッシュボード
- `/orders/passbook/` - 通帳ビュー
- `/subcontracts/` - 下請け管理
- `/admin/` - Django管理画面

## プロジェクト構造

```
project_accounting_system/
├── construction_dispatch/    # Djangoプロジェクト設定
│   ├── settings.py          # 設定ファイル
│   ├── urls.py              # URLルーティング
│   └── wsgi.py              # WSGI設定
├── order_management/         # 案件管理・経理管理アプリ
│   ├── models.py            # データモデル
│   ├── views.py             # ビューロジック
│   ├── forms.py             # フォーム定義
│   ├── urls.py              # URLパターン
│   └── templates/           # テンプレート
├── subcontract_management/   # 下請け管理アプリ
│   ├── models.py            # データモデル
│   ├── views.py             # ビューロジック
│   └── templates/           # テンプレート
├── static/                  # 静的ファイル
├── media/                   # アップロードファイル
├── manage.py                # Django管理コマンド
└── requirements.txt         # 依存パッケージ
```

## 開発

### テストデータの作成

```bash
python manage.py shell
# Djangoシェル内でテストデータ作成スクリプトを実行
```

### 静的ファイルの収集

```bash
python manage.py collectstatic
```

## 注意事項

- **本番環境**: `DEBUG = False`に設定し、`SECRET_KEY`を変更してください
- **セキュリティ**: `ALLOWED_HOSTS`を適切に設定してください
- **データベース**: 本番環境ではPostgreSQLまたはMySQLを推奨します

## ライセンス

このプロジェクトは内部使用のためのものです。

## サポート

質問や問題がある場合は、開発チームにお問い合わせください。
