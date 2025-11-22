# フロントエンド進捗バー実装計画

## 概要

音声クローニング処理（約4分）の進捗を可視化し、ユーザーに処理状況をリアルタイムで伝える。

## 技術アプローチ

### Option A: WebSocket（推奨）

**メリット**:
- リアルタイム通信
- サーバープッシュ型
- 正確な進捗情報

**実装概要**:
```python
# Backend: WebSocket endpoint
from fastapi import WebSocket
import asyncio

@app.websocket("/ws/voice-clone/{task_id}")
async def voice_clone_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()

    # 進捗を送信
    await websocket.send_json({
        "status": "processing",
        "step": "whisper_extraction",
        "progress": 30,
        "message": "音声特徴を抽出中..."
    })

    # 処理完了
    await websocket.send_json({
        "status": "completed",
        "progress": 100,
        "result_url": "/api/voice-clone/profiles/openvoice_xxx"
    })
```

```javascript
// Frontend: WebSocket client
const ws = new WebSocket('ws://localhost:55433/ws/voice-clone/' + taskId);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProgressBar(data.progress, data.message);
};
```

### Option B: Server-Sent Events (SSE)

**メリット**:
- シンプルな実装
- HTTP/2対応
- 自動再接続

**実装概要**:
```python
# Backend: SSE endpoint
from fastapi import Response
from sse_starlette.sse import EventSourceResponse

@app.get("/api/voice-clone/progress/{task_id}")
async def voice_clone_progress_stream(task_id: str):
    async def event_generator():
        for progress in range(0, 101, 10):
            await asyncio.sleep(1)
            yield {
                "event": "progress",
                "data": json.dumps({
                    "progress": progress,
                    "message": f"処理中... {progress}%"
                })
            }

    return EventSourceResponse(event_generator())
```

### Option C: ポーリング（最もシンプル）

**メリット**:
- 実装が容易
- 既存のREST APIを活用

**実装概要**:
```javascript
// Frontend: Polling
const pollProgress = async (taskId) => {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/voice-clone/status/${taskId}`);
    const data = await response.json();

    updateProgressBar(data.progress, data.message);

    if (data.status === 'completed' || data.status === 'failed') {
      clearInterval(interval);
    }
  }, 2000);  // 2秒ごとにポーリング
};
```

## 推奨実装: Option A (WebSocket)

### Phase 2.1.1: Backend実装

1. **タスクキューの実装**:
```python
# backend/services/task_queue.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class VoiceCloneTask:
    task_id: str
    status: TaskStatus
    progress: int  # 0-100
    current_step: str
    message: str
    error: Optional[str] = None

# グローバルタスクストア（実運用ではRedis等を使用）
tasks: dict[str, VoiceCloneTask] = {}
```

2. **WebSocketエンドポイント**:
```python
# backend/routers/voice_clone_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

@router.websocket("/ws/voice-clone/{task_id}")
async def voice_clone_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()

    try:
        while True:
            # タスク状態を取得
            task = tasks.get(task_id)
            if not task:
                await websocket.send_json({"error": "Task not found"})
                break

            # 進捗を送信
            await websocket.send_json({
                "task_id": task_id,
                "status": task.status,
                "progress": task.progress,
                "step": task.current_step,
                "message": task.message
            })

            # 完了または失敗で終了
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

            await asyncio.sleep(0.5)  # 500msごとに更新

    except WebSocketDisconnect:
        pass
```

3. **音声クローニング処理の更新**:
```python
# backend/routers/voice_clone.py
async def create_voice_clone_with_progress(
    audio_file: UploadFile,
    profile_name: str,
    task_id: str
):
    # タスク初期化
    tasks[task_id] = VoiceCloneTask(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0,
        current_step="init",
        message="処理を開始しています..."
    )

    try:
        # Step 1: ファイル保存
        tasks[task_id].progress = 10
        tasks[task_id].message = "音声ファイルを保存中..."
        await save_audio_file(audio_file)

        # Step 2: Whisper処理
        tasks[task_id].progress = 30
        tasks[task_id].current_step = "whisper"
        tasks[task_id].message = "音声特徴を抽出中（最大2分）..."
        await whisper_process(audio_file)

        # Step 3: OpenVoice埋め込み生成
        tasks[task_id].progress = 70
        tasks[task_id].current_step = "embedding"
        tasks[task_id].message = "音声モデルを生成中..."
        await create_embedding(audio_file)

        # Step 4: 完了
        tasks[task_id].status = TaskStatus.COMPLETED
        tasks[task_id].progress = 100
        tasks[task_id].message = "処理が完了しました！"

    except Exception as e:
        tasks[task_id].status = TaskStatus.FAILED
        tasks[task_id].error = str(e)
        raise
