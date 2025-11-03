# ナビゲーションバー リンクチェック

## ✅ 保持するメニュー（全て有効）

### 1. ダッシュボード
- [x] ダッシュボード: `/orders/` → `order_management:dashboard`

### 2. 案件管理
- [x] 案件一覧: `/orders/project/` → `order_management:project_list`
- [x] 新規案件登録: `/orders/project/create/` → `order_management:project_create`
- [x] 受注案件（フィルタ）: `/orders/project/?status=受注`
- [x] 進行中案件（フィルタ）: `/orders/project/?status=進行中`

### 3. 業者管理
- [x] 受注業者: `/orders/contractor-dashboard/` → `order_management:contractor_dashboard`
- [x] 発注業者: `/orders/ordering-dashboard/` → `order_management:ordering_dashboard`
- [x] 業者マスター: `/subcontracts/contractors/` → `subcontract_management:contractor_list`
- [x] 発注管理ダッシュボード: `/subcontracts/` → `subcontract_management:dashboard`

### 4. 経理・支払
- [x] 経理ダッシュボード: `/orders/accounting/` → `order_management:accounting_dashboard`
- [x] キャッシュフロー管理: `/orders/cashflow/` → `order_management:cashflow_dashboard`
- [x] 売上予測: `/orders/forecast/` → `order_management:forecast_dashboard`
- [x] レポート管理: `/orders/report-dashboard/` → `order_management:report_dashboard`
- [x] 入金管理: `/orders/receipt/` → `order_management:receipt_dashboard`
- [x] 出金管理: `/orders/payment/` → `order_management:payment_dashboard`
- [x] 支払い追跡: `/subcontracts/payment-tracking/` → `subcontract_management:payment_tracking`
- [x] 利益分析: `/subcontracts/profit-analysis/` → `subcontract_management:profit_analysis_list`

### 5. カレンダー・業績
- [x] 施工カレンダー: `/orders/construction-calendar/` → `order_management:construction_calendar`
- [x] ガントチャート: `/orders/gantt-chart/` → `order_management:gantt_chart`
- [x] 月次業績: `/orders/performance-monthly/` → `order_management:performance_monthly`

### 6. システム管理
- [x] システム管理: `/admin/` → Django Admin

## ❌ 削除済み（コメントアウト済み）

### 現場調査（surveys）
- 調査一覧
- スケジュール管理
- 調査予約作成
- 調査員管理

## 📝 テスト手順

1. Renderでデプロイが完了するのを待つ
2. https://project-accounting-system.onrender.com にアクセス
3. ログイン: admin / admin123
4. 上記の各リンクを順番にクリックして動作確認
5. エラーが出るページがあれば、エラーメッセージを記録

## 🔍 期待される動作

すべてのリンクは：
- ✅ 404エラーが出ない
- ✅ TemplateDoesNotExist エラーが出ない
- ✅ ページが正常に表示される
- ✅ データがない場合は「データがありません」的なメッセージが表示される

## 🚨 既知の問題

- キャッシュフローダッシュボード: 修正済み（テンプレートパス）
- 現場調査リンク: 削除済み（コメントアウト）
