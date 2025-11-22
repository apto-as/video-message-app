# 要件定義サマリー
## Requirements Summary - User Responses Analysis

**Project**: Video Message App - Next Phase Development
**Date**: 2025-11-02
**Status**: ✅ ALL QUESTIONS ANSWERED
**Response Quality**: 🌟 Excellent - Clear and Detailed

---

## 📊 回答完了状況

| 優先度 | 総数 | 回答済み | 進捗率 |
|--------|------|---------|--------|
| 🔴 Critical | 8 | 8 | 100% ✅ |
| 🟡 Important | 6 | 6 | 100% ✅ |
| 🟢 Nice to Have | 5 | 5 | 100% ✅ |
| **合計** | **19** | **19** | **100%** |

---

## 🎯 プロジェクト特性の明確化

### ユースケース
**お祝いメッセージ動画生成**
- 明るくハキハキとした口調
- お祝い用BGM（5曲システム内蔵）
- シンプルで使いやすいUI

### ユーザー体験の優先事項
1. **シンプルさ**: 画面遷移最小化、確認ステップ削減
2. **品質**: 精度優先（95%）、画像・音声の最適化
3. **スピード**: パーセンテージ表示で処理状況を可視化

---

## 🔴 CRITICAL 要件（実装の核心）

### 1. 複数人物選択UI

#### Q1: UI配置
**決定**: **C) インライン表示**

**実装方針**:
```
┌─────────────────────────────────┐
│  アップロード画像              │
│  [画像プレビュー]              │
│                                 │
│  ↓ 複数人物検出時              │
│                                 │
│  どの人物を使用しますか？      │
│  [👤1] [👤2] [👤3]  ← 横並び │
│   ✓                             │
└─────────────────────────────────┘
```

**設計ポイント**:
- 画面遷移なし（モーダル・サイドパネル不使用）
- アップロード画像の直下に配置
- 横幅はアップロード画像の表示範囲内

---

#### Q2: プレビュー表示
**決定**: **A) サムネイル一覧（横並び）**

**実装仕様**:
```html
<div class="person-selector">
  <div class="person-thumbnail" data-person-id="1">
    <img src="person1_preview.png" />
    <input type="radio" name="selected-person" checked />
  </div>
  <div class="person-thumbnail" data-person-id="2">
    <img src="person2_preview.png" />
    <input type="radio" name="selected-person" />
  </div>
  <!-- ... -->
</div>
```

**サイズ制約**:
- 横幅: アップロード画像の表示範囲内
- 高さ: 適度なサムネイルサイズ（150-200px推奨）
- 検出人数制限: UI上は3-5人まで表示推奨

---

#### Q3: 確認フロー
**決定**: **B) 不要（選択後すぐ次へ）**

**実装フロー**:
```
1. 画像アップロード
   ↓
2. 複数人物検出（YOLOv8）
   ↓
3. 人物選択UI表示（インライン）
   ↓
4. ユーザーが1人選択
   ↓ (即座に)
5. 背景除去処理開始（確認ダイアログなし）
```

**UXへの影響**:
- ステップ削減 → 処理時間短縮
- シンプルなワークフロー
- エラー時のみリトライ/キャンセル選択

---

### 2. BiRefNet高精度セグメンテーション

#### Q4: デプロイ場所
**決定**: **B) EC2インスタンス（g4dn.xlarge, Tesla T4 GPU）**

**インフラ構成**:
```
EC2 Instance (g4dn.xlarge)
├── Backend (FastAPI) - Port 55433
├── BiRefNet Service - Port 55441 (新規)
│   └── Tesla T4 GPU使用
├── OpenVoice Native - Port 8001
├── VOICEVOX - Port 50021
└── Frontend - Port 55434
```

**理由**:
- 既存インフラの活用（追加コストなし）
- GPU推論の高速化（80ms）
- スケーラビリティは後回し

**コスト影響**: $0（既存EC2で対応）

---

#### Q5: 精度 vs 速度
**決定**: **A) 精度優先（95%精度、GPU 80ms）**

**技術仕様**:
- モデル: BiRefNet-general（最高精度）
- 推論時間: 80ms（GPU加速）
- 精度目標: 95%（髪の毛の間も除去）
- 細部処理: 過度に細かい部分は不要

