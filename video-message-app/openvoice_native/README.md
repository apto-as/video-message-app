# OpenVoice Native Service

ネイティブMacOS環境で動作するOpenVoice V2専用サービス

## 概要

Docker環境でのPyTorch/OpenVoice互換性問題を回避するため、OpenVoice V2機能をネイティブPython環境で実行します。

## セットアップ方法

### 方法1: UV Modern (推奨) - Conda + UV ハイブリッド
```bash
# PyTorchはConda、その他はUVで高速管理
./setup_uv_modern.sh
./start_uv_modern.sh
```

### 方法2: UV Legacy - 従来のUV方式
```bash
# Conda環境内でもUVは安全に動作します
./setup_conda_uv.sh
./start_uv.sh
```

### 方法3: 従来のvenv
```bash
python3 setup.py
./start.sh
```

### 方法4: 開発モード (Conda環境で直接実行)
```bash
# 既にConda環境に必要なパッケージがインストールされている場合
./start_dev.sh
```

## アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Backend        │    │ OpenVoice       │
│   (Docker)      │    │  (Docker)       │    │ Native Service  │
│   Port: 55434   │◄──►│  Port: 55433    │◄──►│  Port: 8001     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                        ┌─────────────────┐
                        │   VoiceVox      │
                        │   (Docker)      │
                        │   Port: 50021   │
                        └─────────────────┘
```

## 機能

- 音声クローンプロファイル管理
- OpenVoice V2による音声合成
- 音声特徴抽出と埋め込み生成
- RESTful API提供

## 依存関係

- Python 3.11+
- PyTorch (MPS対応)
- OpenVoice V2
- FastAPI

## ポート

- 8001: OpenVoice Native Service API