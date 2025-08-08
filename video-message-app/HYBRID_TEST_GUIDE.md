# VOICEVOX + D-ID ハイブリッドシステム手動テストガイド

## 前提条件
- Dockerコンテナが起動中（VOICEVOX、Backend、Frontend）
- D-ID APIキーが設定済み（.envファイル）
- テスト用の画像ファイル（人物の顔写真）

## テスト手順

### 1. システム状態確認

```bash
# コンテナの状態確認
docker ps

# 期待される出力:
# voice_backend    (ポート8000)
# voicevox_engine  (ポート50021)
# voice_frontend   (ポート3000)
```

### 2. VOICEVOX話者一覧の確認

```bash
# 利用可能な話者を確認
curl http://localhost:8000/api/hybrid-video/voicevox-speakers | jq
```

主な話者ID:
- 2: 四国めたん（ノーマル）
- 0: 四国めたん（あまあま）
- 3: ずんだもん（ノーマル）
- 1: ずんだもん（あまあま）
- 8: 春日部つむぎ（ノーマル）

### 3. API経由でのハイブリッド動画生成テスト

#### 方法A: cURLコマンドでのテスト

```bash
# テスト画像を準備（例: test_face.jpg）
# 以下のコマンドでハイブリッド動画を生成

curl -X POST http://localhost:8000/api/hybrid-video/generate-with-voicevox \
  -F "text=こんにちは、私はVOICEVOXとD-IDを組み合わせたハイブリッドシステムです。日本語の自然な発話が可能になりました。" \
  -F "image=@test_face.jpg" \
  -F "speaker_id=3" \
  -F "speed_scale=1.0" \
  -F "pitch_scale=0.0" \
  -F "remove_background=false" \
  -F "enhance_quality=true"
```

#### 方法B: HTTPieでのテスト（より見やすい）

```bash
# HTTPieがインストールされていない場合
brew install httpie

# ハイブリッド動画生成
http -f POST localhost:8000/api/hybrid-video/generate-with-voicevox \
  text="VOICEVOXの音声でD-IDの動画を生成するテストです" \
  image@test_face.jpg \
  speaker_id=2 \
  speed_scale=1.1
```

### 4. Postmanでのテスト

1. Postmanを開く
2. 新しいリクエストを作成
3. 設定:
   - Method: POST
   - URL: `http://localhost:8000/api/hybrid-video/generate-with-voicevox`
   - Body: form-data
   
4. パラメータ:
   - `text` (text): 読み上げたいテキスト
   - `image` (file): 人物の顔画像
   - `speaker_id` (text): 話者ID（例: 3）
   - `speed_scale` (text): 話速（例: 1.0）
   - `pitch_scale` (text): 音高（例: 0.0）
   - `intonation_scale` (text): 抑揚（例: 1.0）
   - `volume_scale` (text): 音量（例: 1.0）
   - `remove_background` (text): true/false
   - `enhance_quality` (text): true/false

### 5. 音声パラメータの調整

各パラメータの効果:
- `speaker_id`: 話者の声質を変更
- `speed_scale`: 0.5〜2.0（遅い〜速い）
- `pitch_scale`: -0.15〜0.15（低い〜高い）
- `intonation_scale`: 0.0〜2.0（平坦〜抑揚強）
- `volume_scale`: 0.0〜2.0（小さい〜大きい）

### 6. テスト例

#### 例1: ずんだもん（あまあま）でゆっくり話す
```bash
curl -X POST http://localhost:8000/api/hybrid-video/generate-with-voicevox \
  -F "text=ずんだもんなのだ！ゆっくりお話しするのだ！" \
  -F "image=@test_face.jpg" \
  -F "speaker_id=1" \
  -F "speed_scale=0.8"
```

#### 例2: 春日部つむぎで元気に話す
```bash
curl -X POST http://localhost:8000/api/hybrid-video/generate-with-voicevox \
  -F "text=元気いっぱい、春日部つむぎです！今日も一日頑張りましょう！" \
  -F "image=@test_face.jpg" \
  -F "speaker_id=8" \
  -F "speed_scale=1.2" \
  -F "pitch_scale=0.05" \
  -F "intonation_scale=1.3"
```

### 7. レスポンスの確認

成功時のレスポンス例:
```json
{
  "success": true,
  "video_url": "https://d-id-talks-prod.s3.us-west-2.amazonaws.com/...",
  "message": "VOICEVOX音声（話者ID: 3）でD-ID動画生成が完了しました"
}
```

エラー時のレスポンス例:
```json
{
  "detail": "エラーメッセージ"
}
```

### 8. 生成された動画の確認

1. レスポンスの`video_url`をコピー
2. ブラウザで開く
3. 動画が正しく生成されているか確認
   - 音声がVOICEVOXの日本語音声か
   - 口の動きが同期しているか
   - 画質が適切か

### トラブルシューティング

#### D-ID APIキーエラー
```bash
# .envファイルのD-ID APIキーを確認
cat .env | grep DID_API_KEY
```

#### VOICEVOX接続エラー
```bash
# VOICEVOXの状態確認
curl http://localhost:50021/version
```

#### バックエンドエラー
```bash
# バックエンドログ確認
docker logs voice_backend --tail 50
```

### 推奨テストケース

1. **基本テスト**: デフォルト設定で動作確認
2. **話者バリエーション**: 各話者IDでテスト
3. **パラメータ調整**: 速度・音高・抑揚の組み合わせ
4. **長文テスト**: 100文字以上のテキスト
5. **背景処理テスト**: remove_background=true
6. **品質向上テスト**: enhance_quality=true

### パフォーマンス計測

```bash
# time コマンドで処理時間計測
time curl -X POST http://localhost:8000/api/hybrid-video/generate-with-voicevox \
  -F "text=パフォーマンステスト" \
  -F "image=@test_face.jpg" \
  -F "speaker_id=3"
```

期待される処理時間:
- VOICEVOX音声生成: 200-500ms
- D-ID動画生成: 10-30秒
- 合計: 15-35秒