**最適化ポイント**:
- FP16推論（メモリ節約、速度2倍）
- バッチサイズ1（リアルタイム性重視）
- 前処理の並列化

---

### 3. D-ID最適化パイプライン

#### Q6: アスペクト比補正
**決定**: **D) AIによる自動判断（顔基準）+ 背景処理**

**実装ロジック**:
```python
def optimize_aspect_ratio(image, background_image=None):
    # 1. 顔検出（OpenCV Face Detection）
    face_rect = detect_face(image)

    # 2. 推奨比率選択（D-ID: 9:16 or 16:9）
    target_ratio = choose_ratio(image.width, image.height)

    # 3. 背景処理分岐
    if background_image:
        # 背景画像あり: 拡大・縮小で推奨比率に調整
        background = resize_to_ratio(background_image, target_ratio)
        result = composite(image, background, face_rect)
    else:
        # 背景画像なし: 白パディング
        result = add_padding(image, target_ratio, color=(255, 255, 255))

    return result
```

**処理フロー**:
```
1. 顔検出（OpenCV or MediaPipe）
   ↓
2. 顔を基準に最適なクロップ位置計算
   ↓
3. 背景処理
   ├─ 背景画像あり → Smart Resize（顔位置維持）
   └─ 背景画像なし → 白パディング
   ↓
4. D-ID推奨比率（9:16 or 16:9）に変換
```

---

#### Q7: D-ID品質最適化
**決定**: **A) フル最適化（ただし解像度アップは除外）**

**最適化項目**:
| 項目 | 実施 | 処理時間 |
|------|------|---------|
| 解像度アップスケール | ❌ **除外** | 0秒 |
| シャープネス調整 | ✅ **実施** | +0.5秒 |
| ノイズ除去 | ✅ **実施** | +1.0秒 |
| 明るさ・コントラスト | ✅ **実施** | +0.5秒 |
| **合計処理時間** | | **+2.0秒** |

**実装コード**:
```python
def optimize_image_quality(image):
    # 1. シャープネス調整（Unsharp Mask）
    image = cv2.filter2D(image, -1, unsharp_mask_kernel)

    # 2. ノイズ除去（Non-local Means Denoising）
    image = cv2.fastNlMeansDenoisingColored(image, h=10)

    # 3. 明るさ・コントラスト補正（CLAHE）
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0).apply(lab[:,:,0])
    image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return image
    # 注: 解像度アップスケールは実施しない
```

---

### 4. 自然な口調（プロソディ調整）

#### Q8: プロソディ調整
**決定**: **A) 完全自動（お祝いメッセージ特化）**

**設計仕様**:
```python
class CelebrationProsodyAdjuster:
    """お祝いメッセージ用プロソディ調整"""

    def __init__(self):
        self.style = {
            "mood": "cheerful",          # 明るい
            "energy": "high",             # ハキハキ
            "pause_emphasis": "strong"    # ポーズ重視
        }

    def adjust(self, text, audio):
        # 1. テキスト解析（空白・区切り文字検出）
        pause_positions = self._detect_pause_markers(text)

        # 2. ピッチ変動（明るく）
        audio = self._adjust_pitch(audio, shift=+20)  # Hz

        # 3. エネルギー変動（ハキハキ）
        audio = self._adjust_energy(audio, boost=1.2)

        # 4. ポーズ挿入（強調）
        audio = self._insert_pauses(audio, pause_positions, duration=0.3)

        # 5. 話速調整（やや速め）
        audio = self._adjust_speed(audio, rate=1.1)

        return audio

    def _detect_pause_markers(self, text):
        """空白文字や区切り文字でポーズ位置を検出"""
        markers = [' ', '、', '。', '！', '？', '\n']
        positions = []
        for i, char in enumerate(text):
            if char in markers:
                positions.append(i)
        return positions
```

**ポーズ挿入ルール**:
| 区切り文字 | ポーズ長 | 例 |
|-----------|---------|-----|
| 空白 ` ` | 0.2秒 | "お誕生日 おめでとう" |
| 読点 `、` | 0.3秒 | "今日は、特別な日" |
| 句点 `。` | 0.5秒 | "おめでとうございます。」 |
| 改行 `\n` | 0.4秒 | "メッセージ\n次の行" |
| 感嘆符 `！` | 0.6秒 | "おめでとう！」 |

