# フェーズ0: MVP開発計画書

## プロジェクト概要

### 目標
D-ID APIを使用した動画生成の基本機能を実装し、技術的実現可能性を検証する

### 期間
2週間（10営業日）

### 成果物
- 動作するWebアプリケーション（ローカル環境）
- D-ID API統合の技術検証
- 次フェーズへの技術的知見

---

## 機能仕様

### 実装する機能

#### 1. 画像アップロード機能
```yaml
仕様:
  - 対応形式: JPG, PNG
  - 最大サイズ: 5MB
  - 推奨解像度: 512x512px以上
  - バリデーション: ファイルタイプ、サイズ、画像形式チェック
  
UI:
  - ドラッグ&ドロップ対応
  - プレビュー表示
  - エラーメッセージ表示
```

#### 2. テキスト入力機能
```yaml
仕様:
  - 最大文字数: 100文字
  - 対応言語: 日本語
  - バリデーション: 文字数制限、空文字チェック
  
UI:
  - リアルタイム文字数表示
  - プレースホルダー: "お誕生日おめでとう！"
  - エラーメッセージ表示
```

#### 3. 動画生成機能
```yaml
仕様:
  - API: D-ID Talks API
  - 音声: ja-JP-NanamiNeural
  - 生成時間: 15-30秒
  - 出力形式: MP4
  
処理フロー:
  1. 画像をBase64エンコード
  2. D-ID APIにリクエスト送信
  3. 生成IDを受け取り
  4. ポーリングで生成状況確認
  5. 完成動画URLを取得
```

#### 4. 動画プレビュー・ダウンロード機能
```yaml
仕様:
  - プレビュー: HTML5 video要素
  - ダウンロード: 動画ファイル直接DL
  - 形式: MP4
  
UI:
  - 動画プレーヤー
  - ダウンロードボタン
  - 新しく生成ボタン
```

#### 5. エラーハンドリング
```yaml
対応エラー:
  - ファイルアップロードエラー
  - D-ID APIエラー
  - ネットワークエラー
  - 生成タイムアウト
  
エラー表示:
  - 分かりやすいメッセージ
  - 対処方法の提示
  - リトライ機能
```

### 実装しない機能
- ❌ ユーザー認証・登録
- ❌ データベース（永続化）
- ❌ BGM合成
- ❌ 複数画像対応
- ❌ 動画編集機能
- ❌ SNS共有機能
- ❌ 多言語対応
- ❌ 課金システム
- ❌ セキュリティ対策（基本的な検証のみ）

---

## 技術仕様

### アーキテクチャ

```
[React Frontend] ←→ [Express Backend] ←→ [D-ID API]
       ↓                    ↓
[Local Storage]      [Temporary Files]
```

### 技術スタック

#### フロントエンド
```yaml
Framework: React 18
Language: JavaScript (ES6+)
Style: CSS3 + CSS Modules
HTTP_Client: Axios
File_Upload: react-dropzone
UI_Components: 
  - react-loader-spinner (ローディング)
  - カスタムコンポーネント
```

#### バックエンド（Python）
```yaml
Runtime: Python 3.9+
Framework: FastAPI
Language: Python
File_Upload: python-multipart
HTTP_Client: httpx (非同期)
Environment: python-dotenv
CORS: fastapi.middleware.cors
Data_Validation: pydantic
```

#### 開発環境
```yaml
Package_Manager: pip + venv (Python), npm (React)
Version_Control: Git
Editor: VS Code
Python_Formatter: black + isort
Python_Linter: flake8
Testing: Manual Testing（自動テストは除外）
```

### プロジェクト構造

```
video-message-app/
├── backend/
│   ├── main.py              # FastAPI サーバー
│   ├── routers/
│   │   └── video.py         # 動画生成API ルート
│   ├── services/
│   │   └── did_client.py    # D-ID API クライアント
│   ├── models/
│   │   └── schemas.py       # Pydantic データモデル
│   ├── core/
│   │   └── config.py        # 設定管理
│   ├── .env                 # 環境変数
│   ├── requirements.txt     # Python依存関係
│   └── README.md
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoGenerator.js  # メインコンポーネント
│   │   │   ├── ImageUpload.js     # 画像アップロード
│   │   │   ├── TextInput.js       # テキスト入力
│   │   │   ├── VideoPreview.js    # 動画プレビュー
│   │   │   └── ErrorMessage.js    # エラー表示
│   │   ├── services/
│   │   │   └── api.js            # APIクライアント
│   │   ├── styles/
│   │   │   └── main.css          # スタイル
│   │   ├── App.js                # ルートコンポーネント
│   │   └── index.js              # エントリーポイント
│   ├── package.json
│   └── README.md
└── README.md
```

---

## 詳細実装仕様

### バックエンド実装（Python FastAPI）

