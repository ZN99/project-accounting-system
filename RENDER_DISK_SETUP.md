# Render Disk セットアップガイド

このアプリケーションは、ユーザーがアップロードしたファイル（PDFなど）を永続的に保存するために、Render Diskを使用します。

## なぜRender Diskが必要か？

Renderの無料プランでは、サーバーが再起動するたびにファイルが消えてしまいます。永続的にファイルを保存するには、Render Diskを追加する必要があります。

## セットアップ手順

### 1. Renderダッシュボードにログイン

https://dashboard.render.com にアクセス

### 2. Webサービスを選択

デプロイ済みのWebサービス（project-accounting-system）を選択

### 3. Diskを追加

1. 左メニューから **「Disks」** を選択
2. **「Add Disk」** ボタンをクリック
3. 以下の情報を入力：

   - **Name**: `media-files`（任意の名前）
   - **Mount Path**: `/opt/render/project/media`（重要：この値を正確に入力）
   - **Size**: `1 GB`（必要に応じて増やす。最小1GB〜最大512GB）

4. **「Create」** をクリック

### 4. サービスを再デプロイ

Diskを追加すると、自動的にサービスが再デプロイされます。

### 5. 動作確認

1. アプリケーションにログイン
2. 案件詳細ページでファイルをアップロード
3. 別のPCまたはブラウザからログインして、同じファイルがダウンロードできることを確認

## 料金

- **1GB**: 月額 $1
- **10GB**: 月額 $10
- **100GB**: 月額 $100

必要に応じてサイズを変更できます（Renderダッシュボードから）。

## トラブルシューティング

### ファイルがアップロードできない

1. Diskが正しくマウントされているか確認（Renderダッシュボード → Disks）
2. Mount Pathが `/opt/render/project/media` になっているか確認
3. サービスログを確認（Renderダッシュボード → Logs）

### ファイルがダウンロードできない

1. ファイルが正しくアップロードされているか確認
2. ブラウザのコンソールでエラーを確認（F12キー）
3. URLが `/media/...` で始まっているか確認

### 既存のファイルを移行したい

ローカル環境の `media/` フォルダをRender Diskに移行する場合：

1. Render SSH経由でファイルをアップロード（Renderの公式ドキュメント参照）
2. または、アプリケーションから再アップロード

## 技術詳細

- **開発環境**: ローカルの `media/` フォルダを使用
- **本番環境（Render）**: `/opt/render/project/media` を使用
- 環境変数 `RENDER` が設定されている場合、自動的にRender Diskを使用

## 参考リンク

- [Render Disks公式ドキュメント](https://render.com/docs/disks)
- [Django Media Files](https://docs.djangoproject.com/en/stable/howto/static-files/)
