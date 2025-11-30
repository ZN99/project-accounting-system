# アーカイブされた経理機能（旧版）

## 📦 アーカイブ日時
2025年11月30日

## ⚠️ 重要な注意事項
このディレクトリには、旧バージョンの経理機能が格納されています。
これらの機能は参照専用であり、**実運用には使用しないでください**。

新しい経理機能は `services/cashflow_service.py` および `views_payment_management.py` を使用してください。

## 📂 アーカイブされたファイル

### Python ビュー・ユーティリティ
- `views_accounting_old.py` - 会計ダッシュボード（旧）
- `views_payment_old.py` - 支払いダッシュボード（旧）
- `views_receipt_old.py` - 入金ダッシュボード（旧）
- `views_cashflow_old.py` - キャッシュフロー管理（旧）
- `cashflow_utils_old.py` - キャッシュフロー集計ユーティリティ（旧）
- `forecast_utils_old.py` - 予測ユーティリティ（旧）

### テンプレート
- `accounting_dashboard.html` - 会計ダッシュボード画面
- `payment_dashboard.html` - 支払いダッシュボード画面
- `payment_dashboard_improved.html` - 改善版支払いダッシュボード
- `payment_dashboard_contractor_focused.html` - 業者フォーカス版支払いダッシュボード
- `receipt_dashboard.html` - 入金ダッシュボード画面
- `cashflow_dashboard.html` - キャッシュフロー管理画面
- `forecast_dashboard.html` - 売上予測画面
- `receivables_detail.html` - 売掛金詳細画面
- `payables_detail.html` - 買掛金詳細画面
- `report_cashflow_view.html` - キャッシュフローレポートビュー
- `report_forecast_view.html` - 予測レポートビュー

## 🔧 アーカイブ理由
既存の経理機能は以下の理由によりアーカイブされました：
1. **複雑すぎる設計** - 実際の業務フローと乖離
2. **CashFlowTransactionモデルの二重管理** - Subcontract/Projectモデルと重複
3. **使いにくいUI** - 実用性に欠ける画面設計
4. **保守困難** - 機能追加・修正が困難な構造

## 🆕 新しい経理機能
新しい経理機能では以下のアプローチを採用しています：
- **シンプルな設計** - 既存モデル(Subcontract/Project)を直接活用
- **計算レイヤー方式** - データベースに新規テーブルを作成せず計算で実現
- **実用的なUI** - シンプルで使いやすい2タブ構成
- **保守性** - サービス層による明確な責任分離

## 🔍 参照方法
システム管理 > アーカイブ機能 から、これらの旧機能を閲覧できます。

## 🗑️ データベースモデル
`CashFlowTransaction` モデルは削除されず、データベースに残ります。
必要に応じて将来的に完全削除を検討してください。
