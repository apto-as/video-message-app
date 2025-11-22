# Conda環境統合セットアップガイド

OpenVoice依存関係問題解決のため、Conda環境をPython 3.11に対応させる統合セットアップツールです。

## 📋 統合後のファイル

1. **`setup_new_env.sh`** - 統合環境セットアップスクリプト（全機能対応）
2. **`backend/conda_requirements.txt`** - 最適化されたパッケージリスト

## 🚀 使用方法

### 方法1: 新しい環境作成（推奨）

```bash
./setup_new_env.sh prototype-app
```

**特徴:**
- 🆕 Python 3.11.12で新規環境作成
- 📦 すべての依存関係を段階的にインストール
- 🔄 自動競合回避
- ✅ 完全な動作確認

### 方法2: 既存環境の修正

既存環境がある場合の依存関係修正：

```bash
./setup_new_env.sh prototype-app --fix-only
```

**特徴:**
- ⚡ 高速（2-3分）
- 📦 既存環境を保持
- 🔧 依存関係のみ修正
- ✅ パッケージ競合の自動解決

## 🎯 対象パッケージ

### メインバックエンドサービス用
- **Web Framework:** FastAPI, Uvicorn, Pydantic
- **HTTP/Network:** HTTPX, Requests
- **Image Processing:** Pillow, OpenCV, ONNX Runtime, rembg
- **Audio Processing:** SoundFile, PyDub, FFmpeg
- **Math/Scientific:** NumPy (<2.0), SciPy

### バージョン制約
- `numpy>=1.24.0,<2.0.0` （重要：2.x系を回避）
- `pillow>=10.0.0,<11.0.0`
- `opencv-python-headless==4.10.0.84`

## 🔍 実行前チェック

現在の環境状態を確認：

```bash
# Python バージョン
python --version

# 環境一覧
conda env list

# 現在の環境名
echo $CONDA_DEFAULT_ENV
```

## ✅ 実行後確認

スクリプト実行後、以下が自動で確認されます：

```bash
✅ FastAPI: 0.104.1
✅ Uvicorn: 0.24.0
✅ HTTPX: 0.25.2
✅ NumPy: 1.24.x (1.x系)
✅ SciPy: 1.16.0
✅ Pydantic: 2.7.x+
✅ Pillow: 10.x.x
✅ OpenCV: 4.x.x
✅ ONNX Runtime: 1.21.x+
✅ Rembg: imported successfully
✅ Scikit-learn: 1.x.x
✅ Scikit-image: 0.x.x
```

## 🔧 トラブルシューティング

### 環境作成失敗
```bash
# 既存環境を完全削除
conda env remove -n prototype-app -y

# 再実行
./setup_new_env.sh prototype-app
```

### パッケージ競合エラー
```bash
# 依存関係のみ修正
./setup_new_env.sh prototype-app --fix-only
```

### 権限エラー
```bash
# スクリプトに実行権限を付与
chmod +x setup_new_env.sh
```

## 🎯 次のステップ

環境セットアップ完了後：

1. **バックエンドサービス起動テスト**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 55433
   ```

2. **OpenVoice Native Service確認**
   ```bash
   cd ../openvoice_native
   uv run python -m uvicorn main:app --reload --port 55434
   ```

3. **統合テスト実行**
   - フロントエンドでVOICEVOX音声合成をテスト
   - D-ID動画生成をテスト
   - OpenVoice音声クローンをテスト

## 📞 サポート

問題が発生した場合：
1. エラーメッセージの全文を確認
2. `python --version`と`conda list`の出力を確認
3. 必要に応じて完全再構築を実行