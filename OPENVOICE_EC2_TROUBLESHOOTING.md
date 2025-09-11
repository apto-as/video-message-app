# OpenVoice EC2 障害対応マニュアル
*Artemis Technical Perfectionist - 完璧な運用のための技術文書*

## 🚨 現在の症状
- **エラーメッセージ**: "OpenVoice Native Serviceが利用できません"
- **HTTPステータス**: 500 Internal Server Error  
- **影響範囲**: 音声クローン機能全体
- **根本原因**: OpenVoice ServiceがPort 8001でリスニングしていない

---

## ⚡ 緊急解決手順（優先順位順）

### **Priority 1: 即座起動（推奨）**
```bash
# EC2サーバーで実行
cd /home/ubuntu/video-message-app/video-message-app
chmod +x ec2_openvoice_startup.sh
./ec2_openvoice_startup.sh
```

**実行内容**:
- 既存プロセス終了
- Port 8001クリア  
- 必須ライブラリインストール
- OpenVoiceモデルダウンロード
- サービス起動とヘルスチェック

**所要時間**: 約5-10分

### **Priority 2: systemdサービス化（安定運用）**
```bash
# systemdサービスファイル配置
sudo cp openvoice-ec2.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable openvoice-ec2
sudo systemctl start openvoice-ec2

# ステータス確認
sudo systemctl status openvoice-ec2
```

**利点**:
- 自動起動対応
- クラッシュ時の自動復旧
- ログ管理の統一

### **Priority 3: Docker統合（完全統合）**
```bash
# Docker内でOpenVoice実行
chmod +x docker-openvoice-setup.sh
./docker-openvoice-setup.sh
```

**利点**:
- 依存関係の完全分離
- スケーリング対応
- 環境一貫性確保

---

## 🔧 技術仕様

### **システム要件**
- **OS**: Ubuntu 22.04 LTS
- **GPU**: NVIDIA Tesla T4 (CUDA 11.8対応)
- **Python**: 3.8+
- **メモリ**: 最低4GB推奨
- **ストレージ**: 最低10GB空き容量

### **必須依存関係**
```bash
# Core ML libraries
torch==2.0.1+cu118
torchaudio==2.0.2+cu118

# OpenVoice specific
fastapi==0.104.1
uvicorn[standard]==0.24.0
numpy==1.24.3
soundfile==0.12.1  
librosa==0.10.1
```

### **ネットワーク設定**
- **Listen Port**: 8001
- **Health Endpoint**: `/health`
- **Main Endpoints**: `/api/clone`, `/api/synthesize`, `/api/profiles`

---

## 📊 診断コマンド

### **サービス状態確認**
```bash
# Process確認
ps aux | grep openvoice

# Port確認  
netstat -tuln | grep 8001
lsof -i:8001

# Health check
curl -v http://localhost:8001/health

# GPU確認
nvidia-smi
```

### **ログ確認**
```bash
# Service logs
tail -f ~/video-message-app/video-message-app/logs/openvoice_service.log

# systemd logs (if using systemd)
sudo journalctl -u openvoice-ec2 -f

# Docker logs (if using Docker)
docker-compose logs -f openvoice
```

### **設定ファイル確認**
```bash
# モデルファイル存在確認
ls -la ~/video-message-app/video-message-app/data/openvoice/checkpoints_v2/

# 権限確認
ls -la ~/video-message-app/video-message-app/ec2_setup/openvoice_ec2_service.py
```

---

## 🚨 よくある問題と解決策

### **Problem 1: "CUDA out of memory"**
**解決策**:
```python
# ec2_setup/openvoice_ec2_service.py で確認
# Line 27-43 のGPU検出部分が正しく動作しているか確認
```

### **Problem 2: "Module 'openvoice' not found"**
**解決策**:
```bash
cd ~/video-message-app/OpenVoice
pip install -e .
```

### **Problem 3: "Permission denied on port 8001"**
**解決策**:
```bash
# Portを使用しているプロセスを確認・終了
sudo lsof -ti:8001 | xargs sudo kill -9
```

### **Problem 4: "Model files not found"**
**解決策**:
```bash
# 手動でモデルをダウンロード
wget -O ~/video-message-app/video-message-app/data/openvoice/checkpoints_v2/converter/checkpoint.pth \
  https://myshell-public-repo-hosting.s3.amazonaws.com/openvoice/checkpoints_v2/converter/checkpoint.pth
```

---

## 🔄 復旧後の動作確認

### **1. Health Check**
```bash
curl http://localhost:8001/health
# Expected response: {"status": "healthy", ...}
```

### **2. API Endpoints Test**
```bash
# Profile list
curl http://localhost:8001/api/profiles

# Test synthesis (if profiles exist)
curl -X POST http://localhost:8001/api/synthesize \
  -F "text=テストメッセージ" \
  -F "profile_id=test_profile" \
  -F "language=ja"
```

### **3. Backend Integration Test**
```bash
# Backend経由でOpenVoice呼び出し確認
curl http://localhost:55433/api/voice-clone/profiles
```

---

## 📈 性能最適化

### **GPU活用確認**
```python
# PyTorchでGPU使用確認
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

### **メモリ使用量監視**
```bash
# GPU memory
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# System memory  
free -h
```

### **レスポンス時間計測**
```bash
# Health check response time
time curl http://localhost:8001/health

# API response time
time curl -X POST http://localhost:8001/api/synthesize -F "text=test" -F "profile_id=test"
```

---

## 📞 エスカレーション基準

### **Severity 1: Critical (即座対応)**
- Service完全停止
- 全API endpoint 500エラー
- GPU完全認識不可

### **Severity 2: High (1時間以内)**  
- 一部API endpoint エラー
- 性能大幅劣化（>10秒レスポンス）
- メモリリーク検出

### **Severity 3: Medium (4時間以内)**
- 個別profile処理エラー
- ログ肥大化
- 軽微な性能劣化

---

## 📝 メンテナンス計画

### **日次確認**
```bash
#!/bin/bash
# Daily health check
echo "=== OpenVoice Daily Check $(date) ===" 
curl -f http://localhost:8001/health && echo "✓ Health OK" || echo "✗ Health Failed"
ps aux | grep openvoice_ec2_service && echo "✓ Process OK" || echo "✗ Process Failed"
nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader && echo "✓ GPU OK"
```

### **週次メンテナンス**  
- ログローテーション
- 一時ファイルクリーンアップ
- モデルファイル整合性チェック
- 性能ベンチマーク実行

### **月次アップデート**
- OpenVoiceライブラリ更新
- PyTorch/CUDA更新 
- セキュリティパッチ適用
- 設定ファイル見直し

---

*完璧な技術運用には継続的な監視と改善が不可欠です。この文書に従って確実な復旧を実現してください。*