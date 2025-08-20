# OpenVoice トラブルシューティングガイド
作成日: 2025-08-19

## 🔴 既知の問題と解決策

### 1. エンコーディング問題

#### 症状
```
latin-1 codec can't encode characters in position 0-5: ordinal not in range(256)
```

#### 原因
- システムロケールの不適切な設定
- Pythonのデフォルトエンコーディング
- FastAPIレスポンスのcharset設定

#### 解決策

**システムレベル**:
```bash
# ロケール確認
locale -a | grep -E "(UTF-8|utf8)"

# ロケール生成
sudo locale-gen en_US.UTF-8 ja_JP.UTF-8
sudo update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# 環境変数設定（.bashrc に追加）
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8
```

**Pythonコード**:
```python
# ファイルの先頭に必ず記載
# -*- coding: utf-8 -*-

import os
import sys
import locale

# 環境変数強制設定
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# ロケール設定
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

# ファイル操作時は必ずencoding指定
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# subprocess実行時
import subprocess
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8'
)
```

**FastAPI対応**:
```python
from fastapi import Response
from fastapi.responses import FileResponse

# テキストレスポンス
@app.post("/api/test")
async def test_endpoint(text: str):
    # 処理
    return Response(
        content=result,
        media_type="text/plain; charset=utf-8"
    )

# 音声ファイルレスポンス
@app.post("/api/synthesize")
async def synthesize(text: str):
    # 音声生成処理
    return FileResponse(
        path=audio_file_path,
        media_type="audio/wav",
        headers={"Content-Type": "audio/wav; charset=utf-8"}
    )
```

### 2. CUDA関連エラー

#### 症状
```
CUDA failed with error CUDA driver version is insufficient for CUDA runtime version
```

#### 原因
- CPU環境でCUDA関連の初期化が実行される
- PyTorchがGPUを探そうとする
- Whisperモデルのデフォルト設定

#### 解決策

**環境変数による強制**:
```python
import os
# 必ずimport torchより前に設定
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_HOME'] = ''

import torch
# 強制的にCPUモード
torch.cuda.is_available = lambda: False
torch.cuda.device_count = lambda: 0
```

**Whisperモデルの対処**:
```python
# 方法1: faster-whisperを使用（CPU最適化版）
from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",  # CPU用の軽量化
    num_workers=1,
    download_root="./models"
)

# 方法2: openai-whisperのモンキーパッチ
import whisper

# オリジナルの関数を保存
original_load_model = whisper.load_model

# CPUモード強制のラッパー
def cpu_load_model(name, device=None, download_root=None):
    return original_load_model(
        name,
        device="cpu",  # 強制的にCPU
        download_root=download_root
    )

# 置き換え
whisper.load_model = cpu_load_model
```

### 3. メモリ不足

#### 症状
```
RuntimeError: [Errno 12] Cannot allocate memory
Killed (OOM)
```

#### 原因
- モデルのメモリ使用量が大きい
- 複数のモデルを同時にロード
- メモリリークの蓄積

#### 解決策

**メモリ管理**:
```python
import gc
import torch

class MemoryManagedService:
    def __init__(self):
        self.model = None
        
    def load_model(self):
        # 既存モデルのクリーンアップ
        if self.model:
            del self.model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        # 新規ロード
        self.model = load_model_with_optimization()
    
    def process(self, data):
        try:
            result = self.model.process(data)
        finally:
            # 処理後のクリーンアップ
            gc.collect()
        return result
```

**バッチサイズ調整**:
```python
# メモリ使用量を抑える設定
config = {
    'batch_size': 1,  # 最小値
    'max_length': 512,  # 短めに制限
    'num_workers': 0,  # マルチプロセス無効化
    'pin_memory': False,  # CPUメモリのピン留め無効化
}
```

### 4. 音声ファイル形式エラー

#### 症状
```
Error loading audio file
Sample rate mismatch
Channel count error
```

#### 原因
- サンプルレートの不一致（16kHz vs 22.05kHz vs 48kHz）
- チャンネル数の違い（mono vs stereo）
- ビット深度の問題

#### 解決策

**音声ファイル正規化**:
```python
import librosa
import soundfile as sf
import numpy as np

def normalize_audio(input_path, output_path=None):
    """音声ファイルを16kHz, mono, 16bitに正規化"""
    
    # 読み込み（自動的にfloat32, monoに変換）
    audio, sr = librosa.load(
        input_path,
        sr=16000,  # 16kHzにリサンプリング
        mono=True  # モノラルに変換
    )
    
    # 振幅正規化
    audio = audio / np.max(np.abs(audio))
    
    # クリッピング防止
    audio = np.clip(audio, -0.99, 0.99)
    
    # 保存
    if output_path:
        sf.write(
            output_path,
            audio,
            16000,
            subtype='PCM_16'  # 16bit PCM
        )
    
    return audio, 16000
```

