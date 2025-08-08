# Video Message API (Backend)

D-ID APIを使用した動画メッセージ生成バックエンド

## セットアップ

### 1. 仮想環境作成
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存関係インストール
```bash
pip install -r requirements.txt
```

### 3. 環境変数設定
`.env`ファイルを作成し、D-ID APIキーを設定
```
DID_API_KEY=your_api_key_here
```

### 4. サーバー起動
```bash
python main.py
```

または

```bash
uvicorn main:app --reload --port 8000
```

## API仕様

### POST /api/generate
動画生成エンドポイント

**リクエスト:**
- `image`: 画像ファイル (multipart/form-data)
- `text`: メッセージテキスト (100文字以内)

**レスポンス:**
```json
{
  "success": true,
  "video_url": "https://...",
  "message": "動画生成が完了しました"
}
```

## 自動ドキュメント

http://localhost:8000/docs でSwagger UIを確認できます