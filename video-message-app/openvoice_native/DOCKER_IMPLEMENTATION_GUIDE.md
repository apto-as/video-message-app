# OpenVoice Native Service Docker実装ガイド

**作成日**: 2025-11-03
**対象**: OpenVoice V2 Docker化 (Mac M3 + EC2 CUDA対応)

---

## 概要

OpenVoice Native ServiceをDockerコンテナ化し、Mac (CPU/MPS) とEC2 (CUDA) の両環境で動作させる実装ガイド。

### 達成目標
- ✅ Mac M3 (ARM64/CPU) でのDocker動作
- ✅ EC2 (x86_64/CUDA 11.8) でのDocker動作
- ✅ NVIDIA Container Runtime によるGPU利用
- ✅ 環境変数による柔軟なパス設定
- ✅ すべての依存関係の互換性確保

---

## 重要な発見事項

### 1. パッケージバージョン互換性の問題

#### 問題: PyAV/Cython 3.x 非互換エラー

**症状**:
```
ERROR: Could not build wheels for av, which is required to install pyproject.toml-based projects
Cython.Compiler.Errors.CompileError: /tmp/pip-install-xxx/av_xxx/av/buffer.c
```

**根本原因**:
- **faster-whisper 0.9.0** が PyAV 8.x を要求
- PyAV 8.x は Cython 3.x と非互換
- Python 3.11.12 環境ではCython 3.x がインストールされる

**解決策**:
```txt
# requirements.txt
faster-whisper>=1.2.1  # PyAV 11.0+ 依存（Cython 3.x 互換）
ctranslate2>=4.0,<5     # faster-whisper 1.2.1+ の依存要件
```

**教訓**:
- **faster-whisper 1.2.1+** は PyAV 11.0+ に依存
- PyAV 11.0+ は Cython 3.x 互換の ARM64 binary wheels を提供
- ctranslate2 4.0+ が必須（3.x は非互換）

---

### 2. Dockerコンテナ内パス解決問題

#### 問題: 相対パス計算の環境依存性

**症状**:
```
不足モデルファイル: ['/data/openvoice/checkpoints_v2/converter/checkpoint.pth', ...]
必要なモデルファイルが見つかりません
```

**根本原因**:
```python
# config.py (修正前)
base_dir: Path = Path(__file__).parent.parent
# Docker内: /app/config.py → parent.parent = / (ルート)
# Native: /path/to/project/config.py → parent.parent = /path/to/project/
```

**解決策**:
```python
# config.py (修正後)
base_dir: Path = Path(os.getenv("OPENVOICE_BASE_DIR", Path(__file__).parent.parent))
```

```dockerfile
# Dockerfile
ENV OPENVOICE_BASE_DIR=/app
```

```yaml
# docker-compose.yml
environment:
  - OPENVOICE_BASE_DIR=/app
```

**教訓**:
- Docker環境では `Path(__file__).parent.parent` の動作が異なる
- 環境変数による設定上書きで柔軟性を確保
- Native環境との互換性を維持

---

### 3. 欠落した依存関係

#### 問題: wavmark パッケージ未指定

**症状**:
```
モデル初期化エラー: No module named 'wavmark'
```

**原因**:
- OpenVoice V2 の透かし機能に wavmark を使用
- requirements.txt に記載なし
- EC2 venv には手動インストール済み（pip freeze で確認）

**解決策**:
```txt
# requirements.txt
wavmark==0.0.3
```

**教訓**:
- プロジェクト依存関係は明示的に requirements.txt に記載
- EC2/venv で動作していても、Dockerでは明示的インストールが必要

---

### 4. CUDA対応設定

#### 問題: PyTorch が CUDA を認識しない

**症状**:
```
CUDA available: False
CUDA device count: 0
```

**原因**:
- docker-compose.yml に NVIDIA runtime 設定なし
- GPU可視性の環境変数なし

**解決策**:
```yaml
# docker-compose.yml
services:
  openvoice:
    runtime: nvidia  # NVIDIA Container Runtime
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
```