#### 1. メインサーバー (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from routers import video
from core.config import settings

app = FastAPI(title="Video Message API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(video.router, prefix="/api", tags=["video"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "サーバーエラーが発生しました", "details": str(exc)}
    )

@app.get("/")
async def root():
    return {"message": "Video Message API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2. D-ID API クライアント (services/did_client.py)
```python
import httpx
import asyncio
import base64
from typing import Optional
from core.config import settings

class DIDClient:
    def __init__(self):
        self.base_url = "https://api.d-id.com"
        self.api_key = settings.did_api_key
        
    async def generate_video(self, image_bytes: bytes, text: str) -> str:
        """動画を生成してURLを返す"""
        try:
            # Step 1: 画像をBase64エンコード
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Step 2: 動画生成リクエスト
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/talks",
                    json={
                        "source_url": f"data:image/jpeg;base64,{image_base64}",
                        "script": {
                            "type": "text",
                            "input": text,
                            "provider": {
                                "type": "microsoft",
                                "voice_id": "ja-JP-NanamiNeural"
                            }
                        }
                    },
                    headers={
                        "Authorization": f"Basic {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                talk_id = response.json()["id"]
                
            # Step 3: 生成完了まで待機
            return await self._wait_for_completion(talk_id)
            
        except httpx.HTTPError as e:
            raise Exception(f"D-ID API Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Video generation failed: {str(e)}")
    
    async def _wait_for_completion(self, talk_id: str, max_attempts: int = 30) -> str:
        """生成完了まで待機"""
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/talks/{talk_id}",
                        headers={"Authorization": f"Basic {self.api_key}"},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    status = data.get("status")
                    if status == "done":
                        return data.get("result_url")
                    elif status == "error":
                        raise Exception("Video generation failed")
                    
                    # 2秒待機
                    await asyncio.sleep(2)
                    
            except httpx.HTTPError:
                if attempt == max_attempts - 1:
                    raise Exception("Video generation timeout")
                    
        raise Exception("Video generation timeout")
```

#### 3. データモデル (models/schemas.py)
```python
from pydantic import BaseModel, validator
from typing import Optional

class VideoRequest(BaseModel):
    text: str
    
    @validator('text')
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('テキストは必須です')
        if len(v) > 100:
            raise ValueError('テキストは100文字以内で入力してください')
        return v.strip()

class VideoResponse(BaseModel):
    success: bool
    video_url: Optional[str] = None
    message: str
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
```

#### 4. 設定管理 (core/config.py)
```python
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    did_api_key: str
    cors_origins: list = ["http://localhost:3000"]
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    
    class Config:
        env_file = ".env"

settings = Settings()
```

#### 5. 動画生成ルーター (routers/video.py)
```python
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from services.did_client import DIDClient
from models.schemas import VideoResponse, ErrorResponse
from core.config import settings

router = APIRouter()
did_client = DIDClient()

@router.post("/generate", response_model=VideoResponse)
async def generate_video(
    text: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # バリデーション
        if not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="画像ファイルのみアップロード可能です"
            )
        
        if image.size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail="ファイルサイズは5MB以下にしてください"
            )
        
        if not text or len(text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="テキストは必須です"
            )
        
        if len(text) > 100:
            raise HTTPException(
                status_code=400,
                detail="テキストは100文字以内で入力してください"
            )
        
        # 画像データを読み込み
        image_bytes = await image.read()
        
        # D-ID API で動画生成
        video_url = await did_client.generate_video(image_bytes, text.strip())
        
        return VideoResponse(
            success=True,
            video_url=video_url,
            message="動画生成が完了しました"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"動画生成に失敗しました: {str(e)}"
        )
```

### フロントエンド実装

#### 1. メインコンポーネント (components/VideoGenerator.js)
```jsx
import React, { useState } from 'react';
import ImageUpload from './ImageUpload';
import TextInput from './TextInput';
import VideoPreview from './VideoPreview';
import ErrorMessage from './ErrorMessage';
import { generateVideo } from '../services/api';

const VideoGenerator = () => {
  const [image, setImage] = useState(null);
  const [text, setText] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!image || !text) {
      setError('画像とテキストを入力してください');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await generateVideo(image, text);
      setVideoUrl(result.videoUrl);
    } catch (err) {
      setError(err.message || '動画生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setImage(null);
    setText('');
    setVideoUrl('');
    setError('');
  };

  return (
    <div className="video-generator">
      <h1>動画メッセージ生成（プロトタイプ）</h1>
      
      {error && <ErrorMessage message={error} onClose={() => setError('')} />}
      
      {!videoUrl ? (
        <div className="input-section">
          <ImageUpload onImageSelect={setImage} />
          <TextInput value={text} onChange={setText} />
          <button 
            onClick={handleGenerate} 
            disabled={loading || !image || !text}
            className="generate-button"
          >
            {loading ? '生成中...' : '動画を生成'}
          </button>
        </div>
      ) : (
        <div className="result-section">
          <VideoPreview videoUrl={videoUrl} />
          <button onClick={handleReset} className="reset-button">
            新しく生成
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoGenerator;
```

#### 2. 画像アップロード (components/ImageUpload.js)
```jsx
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const ImageUpload = ({ onImageSelect }) => {
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      onImageSelect(file);
    }
  }, [onImageSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: 5 * 1024 * 1024, // 5MB
    multiple: false
  });

  return (
    <div {...getRootProps()} className="image-upload">
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>ここに画像をドロップしてください</p>
      ) : (
        <p>画像をドラッグ&ドロップ、またはクリックして選択</p>
      )}
    </div>
  );
};

export default ImageUpload;
```

#### 3. APIクライアント (services/api.js)
```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const generateVideo = async (imageFile, text) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('text', text);

  try {
    const response = await axios.post(`${API_BASE_URL}/generate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60秒タイムアウト
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('予期しないエラーが発生しました');
    }
  }
};
```

---

## 開発スケジュール

### 第1週（Day 1-5）

#### Day 1: 環境構築
- [ ] Node.js 18+ インストール確認
- [ ] プロジェクト構造作成
- [ ] package.json設定
- [ ] 必要なパッケージインストール
- [ ] D-ID APIアカウント作成・APIキー取得

**作業時間**: 4時間

#### Day 2: D-ID API動作確認
- [ ] D-ID API基本テスト
- [ ] 認証確認
- [ ] 日本語音声テスト
- [ ] API使用量確認方法の確立

**作業時間**: 4時間

#### Day 3: バックエンド基本実装
- [ ] Express サーバー設定
- [ ] ルート設定
- [ ] ミドルウェア設定
- [ ] 基本的なエラーハンドリング

**作業時間**: 6時間

#### Day 4: D-ID API統合
- [ ] DIDClient クラス実装
- [ ] 動画生成機能実装
- [ ] ポーリング機能実装
- [ ] エラーハンドリング強化

**作業時間**: 8時間

#### Day 5: バックエンドテスト
- [ ] API動作確認
- [ ] エラーケーステスト
- [ ] レスポンス時間測定
- [ ] 問題修正

**作業時間**: 4時間

### 第2週（Day 6-10）

#### Day 6: フロントエンド基本実装
- [ ] React アプリ作成
- [ ] 基本コンポーネント実装
- [ ] CSS基本スタイル
- [ ] コンポーネント間通信

**作業時間**: 6時間

#### Day 7: UI コンポーネント実装
- [ ] 画像アップロード機能
- [ ] テキスト入力機能
- [ ] 動画プレビュー機能
- [ ] エラー表示機能

**作業時間**: 8時間

#### Day 8: フロントエンド・バックエンド統合
- [ ] API通信実装
- [ ] 状態管理実装
- [ ] エラーハンドリング統合
- [ ] ローディング状態表示

**作業時間**: 6時間

#### Day 9: 統合テスト・調整
- [ ] 全機能動作確認
- [ ] UI/UX調整
- [ ] パフォーマンス確認
- [ ] バグ修正

**作業時間**: 8時間

#### Day 10: 完成・検証
- [ ] 最終動作確認
- [ ] パフォーマンス測定
- [ ] 使用量確認
- [ ] 次フェーズ計画見直し
- [ ] ドキュメント作成

**作業時間**: 4時間

**総開発時間**: 58時間

---

## 環境構築手順

### 前提条件
- Node.js 18以上
- npm または yarn
- Git
- VS Code（推奨）

### セットアップ手順

#### 1. プロジェクト作成
```bash
mkdir video-message-app
cd video-message-app
mkdir backend frontend
```

#### 2. バックエンドセットアップ（Python）
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn python-multipart httpx python-dotenv pydantic
pip freeze > requirements.txt
```

