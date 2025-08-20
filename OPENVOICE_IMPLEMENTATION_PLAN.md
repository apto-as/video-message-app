# OpenVoice完全実装計画書
作成日: 2025-08-19
作成者: Trinitas-Core

## 🎯 目的
EC2環境でOpenVoice V2の完全なクローニング機能を実装する。フォールバック実装を排除し、Mac環境で成功していた実装を完全再現する。

## 🔴 現在の問題点

### 1. 致命的な問題
- **エンコーディングエラー**: 日本語テキスト処理で`latin-1 codec can't encode`エラー
- **フォールバック実装**: 実際の音声クローニングが動作していない（元音声をそのまま返すだけ）
- **環境汚染の可能性**: 複数のPythonバージョン、パッケージの競合

### 2. 技術的課題
- Whisperモデルの初期化問題
- CUDAエラー（CPU環境での不適切な設定）
- se_extractorの正常動作未確認
- ToneColorConverterの実装不完全

## 📋 実装計画

### Option A: 既存EC2インスタンスでの修正【推奨 - uv使用】

#### Phase 0: uv環境構築 (Day 1 - 最優先)
```bash
# uvのインストール（Rust製の高速Pythonパッケージマネージャー）
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# uvでPython 3.11環境を作成
cd ~/video-message-app/video-message-app
uv venv --python 3.11
source .venv/bin/activate

# 基本パッケージのインストール（uvは自動的に依存関係を解決）
uv pip install --upgrade pip setuptools wheel
```

#### Phase 1: クリーンアップ (Day 1 - AM)
```bash
# 不要ファイルの整理
mkdir -p ~/video-message-app/video-message-app/backup/$(date +%Y%m%d)
mv ~/video-message-app/video-message-app/openvoice_ec2/*.py ~/video-message-app/video-message-app/backup/$(date +%Y%m%d)/
mv ~/video-message-app/video-message-app/openvoice_ec2/old_* ~/video-message-app/video-message-app/backup/$(date +%Y%m%d)/
mv /tmp/test_*.py ~/video-message-app/video-message-app/backup/$(date +%Y%m%d)/

# 古いPython環境のクリーンアップ
rm -rf ~/video-message-app/video-message-app/openvoice_env
rm -rf ~/.cache/pip
```

#### Phase 2: Mac実装の分析 (Day 1 - PM)
**調査対象ファイル**:
- `openvoice_native/main.py` - 動作していたFastAPIサービス
- `openvoice_native/simple_openvoice.py` - 音声処理ロジック
- `setup_new_env.sh` - Conda環境設定
- `openvoice_native/requirements.txt` - 依存関係

**確認ポイント**:
1. Whisperモデルの初期化方法
2. エンコーディング設定
3. 音声特徴抽出の実装
4. ToneColorConverterの使用方法

#### Phase 2.5: uv環境でのOpenVoice構築 (Day 1 - PM)
```bash
# uv環境内でOpenVoiceをインストール
cd ~/video-message-app/video-message-app
source .venv/bin/activate

# PyTorch CPU版のインストール（uvで高速）
uv pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

# OpenVoiceのクローンとインストール
cd ~/video-message-app
git clone https://github.com/myshell-ai/OpenVoice
cd OpenVoice
uv pip install -e .

# 必要な依存関係をuvでインストール
uv pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    numpy==1.24.4 \
    scipy \
    librosa \
    soundfile \
    openai-whisper \
    httpx \
    aiofiles \
    python-dotenv \
    pydantic==2.5.0

# 環境の確認
uv pip list | grep -E "(torch|openvoice|whisper)"
```

#### Phase 3: エンコーディング問題の解決 (Day 2)
```python
# 必須設定
# -*- coding: utf-8 -*-
import os
import sys
import locale

# 環境変数設定（uv環境内で実行）
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# FastAPIレスポンス設定
from fastapi import Response
response = Response(content=audio_data, media_type="audio/wav")
response.charset = "utf-8"
```

#### Phase 4: 音声特徴抽出の完全実装 (Day 3)
```python
# se_extractorの正しい実装
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

class OpenVoiceProcessor:
    def __init__(self):
        self.device = "cpu"
        self.tone_color_converter = self._init_converter()
        
    def _init_converter(self):
        config_path = "checkpoints_v2/converter/config.json"
        checkpoint_path = "checkpoints_v2/converter/checkpoint.pth"
        converter = ToneColorConverter(config_path, device=self.device)
        converter.load_ckpt(checkpoint_path)
        return converter
    
    def extract_voice_features(self, audio_path):
        """実際の音声特徴抽出"""
        # Whisperベースの特徴抽出
        target_se, audio_name = se_extractor.get_se(
            audio_path,
            self.tone_color_converter,
            vad=False,  # Voice Activity Detectionを無効化（CPU負荷軽減）
            device=self.device
        )
        return target_se, audio_name
```

#### Phase 5: ToneColorConverter実装 (Day 4)
```python
def synthesize_with_clone(self, text, profile_id, language="ja"):
    """実際のクローン音声合成"""
    # 1. テキストを基本音声で合成
    base_audio_path = self._synthesize_base_voice(text, language)
    
    # 2. プロファイルの音声特徴を読み込み
    target_se = np.load(f"storage/openvoice/{profile_id}.npy")
    
    # 3. 基本音声の特徴を抽出
    source_se, _ = self.extract_voice_features(base_audio_path)
    
    # 4. 音声変換を実行
    output_path = f"/tmp/{profile_id}_output.wav"
    self.tone_color_converter.convert(
        audio_src_path=base_audio_path,
        src_se=source_se,
        tgt_se=target_se,
        output_path=output_path,
        message="@MyShell"
    )
    
    return output_path
```