**前提条件**:
1. NVIDIA Driver インストール済み
2. NVIDIA Container Toolkit インストール済み
3. Docker が NVIDIA runtime を認識

**検証コマンド**:
```bash
# NVIDIA runtime 確認
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi

# コンテナ内CUDA確認
docker exec openvoice_native python -c "import torch; print(torch.cuda.is_available())"
```

**教訓**:
- CUDA対応には `runtime: nvidia` と `NVIDIA_VISIBLE_DEVICES` が必須
- PyTorch CUDA ビルド (cu118) だけでは不十分

---

## 最終構成

### Dockerfile

```dockerfile
FROM python:3.11-slim

ARG USE_CUDA=false
ARG DEVICE=cpu

# システム依存関係
RUN apt-get update && apt-get install -y \
    build-essential git ffmpeg \
    libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev \
    libsndfile1 libsndfile1-dev wget curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# PyTorch (CUDA/CPU)
RUN if [ "$USE_CUDA" = "true" ]; then \
        pip install --no-cache-dir torch==2.0.1 torchaudio==2.0.2 \
        --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch==2.0.1 torchaudio==2.0.2 \
        --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Python依存関係
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir git+https://github.com/myshell-ai/MeloTTS.git
RUN python -m unidic download

# OpenVoiceV2 ソース
COPY OpenVoiceV2/ /app/OpenVoiceV2/
WORKDIR /app/OpenVoiceV2
RUN pip install --no-deps -e .

WORKDIR /app
COPY main.py config.py models.py openvoice_service.py ./

RUN mkdir -p /app/storage/openvoice /app/storage/voices /app/data/openvoice

ENV PYTHONUNBUFFERED=1
ENV DEVICE=${DEVICE}
ENV STORAGE_PATH=/app/storage
ENV OPENVOICE_BASE_DIR=/app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-u", "main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  openvoice:
    build:
      context: ./openvoice_native
      args:
        USE_CUDA: ${USE_CUDA:-false}
        DEVICE: ${DEVICE:-cpu}
    container_name: openvoice_native
    runtime: nvidia  # GPU access
    ports:
      - "8001:8001"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./openvoice_native/data/openvoice:/app/data/openvoice:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=${DEVICE:-cpu}
      - STORAGE_PATH=/app/storage
      - OPENVOICE_BASE_DIR=/app
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - voice_network
    restart: unless-stopped
```

### requirements.txt (重要な変更箇所)

```txt
# Python 3.11 対応
numpy>=1.24.0,<2.0

# PyTorch (別途インストール)
# torch==2.0.1+cu118 または cpu
# torchaudio==2.0.2

# 音声処理 (MeloTTS依存)
librosa==0.9.1

# OpenVoice V2 (Cython 3.x 互換)
faster-whisper>=1.2.1
ctranslate2>=4.0,<5
tokenizers==0.13.3
transformers==4.27.4

# Wavmark (OpenVoice V2必須)
wavmark==0.0.3

# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
```

### .env 設定

**Mac (CPU) 環境**:
```bash
USE_CUDA=false
DEVICE=cpu
LOG_LEVEL=INFO
```

**EC2 (CUDA) 環境**:
```bash
USE_CUDA=true
DEVICE=cuda
LOG_LEVEL=INFO
```

---

## ビルドとデプロイ手順

### 1. Mac (Local) でのビルド

```bash
cd /path/to/video-message-app

# ビルド (CPU版)
docker-compose build openvoice

# 起動
docker-compose up -d openvoice

# ログ確認
docker logs openvoice_native --tail 50

# ヘルスチェック
curl http://localhost:8001/health | jq
```

### 2. EC2 (CUDA) でのビルド

**前提条件**:
```bash
# NVIDIA Driver
nvidia-smi

# Docker NVIDIA runtime
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi
```

**ビルドとデプロイ**:
```bash
# .envファイルにCUDA設定
cat > .env << EOF
USE_CUDA=true
DEVICE=cuda
LOG_LEVEL=INFO
EOF

# ビルド (CUDA版)
docker-compose build openvoice

# 起動
docker-compose up -d openvoice

# CUDA確認
docker exec openvoice_native python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# ログ確認
docker logs openvoice_native | grep "使用デバイス"
# 期待: "使用デバイス: cuda"
```