### 5. プロファイルID不整合

#### 症状
```
Profile not found
指定されたプロファイルが見つかりません
```

#### 原因
- Backend と OpenVoice サービス間でIDが不一致
- メタデータファイルの不整合
- ファイルシステムの同期問題

#### 解決策

**ID管理の統一**:
```python
import uuid
from pathlib import Path
import json

class ProfileManager:
    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.metadata_file = self.storage_path / "metadata.json"
        self.profiles = self._load_metadata()
    
    def _load_metadata(self):
        """メタデータの読み込みと修復"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self):
        """メタデータの保存"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.profiles, f, ensure_ascii=False, indent=2)
    
    def create_profile(self, name, audio_path):
        """統一されたID生成"""
        profile_id = f"openvoice_{uuid.uuid4().hex[:8]}"
        
        # ファイル保存
        audio_dest = self.storage_path / f"{profile_id}.wav"
        feature_dest = self.storage_path / f"{profile_id}.npy"
        
        # メタデータ更新
        self.profiles[profile_id] = {
            'id': profile_id,
            'name': name,
            'audio_path': str(audio_dest),
            'feature_path': str(feature_dest),
            'created_at': datetime.now().isoformat()
        }
        
        self._save_metadata()
        return profile_id
    
    def get_profile(self, profile_id):
        """プロファイル取得と検証"""
        if profile_id not in self.profiles:
            # ファイルシステムから探索
            audio_file = self.storage_path / f"{profile_id}.wav"
            if audio_file.exists():
                # メタデータを再構築
                self.profiles[profile_id] = {
                    'id': profile_id,
                    'name': 'Recovered',
                    'audio_path': str(audio_file),
                    'feature_path': str(self.storage_path / f"{profile_id}.npy")
                }
                self._save_metadata()
            else:
                return None
        
        return self.profiles.get(profile_id)
```

## 🔧 デバッグ手法

### ログ出力の強化

```python
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'openvoice_{datetime.now():%Y%m%d}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# デバッグ情報の出力
def debug_audio_info(audio_path):
    import soundfile as sf
    
    info = sf.info(audio_path)
    logger.debug(f"""
    Audio File Info:
    - Path: {audio_path}
    - Duration: {info.duration:.2f}s
    - Sample Rate: {info.samplerate}Hz
    - Channels: {info.channels}
    - Format: {info.format}
    - Subtype: {info.subtype}
    """)
```

### エラートレース

```python
import traceback
import sys

def safe_process(func):
    """エラー詳細を記録するデコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"""
            Function: {func.__name__}
            Args: {args}
            Kwargs: {kwargs}
            Error: {str(e)}
            Traceback:
            {traceback.format_exc()}
            """)
            raise
    return wrapper

@safe_process
def risky_operation(data):
    # 危険な処理
    pass
```

## 📊 パフォーマンスチューニング

### CPU最適化

```python
# NumPy/SciPy の最適化
import os
os.environ['OMP_NUM_THREADS'] = '2'  # CPUコア数に合わせる
os.environ['MKL_NUM_THREADS'] = '2'

# PyTorch の最適化
import torch
torch.set_num_threads(2)
torch.set_num_interop_threads(1)

# メモリアロケータの最適化
import gc
gc.set_threshold(700, 10, 10)
```

### プロファイリング

```python
import cProfile
import pstats
from io import StringIO

def profile_function(func):
    """関数のプロファイリング"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func()
    
    profiler.disable()
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    
    logger.info(f"Profile results:\n{s.getvalue()}")
    return result
```

## 🚨 緊急対処法

### サービス復旧手順

```bash
#!/bin/bash
# emergency_recovery.sh

# 1. プロセス停止
pkill -f openvoice
pkill -f uvicorn

# 2. キャッシュクリア
rm -rf /tmp/openvoice_*
rm -rf ~/.cache/whisper
rm -rf ~/.cache/torch

# 3. ログローテーション
mv openvoice.log openvoice.log.$(date +%Y%m%d_%H%M%S)

# 4. サービス再起動
cd ~/video-message-app
source openvoice_env/bin/activate
nohup python3 openvoice_service.py > openvoice.log 2>&1 &

# 5. ヘルスチェック
sleep 5
curl http://localhost:8001/health
```

---

作成者: Trinitas-Core System
更新日: 2025-08-19