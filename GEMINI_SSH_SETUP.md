# Gemini CLI経由での開発環境設定ガイド

## ✅ インストール完了

EC2インスタンスに以下がインストールされました：
- **Node.js**: v20.19.4
- **npm**: 10.8.2
- **Gemini CLI**: 0.1.18 (`/usr/bin/gemini`)

## 📡 SSH接続方法

### 基本的なSSH接続

```bash
# 通常のSSH接続
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166
```

### Geminiセットアップ用コマンド

SSH接続後、以下のコマンドでGemini APIキーを設定してください：

```bash
# Gemini API キーの設定（接続後に実行）
export GEMINI_API_KEY="your-api-key-here"

# または永続的に設定
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# 設定確認
gemini config
```

## 🚀 Gemini CLI活用方法

### 1. プロジェクトディレクトリでの作業

```bash
# プロジェクトディレクトリに移動
cd ~/video-message-app/video-message-app

# Geminiでプロジェクト分析
gemini analyze .

# コード生成や修正
gemini "OpenVoice接続の問題を修正して"
```

### 2. ファイル編集・管理

```bash
# ファイルの内容をGeminiに渡して編集
gemini edit backend/services/openvoice_native_client.py

# 複数ファイルの一括処理
gemini "backend/servicesディレクトリの全てのPythonファイルをチェック"
```

### 3. デバッグとトラブルシューティング

```bash
# エラーログの分析
docker logs voice_backend --tail 100 | gemini "このエラーを分析して修正方法を提案"

# システム状態の診断
gemini "docker-compose ps && docker logs voice_backend --tail 50" --analyze
```

## 🔧 推奨される作業フロー

### ステップ1: SSH接続とGemini設定

```bash
# ローカルから
ssh -i ~/.ssh/video-app-key.pem -p 22 ubuntu@3.115.141.166

# EC2内で
export GEMINI_API_KEY="your-api-key"
cd ~/video-message-app/video-message-app
```

### ステップ2: Geminiでの開発作業

```bash
# 現在の問題を診断
gemini "OpenVoice Native Serviceが接続できない問題を調査"

# 修正案の生成
gemini fix backend/services/openvoice_native_client.py

# テスト実行
gemini "python backend/scripts/test_voice_synthesis.py を実行して結果を分析"
```

### ステップ3: Docker環境の管理

```bash
# Dockerサービスの再起動
gemini "docker-compose restart backend && docker logs voice_backend -f"

# 環境変数の確認と修正
gemini "backend/.envファイルを確認してOpenVoice設定を最適化"
```

## 📝 便利なエイリアス設定

SSH接続後、以下のエイリアスを設定すると便利です：

```bash
# ~/.bashrcに追加
cat >> ~/.bashrc << 'EOF'

# Gemini shortcuts
alias gm='gemini'
alias gm-fix='gemini fix'
alias gm-analyze='gemini analyze'
alias gm-logs='docker logs voice_backend --tail 100 | gemini'

# Project shortcuts
alias cdapp='cd ~/video-message-app/video-message-app'
alias dc='docker-compose'
alias dcr='docker-compose restart'
alias dcl='docker-compose logs --tail 50'

# Quick status
alias status='docker-compose ps && echo "---" && curl http://localhost:55433/health'

EOF

source ~/.bashrc
```

## 🔐 セキュリティ注意事項

1. **APIキーの管理**
   - Gemini APIキーは環境変数で管理
   - ハードコードしない
   - `.env`ファイルで管理する場合は`.gitignore`に追加

2. **SSH鍵の保護**
   - `~/.ssh/video-app-key.pem`の権限は400に設定
   - 鍵ファイルを共有しない

3. **ポート管理**
   - 必要なポートのみ開放
   - セキュリティグループで適切に制限

## 🎯 次のステップ

1. **Gemini API キーの取得と設定**
   - Google AI Studioからキー取得
   - EC2インスタンスで環境変数設定

2. **OpenVoice問題の解決**
   - Gemini CLIを使用して接続問題を診断
   - 自動修正スクリプトの実行

3. **継続的な開発**
   - Geminiを活用した効率的なデバッグ
   - コード生成と最適化

## 💡 Tips

- `gemini --help`で全コマンド確認
- `gemini config`で現在の設定確認
- ログ分析時は`| gemini`でパイプ処理が便利
- 複雑なタスクは段階的に実行

---
作成: 2025-08-09
Trinitas-Core System