**音声特性**:
- **ピッチ**: +20Hz（明るく）
- **エネルギー**: +20%（ハキハキ）
- **話速**: 1.1倍（やや速め、明るい印象）
- **ポーズ**: 強調（聞き取りやすさ重視）

---

## 🟡 IMPORTANT 要件（設計への影響）

### 5. BGM統合

#### Q9: BGMライブラリ管理
**決定**: **D) ハイブリッド（システム5曲 + ユーザーアップロード）**

**BGM要件**:
- **システム内蔵**: お祝い用BGM 5曲
  - ジャンル: 明るい、ポップ、オーケストラ、アコースティック
  - ソース: 著作権フリー音源サイト（開発時にWeb調査）
  - フォーマット: MP3（128kbps）
  - 長さ: 30-90秒ループ

**推奨BGMソース**:
1. **Pixabay Music** (https://pixabay.com/music/)
2. **Incompetech** (https://incompetech.com/)
3. **YouTube Audio Library**
4. **Free Music Archive**

**検索キーワード**:
- "celebration music"
- "happy birthday background"
- "cheerful acoustic"
- "upbeat orchestral"
- "positive corporate"

**実装仕様**:
```
data/bgm/
├── system/
│   ├── celebration_01.mp3  # オーケストラ風
│   ├── celebration_02.mp3  # アコースティック
│   ├── celebration_03.mp3  # ポップ
│   ├── celebration_04.mp3  # ピアノ
│   └── celebration_05.mp3  # ジャズ
└── user_uploads/
    └── [ユーザーアップロードBGM]
```

---

#### Q10: BGMダッキング
**決定**: **B) 不要（常に一定音量）**

**音量設定**:
```python
# 音声とBGMの音量バランス
VOICE_VOLUME = 1.0      # 100%（基準）
BGM_VOLUME = 0.2        # 20%（音声の邪魔にならない）
```

**実装**:
```python
def mix_audio(voice_audio, bgm_audio):
    # BGMを固定音量に設定（ダッキングなし）
    bgm_normalized = bgm_audio * 0.2  # 20%

    # 音声とBGMをミックス
    final_audio = voice_audio + bgm_normalized

    # クリッピング防止
    final_audio = np.clip(final_audio, -1.0, 1.0)

    return final_audio
```

---

#### Q11: 多言語対応
**決定**: **A) 日本語のみ（当面対応不要）**

**影響**:
- VOICEVOX、OpenVoice V2の日本語特化
- UI/エラーメッセージも日本語のみ
- 将来的な拡張は考慮しない

---

#### Q12: エラーハンドリング
**決定**: **C) ユーザー選択（リトライ/キャンセル）**

**エラーメッセージ仕様**:

```javascript
// ケース1: 人物検出失敗
{
  title: "人物が検出できませんでした",
  message: "画像に人物の顔が含まれていない可能性があります。\n別の画像を試してください。",
  actions: [
    { label: "別の画像を選択", action: "reupload" },
    { label: "キャンセル", action: "cancel" }
  ]
}

// ケース2: 背景除去失敗
{
  title: "背景除去に失敗しました",
  message: "画像処理中にエラーが発生しました。\n再度お試しください。",
  actions: [
    { label: "リトライ", action: "retry" },
    { label: "キャンセル", action: "cancel" }
  ]
}

// ケース3: D-ID APIエラー
{
  title: "動画生成に失敗しました",
  message: "D-ID APIとの通信でエラーが発生しました。\n（エラーコード: 429 - レート制限）",
  actions: [
    { label: "リトライ", action: "retry" },
    { label: "キャンセル", action: "cancel" }
  ]
}
```

**実装パターン**:
```typescript
interface ErrorDialogProps {
  title: string;
  message: string;
  onRetry?: () => void;
  onCancel: () => void;
  showRetry: boolean;
}

const ErrorDialog: React.FC<ErrorDialogProps> = ({
  title,
  message,
  onRetry,
  onCancel,
  showRetry
}) => {
  return (
    <Dialog>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>{message}</DialogContent>
      <DialogActions>
        {showRetry && (
          <Button onClick={onRetry} color="primary">
            リトライ
          </Button>
        )}
        <Button onClick={onCancel} color="secondary">
          キャンセル
        </Button>
      </DialogActions>
    </Dialog>
  );
};
```