```

### Phase 2.1.2: Frontend実装

1. **React Hook for WebSocket**:
```javascript
// frontend/src/hooks/useVoiceCloneProgress.js
import { useState, useEffect, useRef } from 'react';

export const useVoiceCloneProgress = (taskId) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('pending');
  const [message, setMessage] = useState('');
  const wsRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(`ws://localhost:55433/ws/voice-clone/${taskId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.progress);
      setStatus(data.status);
      setMessage(data.message);
    };

    ws.onerror = () => {
      setStatus('error');
      setMessage('接続エラーが発生しました');
    };

    return () => {
      ws.close();
    };
  }, [taskId]);

  return { progress, status, message };
};
```

2. **Progress Bar Component**:
```javascript
// frontend/src/components/VoiceCloneProgress.jsx
import React from 'react';
import { useVoiceCloneProgress } from '../hooks/useVoiceCloneProgress';

export const VoiceCloneProgress = ({ taskId }) => {
  const { progress, status, message } = useVoiceCloneProgress(taskId);

  const getProgressColor = () => {
    if (status === 'failed') return 'bg-red-500';
    if (status === 'completed') return 'bg-green-500';
    return 'bg-blue-500';
  };

  return (
    <div className="w-full max-w-md mx-auto p-4">
      <div className="mb-2 flex justify-between items-center">
        <span className="text-sm font-medium">{message}</span>
        <span className="text-sm text-gray-600">{progress}%</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div
          className={`h-full ${getProgressColor()} transition-all duration-300 ease-out`}
          style={{ width: `${progress}%` }}
        >
          {/* アニメーション効果 */}
          <div className="h-full w-full bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer" />
        </div>
      </div>

      {status === 'processing' && (
        <div className="mt-2 text-xs text-gray-500">
          処理には約4分かかります。このページを閉じずにお待ちください。
        </div>
      )}
    </div>
  );
};
```

3. **CSS Animations**:
```css
/* frontend/src/styles/progress.css */
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-shimmer {
  animation: shimmer 2s infinite;
}
```

## 実装スケジュール

| Phase | タスク | 担当 | 工数 | 期限 |
|-------|-------|------|------|------|
| 2.1.1 | Backend WebSocket実装 | Artemis | 4h | Day 1-2 |
| 2.1.2 | Frontend Hook/Component | Athena | 3h | Day 2-3 |
| 2.1.3 | 統合テスト | Hestia | 2h | Day 3 |
| 2.1.4 | デプロイ（EC2） | Eris | 1h | Day 4 |

**総工数**: 10時間（2-3日）

## テスト計画

### Unit Tests

```python
# tests/test_voice_clone_ws.py
import pytest
from fastapi.testclient import TestClient

def test_websocket_progress():
    with client.websocket_connect("/ws/voice-clone/test_task") as ws:
        data = ws.receive_json()
        assert data["status"] in ["pending", "processing"]
        assert 0 <= data["progress"] <= 100
```

### Integration Tests

```javascript
// frontend/src/__tests__/VoiceCloneProgress.test.js
import { render, screen, waitFor } from '@testing-library/react';
import { VoiceCloneProgress } from '../components/VoiceCloneProgress';

test('displays progress updates', async () => {
  render(<VoiceCloneProgress taskId="test_task" />);

  await waitFor(() => {
    expect(screen.getByText(/処理中/)).toBeInTheDocument();
  });
});
```

## リスク評価

| リスク | 影響 | 対策 |
|-------|------|------|
| WebSocket接続失敗 | 進捗表示不可 | ポーリングへのフォールバック |
| タスクID衝突 | 進捗混乱 | UUID v4使用 |
| メモリリーク（タスクストア） | サーバーメモリ枯渇 | TTL付きタスク削除（24時間） |
| ネットワーク遅延 | 進捗表示のラグ | 500ms更新間隔で許容範囲 |

## 代替案（Option C: ポーリング）

WebSocket実装が困難な場合のシンプルな代替案:

```python
# Backend
@app.get("/api/voice-clone/status/{task_id}")
async def get_task_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task
```

```javascript
// Frontend
const pollStatus = async (taskId) => {
  const interval = setInterval(async () => {
    const res = await fetch(`/api/voice-clone/status/${taskId}`);
    const data = await res.json();
    updateProgress(data);

    if (data.status === 'completed') clearInterval(interval);
  }, 2000);
};
```

**ポーリング方式の工数**: 6時間（1-2日）

## 成功基準

- ✅ 進捗バーが0%から100%まで滑らかに更新される
- ✅ 各処理ステップが明確に表示される
- ✅ 処理時間の目安が表示される（約4分）
- ✅ エラー時に適切なメッセージが表示される
- ✅ ページを離れても処理が継続される
- ✅ ユーザーからの「停滞」報告が0件になる