---

## トラブルシューティング

### PyAV ビルドエラー

**症状**: `Could not build wheels for av`

**確認**:
```bash
grep faster-whisper requirements.txt
# 出力: faster-whisper>=1.2.1
```

**対応**: faster-whisper を 1.2.1 以上にアップグレード

---

### モデルファイルが見つからない

**症状**: `不足モデルファイル: ['/data/openvoice/...'`

**確認**:
```bash
# config.py の設定確認
grep OPENVOICE_BASE_DIR config.py

# Dockerfile の ENV 確認
grep OPENVOICE_BASE_DIR Dockerfile

# docker-compose.yml の環境変数確認
grep OPENVOICE_BASE_DIR docker-compose.yml
```

**対応**:
1. config.py に `os.getenv("OPENVOICE_BASE_DIR", ...)` があるか確認
2. Dockerfile に `ENV OPENVOICE_BASE_DIR=/app` があるか確認
3. docker-compose.yml に `OPENVOICE_BASE_DIR=/app` があるか確認

---

### CUDA が利用できない

**症状**: `CUDA available: False`

**確認**:
```bash
# ホストでCUDA確認
nvidia-smi

# Docker runtime 確認
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi

# docker-compose.yml確認
grep -A2 "runtime:" docker-compose.yml
grep "NVIDIA_VISIBLE_DEVICES" docker-compose.yml
```

**対応**:
1. NVIDIA Container Toolkit インストール: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
2. docker-compose.yml に `runtime: nvidia` と `NVIDIA_VISIBLE_DEVICES=all` を追加
3. コンテナ再起動: `docker-compose restart openvoice`

---

## パフォーマンス比較

### ビルド時間

| 環境 | CPU | ビルド時間 |
|------|-----|----------|
| Mac M3 Pro | ARM64 (10 cores) | ~15分 |
| EC2 g4dn.xlarge | x86_64 (4 cores) | ~40分 |

### 推論速度 (予想)

| 環境 | デバイス | 音声合成速度 |
|------|---------|------------|
| Mac M3 | CPU | 1.0x - 2.0x |
| EC2 g4dn | Tesla T4 (CUDA) | 5.0x - 10.0x |

※実際の速度は音声長、テキスト複雑度に依存

---

## 統合テスト

### 自動テストスクリプト

```python
#!/usr/bin/env python3
"""OpenVoice Docker統合テスト"""
import requests

OPENVOICE_URL = "http://localhost:8001"

# 1. ヘルスチェック
resp = requests.get(f"{OPENVOICE_URL}/health")
data = resp.json()
assert data['status'] == 'healthy'
assert data['pytorch_device'] in ['cpu', 'cuda']
print(f"✓ Health OK - Device: {data['pytorch_device']}")

# 2. プロファイル一覧
resp = requests.get(f"{OPENVOICE_URL}/voice-clone/profiles")
profiles = resp.json()
print(f"✓ Profiles: {len(profiles)} registered")

print("✅ All tests passed!")
```

**実行**:
```bash
python3 test_integration.py
```

---

## まとめ

### 成功要因

1. **faster-whisper 1.2.1+** による Cython 3.x 互換性確保
2. **環境変数ベースのパス設定** で Docker/Native 両対応
3. **NVIDIA Container Runtime** による CUDA 統合
4. **段階的デバッグ** (Mac → EC2 → CUDA対応)

### 今後の改善点

1. マルチステージビルドでイメージサイズ削減
2. キャッシュ最適化でビルド時間短縮
3. GPU utilization モニタリング追加
4. 音声合成パフォーマンステスト自動化

---

## 参考リンク

- [OpenVoice V2 GitHub](https://github.com/myshell-ai/OpenVoice)
- [faster-whisper Release Notes](https://github.com/SYSTRAN/faster-whisper/releases)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [PyAV Documentation](https://pyav.org/)

---

**作成者**: Claude Code
**最終更新**: 2025-11-03