#### 3. フロントエンドセットアップ
```bash
cd ../frontend
npx create-react-app . --template minimal
npm install axios react-dropzone react-loader-spinner
```

#### 4. 環境変数設定
```bash
# backend/.env
DID_API_KEY=your-d-id-api-key-here
```

### 開発サーバー起動
```bash
# バックエンド（Python）
cd backend
source venv/bin/activate  # 毎回必要
python main.py
# または: uvicorn main:app --reload --port 8000

# フロントエンド（別ターミナル）
cd frontend
npm start
```

---

## テスト計画

### 機能テスト

#### 1. 画像アップロード機能
- [ ] 正常な画像ファイル（JPG/PNG）のアップロード
- [ ] 不正なファイル形式の拒否
- [ ] ファイルサイズ制限（5MB）の確認
- [ ] ドラッグ&ドロップ機能の確認

#### 2. テキスト入力機能
- [ ] 日本語テキスト入力
- [ ] 文字数制限（100文字）の確認
- [ ] 空文字の拒否
- [ ] 特殊文字の処理

#### 3. 動画生成機能
- [ ] 正常な動画生成
- [ ] 生成時間の測定
- [ ] エラーハンドリング確認
- [ ] 音声品質の確認

#### 4. 動画プレビュー・ダウンロード機能
- [ ] 動画プレビュー表示
- [ ] ダウンロード機能
- [ ] 異なるブラウザでの動作確認

