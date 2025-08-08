# 🧪 動画メッセージアプリ テストガイド

## 事前準備

### 1. テスト用画像の準備
以下のような画像を用意してください：

**メイン画像（人物写真）**:
- 人物が写っている写真（JPG、PNG形式）
- サイズ: 100x100px ～ 4096x4096px
- ファイルサイズ: 5MB以下
- 推奨: 背景がある人物のポートレート写真

**背景画像（オプション）**:
- 合成したい背景画像（風景、スタジオ背景など）
- 同じサイズ制限が適用されます

### 2. テスト環境確認
```bash
# 現在のディレクトリ確認
pwd
# → /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/backend

# 必要なライブラリが入っているか確認
python -c "import rembg, PIL, cv2; print('✅ All libraries installed')"
```

## 🚀 サーバー起動手順

### ターミナル1: バックエンド起動
```bash
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/backend
./run_server.sh
```

**期待される出力**:
```
🚀 バックエンドサーバーを起動します...
INFO:     Will watch for changes in these directories: ['/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using WatchFiles
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### ターミナル2: フロントエンド起動
```bash
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/frontend
./run_frontend.sh
```

**期待される出力**:
```
🎨 フロントエンドサーバーを起動します...
Compiled successfully!

You can now view frontend in the browser.
  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

## 🧪 テスト項目

### 【テスト1】基本的な画像アップロード
1. ブラウザで `http://localhost:3000` を開く
2. 「画像を選択」をクリック
3. 人物写真をアップロード
4. ✅ プレビュー画像が表示される

### 【テスト2】背景削除機能
1. 画像をアップロード後、背景処理セクションが表示される
2. 「背景を削除する」がチェックされていることを確認
3. 「✨ 画像を処理」をクリック
4. ✅ 処理中インジケーターが表示される
5. ✅ 処理済み画像（背景削除済み）が表示される
6. ✅ 処理状況に「背景削除: ✅」が表示される

### 【テスト3】背景合成機能
1. メイン画像をアップロード
2. 「🖼️ 背景画像を選択」から背景画像をアップロード
3. 「✨ 画像を処理」をクリック
4. ✅ 人物と背景が合成された画像が表示される
5. ✅ 処理状況に「背景合成: ✅」が表示される

### 【テスト4】動画生成（統合テスト）
1. 画像処理完了後、テキスト入力欄にメッセージを入力
   - 例: "お誕生日おめでとうございます！"
2. 「🎨 処理済み画像で動画を生成」をクリック
3. ✅ D-ID APIで動画が生成される
4. ✅ 生成された動画が再生される

### 【テスト5】エラーハンドリング
1. **大きすぎるファイル**: 5MB以上の画像をアップロード
   - ✅ エラーメッセージが表示される
2. **非対応ファイル**: PDF等の非画像ファイルをアップロード
   - ✅ エラーメッセージが表示される
3. **空のテキスト**: テキストを入力せずに動画生成
   - ✅ エラーメッセージが表示される

## 🔧 トラブルシューティング

### バックエンドエラーの場合
```bash
# ログを確認
tail -f /dev/null  # サーバーの出力を確認

# 依存関係の再インストール
pip install -r requirements.txt

# 画像処理ライブラリのテスト
python test_background_processing.py
```

### フロントエンドエラーの場合
```bash
# 依存関係の再インストール
npm install

# キャッシュクリア
npm start -- --reset-cache
```

### CORSエラーの場合
- バックエンドとフロントエンドが正しいポートで起動しているか確認
- バックエンド: http://localhost:8000
- フロントエンド: http://localhost:3000

## 📊 期待される処理時間

| 処理 | 画像サイズ | 期待時間 |
|------|------------|----------|
| 背景削除 | 512x512px | 1-2秒 |
| 背景削除 | 1024x1024px | 2-4秒 |
| 背景合成 | 1024x1024px | 1-2秒 |
| 動画生成 | D-ID API | 30-60秒 |

## 🎯 成功判定基準

### 🟢 完全成功
- 全ての処理がエラーなく完了
- 背景削除の精度が高い
- 合成画像が自然
- 動画が正常に再生される

### 🟡 部分成功
- 基本機能は動作するが、処理時間が長い
- 背景削除の精度にばらつき
- 一部のエラーハンドリングが不完全

### 🔴 失敗
- サーバーが起動しない
- 画像処理でエラーが発生
- D-ID APIとの連携に失敗

## 📝 テスト結果の記録

テスト実行時は以下を記録してください：
- 使用した画像のサイズと形式
- 各処理の実際の処理時間
- 発生したエラーメッセージ
- 生成された動画の品質

---

## 🆘 困った時は

1. **エラーログの確認**: ブラウザの開発者ツール（F12）→ Console
2. **サーバーログの確認**: ターミナルの出力メッセージ
3. **ネットワーク確認**: 開発者ツール → Network タブ
4. **画像ファイルの確認**: 形式、サイズ、破損していないか