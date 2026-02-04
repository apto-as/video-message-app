# Video Message App (Frontend)

動画メッセージ生成アプリのReactフロントエンド

## セットアップ

### 1. 依存関係インストール
```bash
npm install --legacy-peer-deps
```

### 2. 開発サーバー起動
```bash
npm start
```

ブラウザで http://localhost:3000 を開く

## 機能

- 画像アップロード（ドラッグ&ドロップ対応）
- テキスト入力（100文字制限）
- リップシンク動画生成（MuseTalk使用）
- 動画プレビュー・ダウンロード

## 技術スタック

- React 19
- axios (API通信)
- react-dropzone (ファイルアップロード)

## 注意事項

バックエンドサーバー（http://localhost:8000）が起動している必要があります