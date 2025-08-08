# Video Message App

D-ID APIを使用した動画メッセージ生成アプリケーション（MVP）

## 概要

写真とテキストメッセージから、話している動画を自動生成するWebアプリケーションです。

## 技術構成

- **バックエンド**: Python + FastAPI
- **フロントエンド**: React 19
- **API**: D-ID Talks API
- **開発期間**: 2週間（MVP）

## セットアップ手順

### 1. プロジェクトクローン
```bash
git clone <repository>
cd video-message-app
```

### 2. バックエンドセットアップ
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. フロントエンドセットアップ
```bash
cd ../frontend
npm install --legacy-peer-deps
```

### 4. 環境変数設定
`backend/.env`ファイルに D-ID APIキーを設定
```
DID_API_KEY=your_api_key_here
```

## 起動方法

### バックエンド（ポート8000）
```bash
cd backend
source venv/bin/activate
python main.py
```

### フロントエンド（ポート3000）
```bash
cd frontend
npm start
```

## 機能

### 実装済み機能
- ✅ 画像アップロード（JPG/PNG、5MB以下）
- ✅ テキスト入力（100文字制限）
- ✅ D-ID APIによる動画生成
- ✅ 動画プレビュー・ダウンロード
- ✅ エラーハンドリング

### 未実装機能（次フェーズ）
- ❌ ユーザー認証
- ❌ BGM合成
- ❌ データ永続化
- ❌ モバイルアプリ
- ❌ 課金システム

## API仕様

### POST /api/generate
**リクエスト:**
- `image`: 画像ファイル
- `text`: メッセージ（100文字以内）

**レスポンス:**
```json
{
  "success": true,
  "video_url": "https://...",
  "message": "動画生成が完了しました"
}
```

## 開発ガイド

### API ドキュメント
http://localhost:8000/docs

### ディレクトリ構造
```
video-message-app/
├── backend/          # Python FastAPI
├── frontend/         # React App
└── README.md
```

## 注意事項

- D-ID APIの無料枠は月20分です
- 生成には15-30秒程度かかります
- インターネット接続が必要です