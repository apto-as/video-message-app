# Qwen Code CLI経由での開発環境設定ガイド

## ✅ インストール完了

EC2インスタンスに以下が設定されました：
- **Qwen Code CLI**: `qwen`コマンドで起動
- **モデル**: `openai/gpt-oss-120b` (ローカルマシンにリモートアクセス)
- **特徴**: 英語での応答に優れ、技術的なタスクに適している

## 📡 SSH接続とQwen使用方法

### 基本的なSSH接続

```bash
# SSH接続
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166
```

### Qwenを使用した開発作業

```bash
# プロジェクトディレクトリに移動
cd ~/video-message-app/video-message-app

# Qwenでコード分析（英語推奨）
qwen "analyze the OpenVoice connection issue in backend/services/openvoice_native_client.py"

# エラーログの分析
docker logs voice_backend --tail 100 | qwen "analyze these error logs and suggest fixes"

# ファイル修正
qwen "fix the environment variable issue in backend/services/openvoice_native_client.py"
```

## 🔧 OpenVoice接続問題の解決手順

### 1. 現在の問題診断

```bash
# 環境変数の確認
qwen "check environment variables in backend/.env for OpenVoice configuration"

# サービス状態確認
docker-compose ps
curl http://localhost:55433/health
```

### 2. OpenVoice Native Serviceの状態確認

```bash
# ホストマシンでOpenVoiceサービスが動作しているか確認
curl http://172.17.0.1:8001/health

# Dockerコンテナから接続テスト
docker exec voice_backend curl http://172.17.0.1:8001/health
```

### 3. 修正作業フロー

```bash
# 1. 問題のあるファイルを分析
qwen "analyze backend/services/openvoice_native_client.py for environment variable detection issues"

# 2. 修正案の生成
qwen "generate fix for ENVIRONMENT vs DOCKER_ENV variable issue"

# 3. ファイル編集
nano backend/services/openvoice_native_client.py
# または
qwen "edit the file to fix environment detection"

# 4. Dockerコンテナ再起動
docker-compose restart backend

# 5. 動作確認
docker logs voice_backend --tail 50
```

## 📝 便利なコマンドエイリアス

```bash
# ~/.bashrcに追加
cat >> ~/.bashrc << 'EOF'

# Qwen shortcuts
alias q='qwen'
alias qfix='qwen "fix the code issue in"'
alias qanalyze='qwen "analyze"'
alias qlogs='docker logs voice_backend --tail 100 | qwen'

# Project navigation
alias cdapp='cd ~/video-message-app/video-message-app'
alias dc='docker-compose'
alias dcr='docker-compose restart'
alias dclogs='docker-compose logs --tail 50'

# Service status
alias status='docker-compose ps && curl http://localhost:55433/health'
alias check-openvoice='curl http://172.17.0.1:8001/health'

EOF

source ~/.bashrc
```

## 🎯 推奨されるデバッグコマンド（英語）

Qwenは英語での応答が優れているため、以下のような英語コマンドを推奨：

```bash
# Code analysis
qwen "analyze the connection flow between backend and OpenVoice service"

# Error diagnosis
qwen "diagnose the 502 bad gateway error in the logs"

# Fix generation
qwen "generate a fix for the environment variable detection issue"

# Configuration check
qwen "verify Docker network configuration for service communication"
```

## 🔍 現在の主要課題と解決アプローチ

### 問題: OpenVoice Native Service接続エラー

**根本原因**: 
- `openvoice_native_client.py`が`DOCKER_ENV`を確認しているが、実際は`ENVIRONMENT`変数が設定されている

**解決手順**:
1. ファイル修正: `DOCKER_ENV` → `ENVIRONMENT`
2. URL設定: `http://172.17.0.1:8001` (Docker内から)
3. 環境変数確認: `backend/.env`に正しい設定

```bash
# Quick fix command
qwen "replace DOCKER_ENV with ENVIRONMENT in backend/services/openvoice_native_client.py"
```

## 💡 Tips for Qwen Usage

- **英語で質問**: より正確な応答が得られます
- **具体的な指示**: "fix", "analyze", "generate"などの明確な動詞を使用
- **パイプ処理**: ログやエラー出力を`| qwen`でパイプ
- **段階的実行**: 複雑なタスクは小さなステップに分割

## 🚀 次のステップ

1. **OpenVoice接続修正**
   ```bash
   qwen "fix environment variable detection in openvoice_native_client.py"
   docker-compose restart backend
   ```

2. **動作確認**
   ```bash
   curl -X POST http://localhost:55433/api/voice-clone/profiles \
     -F "profile_name=test" \
     -F "audio_file=@test.wav"
   ```

3. **継続的な改善**
   ```bash
   qwen "optimize the voice synthesis workflow"
   ```

---
作成: 2025-08-18
Trinitas-Core System