### エラーハンドリングテスト

#### 1. API エラー
- [ ] D-ID API障害時の対応
- [ ] 認証エラーの処理
- [ ] レート制限エラーの処理
- [ ] タイムアウト時の処理

#### 2. ネットワークエラー
- [ ] インターネット接続断時の対応
- [ ] 低速回線での動作確認
- [ ] サーバーダウン時の対応

#### 3. クライアントエラー
- [ ] 不正な入力値の処理
- [ ] ブラウザ互換性の確認
- [ ] JavaScript無効時の対応

### パフォーマンステスト

#### 1. 応答時間
- [ ] 動画生成時間: 30秒以内
- [ ] 画像アップロード: 5秒以内
- [ ] API応答時間: 2秒以内

#### 2. リソース使用量
- [ ] メモリ使用量監視
- [ ] CPU使用率監視
- [ ] ネットワーク使用量監視

---

## 成功指標

### 技術的KPI
- **画像アップロード成功率**: 95%以上
- **動画生成成功率**: 90%以上
- **生成時間**: 30秒以内
- **D-ID API使用料**: 無料枠内（月20分）
- **エラー発生率**: 5%以下

### 品質指標
- **コード品質**: ESLint準拠
- **動作確認**: 主要ブラウザ対応
- **レスポンシブ**: 基本的なモバイル対応
- **アクセシビリティ**: 基本的なキーボード操作対応

### ユーザビリティ指標
- **操作の直感性**: 説明なしで操作可能
- **エラーメッセージ**: 分かりやすい日本語
- **ローディング**: 進捗状況の表示
- **結果**: 満足できる動画品質

---

## リスク管理

### 高リスク

#### 1. D-ID API制限
- **リスク**: 無料枠（月20分）の超過
- **対策**: 使用量の厳密な管理、テスト用サンプルデータの活用
- **モニタリング**: 使用量の日次確認

#### 2. 動画生成失敗
- **リスク**: API障害、生成品質低下
- **対策**: 詳細なエラーログ、リトライ機能
- **モニタリング**: 成功率の監視

#### 3. 開発時間超過
- **リスク**: 機能実装の遅延
- **対策**: 機能の優先度明確化、必要に応じた機能削減
- **モニタリング**: 日次進捗確認

### 中リスク

#### 1. 技術的課題
- **リスク**: D-ID API仕様の理解不足
- **対策**: 事前の十分な調査、公式ドキュメントの精読
- **モニタリング**: 実装進捗の確認

#### 2. 品質問題
- **リスク**: 動画・音声品質の不満
- **対策**: 複数パターンでのテスト実施
- **モニタリング**: 品質の主観的評価

### 低リスク

#### 1. 環境問題
- **リスク**: 開発環境の不具合
- **対策**: 標準的な技術スタックの使用
- **モニタリング**: 開発環境の定期確認

---

## 成果物

### 1. 動作するWebアプリケーション
- React フロントエンド
- Express バックエンド
- D-ID API統合

### 2. 技術検証報告書
- D-ID API性能評価
- 技術的課題の洗い出し
- 次フェーズへの推奨事項

### 3. 開発ドキュメント
- セットアップ手順
- API仕様書
- 既知の問題と対策

### 4. 次フェーズ計画
- 技術的知見を反映した計画修正
- 課題対策の具体化
- 開発効率改善案

---

## 次フェーズへの引き継ぎ

### 技術的知見
- D-ID API の実際の性能・制限
- 動画生成の品質・安定性
- フロントエンド・バックエンドの最適な構成

### 判断基準
- 技術的実現可能性の確認
- ユーザビリティの基本評価
- 開発効率の実績

### 改善点
- 発見された技術的課題
- UI/UX の改善案
- パフォーマンス最適化案

### 次フェーズ推奨事項
- 技術スタックの最終確定
- 開発体制の見直し
- スケジュール調整の必要性

---

## 結論

フェーズ0では、動画メッセージアプリの最小限の機能を実装し、D-ID APIとの統合を通じて技術的実現可能性を検証します。この2週間の成果を基に、次フェーズでのより本格的な開発への道筋を明確にします。

成功の鍵は、機能を必要最小限に絞り込み、品質よりもまず「動作する」ことを優先することです。完璧を求めず、学習と検証に重点を置いた開発を進めていきます。