# 🗄️ ストレージ永続化ガイド

## 概要
このガイドでは、音声クローニングアプリケーションの永続化設定について説明します。

## 📁 ディレクトリ構造

```
video-message-app/
├── data/                           # 永続化マウントポイント（ホスト側）
│   ├── backend/
│   │   ├── storage/               # バックエンドデータ永続化
│   │   │   ├── voices/           # 音声プロファイル
│   │   │   │   ├── profiles/     # プロファイル情報
│   │   │   │   │   └── openvoice_xxxxx/
│   │   │   │   │       ├── embedding.pkl     # 音声埋め込み（重要！）
│   │   │   │   │       ├── profile.json      # プロファイル情報
│   │   │   │   │       ├── sample_01.wav     # 録音音声サンプル1（参照音声）
│   │   │   │   │       ├── sample_02.wav     # 録音音声サンプル2
│   │   │   │   │       └── sample_03.wav     # 録音音声サンプル3
│   │   │   │   ├── embeddings/   # 音声埋め込みファイル
│   │   │   │   └── samples/       # 音声サンプル
│   │   │   └── openvoice/         # OpenVoice出力ファイル
│   │   ├── models/                # AIモデルファイル
│   │   └── temp/                  # 一時ファイル（永続化）
│   ├── voicevox/                  # VOICEVOX音声モデル永続化
│   └── openvoice/                 # OpenVoice V2モデル永続化
├── docker-compose.yml
└── ...
```

## 🐳 Docker設定

### docker-compose.yml マウント設定

```yaml
services:
  backend:
    volumes:
      - ./backend:/app                        # 開発用（ソースコード）
      - ./data/backend/storage:/app/storage   # 音声データ永続化
      - ./data/backend/models:/app/models     # AIモデル永続化
      - ./data/backend/temp:/app/temp         # 一時ファイル永続化
      - ./data/openvoice:/app/openvoice_models # OpenVoice V2モデル

  voicevox:
    volumes:
      - ./data/voicevox:/opt/voicevox_engine  # VOICEVOX永続化
```

## 🔧 重要なファイルの永続化

### 1. 音声埋め込みファイル（embedding.pkl）
**場所**: `/app/storage/voices/profiles/{profile_id}/embedding.pkl`
**重要度**: ★★★★★
**内容**: 音声クローンの特徴データ
**問題**: これが失われると「ボー」音になる

### 2. 音声プロファイル情報（profile.json）
**場所**: `/app/storage/voices/profiles/{profile_id}/profile.json`
**重要度**: ★★★★☆
**内容**: プロファイルメタデータ

### 3. 音声サンプルファイル（sample_xx.wav）
**場所**: `/app/storage/voices/profiles/{profile_id}/sample_01.wav, sample_02.wav, sample_03.wav`
**重要度**: ★★★★☆
**内容**: 録音した全ての音声サンプル（再学習・品質向上に重要）

### 4. 録音一時ファイル
**場所**: `/app/temp/`
**重要度**: ★★★☆☆
**内容**: 録音処理中の一時ファイル

### 5. OpenVoice V2モデルファイル
**場所**: `/app/openvoice_models/`
**重要度**: ★★★★☆
**内容**: 音声合成用のAIモデル

## 🚨 トラブルシューティング

### 問題1: 音声クローンで「ボー」音が聞こえる→エラー表示に変更
**原因**: 埋め込みファイル（embedding.pkl）が見つからない
**現在の動作**: 適切なエラーメッセージが表示される
**解決**: 
1. `/data/backend/storage/voices/profiles/` ディレクトリの存在確認
2. プロファイルIDディレクトリ内の `embedding.pkl` ファイル存在確認
3. 音声クローンを再作成

### 問題2: 音声クローニングが高速すぎる→実際の音声時間ベースに変更
**原因**: 処理時間が実際の音声時間に基づいていない
**現在の動作**: 音声時間×0.4の処理時間で実行される
**解決**:
1. バックエンドログで「音声総時間: X秒, 推定処理時間: Y秒」確認
2. 実際の音声サンプル時間が適切に検出されているか確認

### 問題3: コンテナ再起動後にプロファイルが消える
**原因**: ボリュームマウントが正しく設定されていない
**解決**:
1. `docker-compose.yml` のボリューム設定確認
2. `./data/` ディレクトリの権限確認
3. Docker再起動

## 📊 ログ確認方法

### バックエンドログ確認
```bash
docker logs voice_backend
```

### 重要なログメッセージ
- `音声特徴抽出開始: X個のサンプルを分析中...`
- `音声総時間: X.X秒, 推定処理時間: Y.Y秒`
- `音声クローン作成完了: /app/storage/voices/profiles/xxx/embedding.pkl`
- `埋め込みファイルが見つかりました。クローン音声で合成を試行します`
- `ERROR: 音声クローンが利用できません。プロファイル「xxx」の埋め込みデータが見つかりません`

## 🔄 メンテナンス

### データバックアップ
```bash
# 音声データバックアップ
tar -czf voice_data_backup_$(date +%Y%m%d).tar.gz data/

# 特定プロファイルのバックアップ
cp -r data/backend/storage/voices/profiles/openvoice_xxxxx backup/
```

### 古いファイル清理
```bash
# 一時ファイル清理（30日以上）
find data/backend/temp -type f -mtime +30 -delete

# ログファイル清理
find logs -type f -mtime +7 -delete
```

## ✅ 設定確認チェックリスト

- [ ] `data/` ディレクトリが作成されている
- [ ] docker-compose.yml でボリュームマウントが正しく設定されている
- [ ] 音声クローニング時に適切な処理時間がかかっている（3-5秒）
- [ ] 埋め込みファイルが永続パスに保存されている
- [ ] テスト音声で実際のクローン音声が再生される（「ボー」音ではない）

---

**注意**: この設定により、コンテナを再起動しても音声クローンデータが失われることはありません。