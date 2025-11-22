"""
アプリケーション定数定義
マジックナンバーを排除し、保守性を向上
"""

# ==========================================
# ファイルサイズ制限（バイト）
# ==========================================

# 1MB = 1024 * 1024 bytes
MB = 1024 * 1024

# 画像ファイル
MAX_IMAGE_SIZE_BYTES = 10 * MB  # 10MB
MAX_IMAGE_SIZE_MB = 10

# 音声ファイル
MAX_AUDIO_SIZE_BYTES = 10 * MB  # 10MB
MAX_AUDIO_SIZE_MB = 10

# 一般ファイル（デフォルト）
MAX_FILE_SIZE_BYTES = 5 * MB  # 5MB
MAX_FILE_SIZE_MB = 5

# 大容量音声データ（API response等）
MAX_LARGE_AUDIO_SIZE_BYTES = 100 * MB  # 100MB
MAX_LARGE_AUDIO_SIZE_MB = 100

# ==========================================
# 音声合成パラメータ
# ==========================================

# 速度範囲
MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

# ピッチ範囲
MIN_PITCH = -0.15
MAX_PITCH = 0.15
DEFAULT_PITCH = 0.0

# 音量範囲
MIN_VOLUME = 0.0
MAX_VOLUME = 2.0
DEFAULT_VOLUME = 1.0

# ==========================================
# テキスト長制限
# ==========================================

MAX_TEXT_LENGTH = 1000  # 合成テキストの最大文字数
MAX_PROFILE_NAME_LENGTH = 100  # プロファイル名の最大文字数

# ==========================================
# タイムアウト設定（秒）
# ==========================================

OPENVOICE_REQUEST_TIMEOUT = 300  # OpenVoice API タイムアウト (5分)
VOICEVOX_REQUEST_TIMEOUT = 30    # VOICEVOX API タイムアウト (30秒)
DID_REQUEST_TIMEOUT = 120        # D-ID API タイムアウト (2分)

# ==========================================
# パス設定
# ==========================================

# ストレージディレクトリ名
VOICES_DIR = "voices"
OPENVOICE_DIR = "openvoice"
TEMP_DIR = "temp"
PROFILES_DIR = "profiles"

# メタデータファイル名
VOICES_METADATA_FILE = "voices_metadata.json"
PROFILE_METADATA_FILE = "profile.json"

# ==========================================
# API設定
# ==========================================

# リトライ設定
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# CORS
DEFAULT_CORS_ORIGINS = ["http://localhost:55434"]

# ==========================================
# ログ設定
# ==========================================

DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
