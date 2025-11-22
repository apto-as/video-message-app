# Real-time Progress Tracking System

完全パイプライン (YOLO → BiRefNet → Prosody → D-ID) のリアルタイム進捗追跡システム。

## 概要

このシステムは、ビデオ生成パイプラインの進捗をリアルタイムで追跡し、WebSocketまたはSSE（Server-Sent Events）を通じてクライアントに通知します。

### 主な機能

- **リアルタイム進捗通知**: <2秒のレイテンシ
- **複数接続サポート**: 最大100同時接続
- **自動フォールバック**: WebSocket → SSE → HTTP Polling
- **段階的進捗**: 5段階の進捗表示（0% → 20% → 40% → 60% → 80% → 100%）
- **自動クリーンアップ**: 1時間後に古いデータを自動削除

## パイプライン段階

| Stage | Progress | Description |
|-------|----------|-------------|
| `initialized` | 0% | パイプライン初期化 |
| `yolo_detection` | 0-20% | YOLO人物検出 |
| `birefnet_removal` | 20-40% | BiRefNet背景除去 |
| `prosody_adjustment` | 40-60% | Prosody調整（オプション） |
| `d_id_upload` | 60-70% | D-IDへのアップロード |
| `d_id_processing` | 70-80% | D-ID動画生成 |
| `finalizing` | 80-90% | 最終処理 |
| `complete` | 100% | 完了 |
| `failed` | -1 | エラー |

---

## API エンドポイント

### 1. ビデオ生成開始

**POST** `/api/video-generation/generate`

完全パイプラインを実行し、進捗追跡用のタスクIDを返します。

**Request (multipart/form-data)**:
```http
POST /api/video-generation/generate
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="image"; filename="photo.jpg"
Content-Type: image/jpeg

[image binary data]
--boundary
Content-Disposition: form-data; name="audio"; filename="voice.wav"
Content-Type: audio/wav

[audio binary data]
--boundary
Content-Disposition: form-data; name="conf_threshold"

0.5
--boundary
Content-Disposition: form-data; name="apply_smoothing"

true
--boundary--
```

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Pipeline started, use provided URLs to track progress",
  "websocket_url": "ws://localhost:55433/api/ws/progress/550e8400-e29b-41d4-a716-446655440000",
  "sse_url": "http://localhost:55433/api/sse/progress/550e8400-e29b-41d4-a716-446655440000",
  "polling_url": "http://localhost:55433/api/ws/progress/550e8400-e29b-41d4-a716-446655440000/latest"
}
```

### 2. WebSocket進捗追跡

**WebSocket** `ws://host:port/api/ws/progress/{task_id}`

リアルタイム進捗更新を受信します（推奨）。

**メッセージ形式**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "stage_update",
  "data": {
    "stage": "yolo_detection",
    "progress": 20,
    "message": "Detected 2 person(s), selected person 0",
    "metadata": {
      "detected_persons": 2,
      "selected_person": {
        "person_id": 0,
        "confidence": 0.95
      }
    }
  },
  "timestamp": "2025-11-07T12:34:56.789Z"
}
```

**イベントタイプ**:
- `stage_update`: 段階変更
- `progress_update`: 進捗更新
- `error`: エラー発生
- `complete`: 完了
- `heartbeat`: 接続確認（30秒ごと）

### 3. SSE進捗追跡（フォールバック）

**GET** `/api/sse/progress/{task_id}`

Server-Sent Eventsで進捗を受信します。WebSocketが使用できない場合のフォールバック。

```javascript
const eventSource = new EventSource('/api/sse/progress/550e8400-e29b-41d4-a716-446655440000');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

### 4. HTTP Polling（最終フォールバック）

**GET** `/api/ws/progress/{task_id}/latest`

最新の進捗イベントを取得します。WebSocketとSSEが使用できない場合の最終手段。

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "stage_update",
    "data": {
      "stage": "birefnet_removal",
      "progress": 40,
      "message": "Background removed successfully"
    },
    "timestamp": "2025-11-07T12:35:12.456Z"
  }
}
```

### 5. 履歴取得

**GET** `/api/ws/progress/{task_id}/history`

タスクの全進捗履歴を取得します。

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_count": 12,
  "events": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "stage_update",
      "data": {
        "stage": "initialized",
        "progress": 0,
        "message": "Pipeline initialized"
      },
      "timestamp": "2025-11-07T12:34:50.123Z"
    },
    ...
  ]
}
```

---

## クライアント統合

### React Hook（推奨）

`useProgressTracking` Hookを使用して簡単に統合できます。

```tsx
import { useProgressTracking } from './hooks/useProgressTracking';

function VideoGenerationProgress({ taskId }: { taskId: string }) {
  const { progress, isConnected, error, connectionType } = useProgressTracking(taskId, {
    preferWebSocket: true,
    onComplete: (data) => {
      console.log('Video URL:', data.video_url);
      // 完了処理
    },
    onError: (error) => {
      console.error('Generation failed:', error);
      // エラー処理
    }
  });

  return (
    <div>
      <h2>Video Generation Progress</h2>

      {/* 接続状態 */}
      <div>
        Connection: {isConnected ? `Connected (${connectionType})` : 'Disconnected'}
      </div>

      {/* プログレスバー */}
      <div style={{ width: '100%', height: '20px', background: '#eee' }}>
        <div
          style={{
            width: `${progress.progress}%`,
            height: '100%',
            background: 'green',
            transition: 'width 0.3s'
          }}
        />
      </div>

      {/* 詳細情報 */}
      <p>Stage: {progress.stage}</p>
      <p>Progress: {progress.progress}%</p>
      <p>Message: {progress.message}</p>

      {/* エラー表示 */}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
    </div>
  );
}
```