---

#### Q13: プログレス表示
**決定**: **B) パーセンテージ表示**

**実装仕様**:
```typescript
interface ProgressState {
  currentStep: string;
  percentage: number;
  totalSteps: number;
  currentStepIndex: number;
}

// 処理ステップと所要時間
const PROCESSING_STEPS = [
  { name: "画像をアップロード中", weight: 5 },      // 5%
  { name: "人物を検出中", weight: 10 },             // 10%
  { name: "背景を除去中", weight: 20 },             // 20%
  { name: "画像を最適化中", weight: 15 },           // 15%
  { name: "音声を合成中", weight: 20 },             // 20%
  { name: "動画を生成中", weight: 30 }              // 30%
];

// UI表示
<ProgressBar>
  <LinearProgress value={percentage} />
  <Typography>{currentStep}... {percentage}%</Typography>
</ProgressBar>
```

**更新タイミング**:
```python
async def generate_video(image, text, voice_profile):
    total_steps = 6

    # Step 1
    await update_progress(1, 6, "画像をアップロード中")
    image_url = await upload_image(image)

    # Step 2
    await update_progress(2, 6, "人物を検出中")
    persons = await detect_persons(image_url)

    # Step 3
    await update_progress(3, 6, "背景を除去中")
    segmented = await remove_background(image_url, persons[0])

    # ... 以降同様
```

---

#### Q14: キャッシング戦略
**決定**: **C) キャッシュなし（常に最新生成）**

**影響**:
- シンプルな実装（キャッシュ管理不要）
- ストレージコスト削減
- 毎回最新の結果を生成（品質保証）

**削除される実装**:
- ~~画像ハッシュ計算~~
- ~~キャッシュキー管理~~
- ~~キャッシュ有効期限~~
- ~~キャッシュクリーンアップ~~

**処理フロー**:
```
1. ユーザーリクエスト
   ↓
2. 常に新規生成（キャッシュチェックなし）
   ↓
3. 結果を返す
   ↓
4. 一時ファイル削除（即座）
```

---

## 🟢 NICE TO HAVE 要件（スコープ外）

### スコープから除外される機能

| 機能 | 決定 | 影響 |
|------|------|------|
| Q15: バッチ処理 | ❌ 不要 | -2週間（実装工数削減） |
| Q16: テンプレート | ❌ 不要 | -1週間 |
| Q17: 動画編集 | ❌ 不要 | -3週間 |
| Q18: 呼吸音挿入 | △ 条件付き | D-ID非関与なら実装 |

**工数削減**: 合計 **-6週間**（14週間 → 8週間に短縮可能）

---

### Q18: 音声改善（条件付き実装）

**決定**: **B) 呼吸音の挿入**（D-ID関与なしの場合のみ）

**技術調査が必要**:
1. D-IDが音声処理にどこまで関与しているか？
2. OpenVoice V2の出力音声にD-IDが手を加えるか？
3. 呼吸音挿入のタイミング（D-ID前 or 後）

**実装方針**:
```python
# Case A: D-ID前に呼吸音挿入可能
voice = synthesize_voice(text, profile)
voice_with_breath = insert_breath_sounds(voice, pause_positions)
video = d_id_generate(image, voice_with_breath)  # OK

# Case B: D-IDが音声を再処理する場合
voice = synthesize_voice(text, profile)
video = d_id_generate(image, voice)  # D-IDが音声を変更
# → 呼吸音挿入は無効化される → 実装不可
```

**判断基準**:
- D-IDのドキュメント確認
- 実験的に呼吸音入り音声でテスト
- 最終動画で呼吸音が保持されているか検証

**対応不可の場合**: スコープから除外、工数影響なし

---

## 📈 工数・スケジュールへの影響

### 元の計画（Trinitas分析）
**総工数**: 14週間（448時間）

### 要件明確化後の調整