#### Phase 6: 統合テスト (Day 5)
- 日本語テキストでの完全なE2Eテスト
- プロファイル作成 → 音声合成 → 検証
- Backend APIとの統合確認

### Option B: 新規EC2インスタンスでのクリーン実装

#### 利点
- 環境汚染なし
- uvによる完全な環境分離
- 依存関係の競合なし
- 設定ミスのリセット

#### 新規インスタンス仕様
```yaml
Instance Type: t3.large
AMI: Ubuntu 22.04 LTS
Storage: 30GB (gp3)
Python: 3.11.x (pyenvで管理)
Region: ap-northeast-1
```

#### セットアップスクリプト（uv使用）
```bash
#!/bin/bash
# setup_fresh_ec2_with_uv.sh

# System update
sudo apt-get update && sudo apt-get upgrade -y

# 必要なシステムパッケージ
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    ffmpeg \
    git \
    curl \
    locales

# ロケール設定（日本語対応）
sudo locale-gen en_US.UTF-8 ja_JP.UTF-8
sudo update-locale LANG=en_US.UTF-8

# uvのインストール（Pythonバージョン管理も含む）
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# プロジェクトディレクトリ作成
mkdir -p ~/video-message-app/video-message-app
cd ~/video-message-app/video-message-app

# uvでPython 3.11環境を作成
uv venv --python 3.11
source .venv/bin/activate

# OpenVoice環境構築（uv環境内）
cd ~/video-message-app
git clone https://github.com/myshell-ai/OpenVoice
cd OpenVoice
uv pip install -e .

# 依存関係をuvでインストール
uv pip install \
    torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    numpy==1.24.4 \
    scipy \
    librosa \
    soundfile \
    openai-whisper

# モデルダウンロード
mkdir -p ~/video-message-app/checkpoints_v2
# HuggingFaceからモデルファイルをダウンロード

# サービス起動（uv環境内）
cd ~/video-message-app/video-message-app
source .venv/bin/activate
python openvoice_service.py
```

## 🔍 問題解決アプローチ

### エンコーディング問題
1. **システムロケール確認**
   ```bash
   locale -a
   # ja_JP.UTF-8が存在することを確認
   ```

2. **Python環境変数**
   ```python
   import os
   os.environ['PYTHONIOENCODING'] = 'utf-8'
   ```

3. **ファイル読み書き時**
   ```python
   with open(filepath, 'r', encoding='utf-8') as f:
       content = f.read()
   ```

### Whisperモデル問題
1. **OpenAI Whisperの代替**
   ```python
   # faster-whisperを使用（CPU最適化版）
   from faster_whisper import WhisperModel
   model = WhisperModel("base", device="cpu", compute_type="int8")
   ```

2. **モンキーパッチ適用**
   ```python
   # CUDAを強制的に無効化
   import whisper
   whisper.available_models = lambda: ["base", "small"]
   whisper.load_model = lambda name, device="cpu": load_cpu_model(name)
   ```

## 📊 成功指標

### 必須要件
- [ ] 日本語テキストが正常に処理される
- [ ] 実際の音声クローニングが動作する
- [ ] プロファイル作成から音声合成まで完全動作
- [ ] Backend APIとの統合が正常

### パフォーマンス指標
- [ ] プロファイル作成: 30秒以内
- [ ] 音声合成: 10秒以内（10秒のテキスト）
- [ ] メモリ使用量: 4GB以下

## 🚀 実装スケジュール

### Week 1 (8/20-8/24)
- **Day 1 (8/20)**: 環境判断（既存修正 or 新規構築）
- **Day 2 (8/21)**: 環境準備とクリーンアップ
- **Day 3 (8/22)**: エンコーディング問題解決
- **Day 4 (8/23)**: 音声特徴抽出実装
- **Day 5 (8/24)**: ToneColorConverter実装

### Week 2 (8/26-8/27)
- **Day 6 (8/26)**: 統合テスト
- **Day 7 (8/27)**: 本番デプロイ

## 📝 チェックリスト

### 事前準備
- [ ] Mac環境の動作コード確認
- [ ] 必要なモデルファイルの確認
- [ ] AWSクレジットの確認（新規インスタンスの場合）

### 実装時
- [ ] エンコーディング設定の統一
- [ ] ログ出力の充実化
- [ ] エラーハンドリングの強化
- [ ] テストケースの作成

### 完了確認
- [ ] 日本語音声合成の成功
- [ ] クローン音声の品質確認
- [ ] システム負荷テスト
- [ ] ドキュメント更新

## 🔧 トラブルシューティング

### よくある問題と対策

#### 1. CUDA関連エラー
```python
# 強制的にCPUモード
os.environ['CUDA_VISIBLE_DEVICES'] = ''
torch.cuda.is_available = lambda: False
```

#### 2. メモリ不足
```python
# バッチサイズ調整
batch_size = 1  # 最小値に設定
# ガベージコレクション
import gc
gc.collect()
```

#### 3. 音声ファイル形式
```python
# 必ず16kHz, mono, 16bitに変換
import librosa
audio, sr = librosa.load(audio_path, sr=16000, mono=True)
```

## 🎯 最終目標

**完全に動作するOpenVoice V2クローニングシステム**
- フォールバックなし
- 日本語完全対応
- 実用的な処理速度
- 安定した動作

---

## 連絡先
- プロジェクト: Video Message App
- 環境: AWS EC2 (ap-northeast-1)
- 作成者: Trinitas-Core System

## 更新履歴
- 2025-08-19: 初版作成
- 予定: 実装結果に基づく更新