### WebSocket クライアント（JavaScript）

```javascript
const taskId = '550e8400-e29b-41d4-a716-446655440000';
const ws = new WebSocket(`ws://localhost:55433/api/ws/progress/${taskId}`);

ws.onopen = () => {
  console.log('Connected to progress tracker');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // プログレスバー更新
  updateProgressBar(data.data.progress);

  // メッセージ表示
  updateStatusMessage(data.data.message);

  // 完了処理
  if (data.event_type === 'complete') {
    console.log('Video URL:', data.data.video_url);
    ws.close();
  }

  // エラー処理
  if (data.event_type === 'error') {
    console.error('Error:', data.data.error);
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed');
};
```

### SSE クライアント（JavaScript）

```javascript
const taskId = '550e8400-e29b-41d4-a716-446655440000';
const eventSource = new EventSource(`http://localhost:55433/api/sse/progress/${taskId}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  console.log('Progress:', data.data.progress, '%');
  console.log('Stage:', data.data.stage);
  console.log('Message:', data.data.message);

  if (data.event_type === 'complete') {
    console.log('Video URL:', data.data.video_url);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

### cURL（テスト用）

```bash
# ビデオ生成開始
TASK_ID=$(curl -X POST http://localhost:55433/api/video-generation/generate \
  -F "image=@photo.jpg" \
  -F "audio=@voice.wav" \
  -F "conf_threshold=0.5" \
  -F "apply_smoothing=true" | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# SSEで進捗追跡
curl -N http://localhost:55433/api/sse/progress/$TASK_ID

# または HTTP Pollingで進捗確認（1秒ごと）
while true; do
  curl -s http://localhost:55433/api/ws/progress/$TASK_ID/latest | jq
  sleep 1
done
```

---

## パフォーマンス

### ベンチマーク結果

| メトリクス | 目標値 | 実測値 | 状態 |
|-----------|--------|--------|------|
| イベントスループット | >1000 events/sec | ~15000 events/sec | ✓ |
| 平均配信レイテンシ | <2000ms | ~5ms | ✓ |
| P95配信レイテンシ | <5000ms | ~15ms | ✓ |
| 同時接続数 | 100 | 100 | ✓ |
| メモリ使用量 | <256MB | ~80MB | ✓ |

### ベンチマーク実行

```bash
cd backend
python -m pytest tests/benchmark_progress_tracker.py -v -s
```

---

## トラブルシューティング

### WebSocket接続失敗

**症状**: `WebSocket connection error`

**原因**:
1. サーバーが起動していない
2. ファイアウォールがWebSocketをブロック
3. プロキシがアップグレードを許可していない

**解決策**:
```javascript
// SSEにフォールバック
const { progress } = useProgressTracking(taskId, {
  preferWebSocket: false  // SSEを優先
});
```

### 進捗が更新されない

**症状**: プログレスバーが0%のまま

**原因**:
1. タスクIDが無効
2. パイプライン実行が開始されていない
3. バックグラウンドタスクが失敗

**解決策**:
```bash
# タスクの履歴を確認
curl http://localhost:55433/api/ws/progress/$TASK_ID/history | jq

# バックエンドログを確認
docker logs voice_backend --tail 100
```

### 接続が頻繁に切断される

**症状**: 30秒ごとに切断される

**原因**: プロキシやロードバランサーのタイムアウト

**解決策**:
```nginx
# Nginx設定例
location /api/ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;  # 1時間
    proxy_send_timeout 3600s;
}

location /api/sse/ {
    proxy_pass http://backend;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}
```

---

## セキュリティ考慮事項

### 認証

タスクIDは推測不可能なUUIDv4を使用していますが、本番環境では追加の認証が推奨されます。

```python
# 例: JWTトークンでタスクアクセスを制限
@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(...)
):
    # トークン検証
    user = verify_jwt_token(token)
    if not user.has_access_to_task(task_id):
        await websocket.close(code=1008)  # Policy Violation
        return

    await websocket.accept()
    # ...
```

### レート制限

DOS攻撃を防ぐため、接続数を制限します。

```python
# services/rate_limiter.py
class ConnectionRateLimiter:
    def __init__(self, max_connections_per_ip: int = 10):
        self.max_connections = max_connections_per_ip
        self.connections: Dict[str, int] = {}

    def can_connect(self, ip: str) -> bool:
        return self.connections.get(ip, 0) < self.max_connections
```

---

## デプロイ

### Docker Compose

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "55433:55433"
    environment:
      - BASE_URL=http://localhost:55433
      - STORAGE_DIR=/app/storage
    volumes:
      - ./data/backend/storage:/app/storage
```

### 環境変数

```bash
# .env
BASE_URL=http://localhost:55433
STORAGE_DIR=/app/storage
```

---

## まとめ

リアルタイム進捗追跡システムの統合により、ユーザーはビデオ生成の進行状況をリアルタイムで確認でき、完了まで待つことができます。

**主な利点**:
- ユーザー体験の向上（進捗の可視化）
- エラーの早期検出
- システムの透明性向上
- 複数クライアントのサポート

**次のステップ**:
1. React Hookを使用してフロントエンドに統合
2. プログレスバーとステージ表示を実装
3. エラーハンドリングとリトライ機能を追加
4. 本番環境での認証・認可を実装