#### 工数削減要因
| 項目 | 削減工数 | 理由 |
|------|---------|------|
| 解像度アップスケール除外 | -8時間 | 実装不要 |
| キャッシング不要 | -16時間 | 実装・管理コスト削減 |
| バッチ処理除外 | -80時間 | 機能削除 |
| テンプレート除外 | -40時間 | 機能削除 |
| 動画編集除外 | -120時間 | 機能削除 |
| 多言語対応除外 | -60時間 | 日本語のみ |
| **削減合計** | **-324時間** | |

#### 工数追加要因
| 項目 | 追加工数 | 理由 |
|------|---------|------|
| AIベースアスペクト比補正 | +12時間 | 顔検出 + Smart Resize |
| プロソディ完全自動化 | +20時間 | お祝い特化チューニング |
| BGM Web調査・選定 | +8時間 | 5曲選定とライセンス確認 |
| エラーダイアログUI | +8時間 | リトライ/キャンセル実装 |
| パーセンテージ進捗表示 | +6時間 | WebSocket/SSE実装 |
| **追加合計** | **+54時間** | |

### 最終工数見積もり

**調整後総工数**: 448 - 324 + 54 = **178時間（約5.6週間）**

**削減率**: 60%削減（14週間 → 5.6週間）

---

## 🎯 次のステップ

### Phase 1: 詳細設計書の作成（今から）
1. 技術仕様書の作成
2. API設計書の作成
3. UI/UXワイヤーフレーム
4. データベーススキーマ設計（必要に応じて）

### Phase 2: 技術検証（3-5日）
5. BiRefNet on EC2のセットアップ
6. プロソディ調整アルゴリズムのPoC
7. BGM選定（Web調査）

### Phase 3: 実装開始準備
8. EC2起動とセットアップ
9. 開発環境の構築
10. タスク分割とスプリント計画

---

## 📊 要件の優先順位マトリックス

### Must Have（必須実装）

| 機能 | 優先度 | 工数 | 依存関係 |
|------|--------|------|---------|
| 複数人物選択UI | P0 | 16h | YOLOv8 |
| BiRefNet統合 | P0 | 24h | EC2 GPU |
| D-ID最適化パイプライン | P0 | 20h | OpenCV |
| プロソディ調整 | P0 | 20h | OpenVoice |
| BGM統合 | P1 | 16h | pydub |
| エラーハンドリング | P1 | 8h | - |
| プログレス表示 | P1 | 6h | WebSocket |

### Could Have（条件付き）

| 機能 | 条件 | 工数 |
|------|------|------|
| 呼吸音挿入 | D-ID非関与 | 8h |

### Won't Have（実装しない）

- バッチ処理
- テンプレート機能
- 動画編集機能
- 多言語対応

---

## 🎨 UI/UXデザインガイドライン

### デザイン原則
1. **シンプルさ**: 1画面で完結、最小ステップ
2. **視認性**: パーセンテージで進捗を明示
3. **日本語**: すべてのUI・エラーメッセージを日本語化
4. **レスポンシブ**: デスクトップ・モバイル両対応

### カラーパレット（お祝いテーマ）
```css
--primary-color: #FF6B9D;      /* ピンク（お祝い） */
--secondary-color: #FFA500;    /* オレンジ（明るい） */
--success-color: #4CAF50;      /* 緑（完了） */
--error-color: #F44336;        /* 赤（エラー） */
--background-color: #FFF9F0;   /* アイボリー（温かみ） */
```

---

## 📝 技術スタック確定

### フロントエンド
- **Framework**: React 19
- **UI Library**: Material-UI v5
- **State Management**: React Context + Hooks
- **Progress**: WebSocket (Socket.IO)

### バックエンド
- **Framework**: FastAPI
- **Image Processing**: BiRefNet, OpenCV, PIL
- **Voice Processing**: OpenVoice V2, Parselmouth
- **Audio Mixing**: pydub, FFmpeg

### インフラ
- **Compute**: EC2 g4dn.xlarge (Tesla T4 GPU)
- **Storage**: Local filesystem（キャッシュなし）
- **Deployment**: Docker Compose

---

**作成日**: 2025-11-02
**最終更新**: 2025-11-02
**ステータス**: ✅ 要件確定
**次のステップ**: 詳細設計書作成
