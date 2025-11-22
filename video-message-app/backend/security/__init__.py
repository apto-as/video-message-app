"""
Security modules for Video Message App
音声処理のセキュリティ検証

Modules:
- audio_validator: 音声ファイル検証、オーディオボム検出
- prosody_validator: Prosodyパラメータ検証、NaN/Inf検出
- resource_limiter: リソース制限、並列処理管理
- error_handler: セキュアなエラーハンドリング
"""

from .audio_validator import AudioValidator
from .prosody_validator import ProsodyValidator
from .resource_limiter import (
    ResourceLimiter,
    voice_clone_limiter,
    voice_synthesis_limiter,
    prosody_adjustment_limiter,
    get_all_limiters,
    get_system_metrics
)
from .error_handler import SecureErrorHandler, handle_generic_error

__all__ = [
    # Audio Validation
    'AudioValidator',

    # Prosody Validation
    'ProsodyValidator',

    # Resource Management
    'ResourceLimiter',
    'voice_clone_limiter',
    'voice_synthesis_limiter',
    'prosody_adjustment_limiter',
    'get_all_limiters',
    'get_system_metrics',

    # Error Handling
    'SecureErrorHandler',
    'handle_generic_error'
]
