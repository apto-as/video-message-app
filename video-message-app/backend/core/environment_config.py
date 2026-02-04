"""
環境設定管理ユーティリティ
Springfield設計による統合環境変数管理システム
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """環境変数の統合管理クラス"""
    
    _instance: Optional['EnvironmentConfig'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'EnvironmentConfig':
        """シングルトンパターンで実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """環境設定の初期化"""
        if not self._initialized:
            self._load_environment_config()
            self._initialized = True
    
    def _load_environment_config(self):
        """環境設定ファイルの読み込み"""
        try:
            # プロジェクトルートの取得
            current_file = Path(__file__).resolve()
            backend_root = current_file.parents[1]  # core -> backend
            
            # Docker環境判定
            is_docker = os.environ.get('DOCKER_ENV', '').lower() == 'true'
            
            # 適切な.envファイルの選択
            if is_docker:
                env_file = backend_root / ".env.docker"
                if not env_file.exists():
                    env_file = backend_root / ".env"
                self.environment_type = "docker"
                logger.info(f"Docker環境検出: {env_file}")
            else:
                env_file = backend_root / ".env"
                self.environment_type = "local"
                logger.info(f"ローカル環境検出: {env_file}")
            
            # 環境変数ファイル読み込み
            if env_file.exists():
                load_dotenv(env_file, override=True)
                self.config_file = str(env_file)
                logger.info(f"環境設定ファイル読み込み完了: {env_file}")
            else:
                self.config_file = None
                logger.warning(f"環境設定ファイルが見つかりません: {env_file}")
            
            # 基本設定の取得
            self._load_basic_config()
            
        except Exception as e:
            logger.error(f"環境設定読み込みエラー: {str(e)}")
            raise
    
    def _load_basic_config(self):
        """基本設定の読み込み"""
        # 環境タイプ
        self.is_docker = os.environ.get('DOCKER_ENV', '').lower() == 'true'
        
        # ストレージパス
        self.storage_root_path = os.environ.get('STORAGE_ROOT_PATH')
        
        # API設定
        self.did_api_key = os.environ.get('DID_API_KEY')
        self.voicevox_base_url = os.environ.get('VOICEVOX_BASE_URL', 'http://voicevox:50021' if self.is_docker else 'http://localhost:50021')
        # DEPRECATED: OpenVoice service has been replaced by Qwen3-TTS
        self.openvoice_api_url = os.environ.get('OPENVOICE_API_URL', 'http://host.docker.internal:8001' if self.is_docker else 'http://localhost:8001')
        
        # デバッグ設定
        self.debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() == 'true'
        self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
        
        logger.info(f"基本設定読み込み完了 - 環境: {self.environment_type}, Docker: {self.is_docker}")
    
    @property
    def is_docker_env(self) -> bool:
        """is_docker_envプロパティ（後方互換性のため）"""
        return self.is_docker
    
    def get_storage_path(self, fallback_path: Optional[str] = None) -> str:
        """ストレージパスの取得（フォールバック機能付き）"""
        if self.storage_root_path:
            return self.storage_root_path
        
        if fallback_path:
            logger.warning(f"STORAGE_ROOT_PATH未設定のため、フォールバックを使用: {fallback_path}")
            return fallback_path
        
        # デフォルトフォールバック
        if self.is_docker:
            default_path = "/app/storage/voices"
        else:
            backend_root = Path(__file__).resolve().parents[1]
            default_path = str(backend_root / "storage" / "voices")
        
        logger.warning(f"STORAGE_ROOT_PATH未設定のため、デフォルトを使用: {default_path}")
        return default_path
    
    def get_voice_service_urls(self) -> Dict[str, str]:
        """音声サービスURLの取得"""
        return {
            "voicevox": self.voicevox_base_url,
            # DEPRECATED: OpenVoice service replaced by Qwen3-TTS
            "openvoice": self.openvoice_api_url,
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """デバッグ情報の取得"""
        return {
            "environment_type": self.environment_type,
            "is_docker": self.is_docker,
            "config_file": self.config_file,
            "storage_root_path": self.storage_root_path,
            "voicevox_base_url": self.voicevox_base_url,
            "openvoice_api_url": self.openvoice_api_url,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level
        }
    
    def validate_configuration(self) -> Dict[str, bool]:
        """設定の検証"""
        validation_results = {
            "storage_path_set": bool(self.storage_root_path),
            "did_api_key_set": bool(self.did_api_key),
            "voicevox_url_set": bool(self.voicevox_base_url),
            "openvoice_url_set": bool(self.openvoice_api_url),  # DEPRECATED
            "config_file_exists": bool(self.config_file)
        }
        
        # ストレージパスの存在確認
        if self.storage_root_path:
            storage_path = Path(self.storage_root_path)
            validation_results["storage_path_exists"] = storage_path.exists()
            validation_results["storage_path_writable"] = storage_path.exists() and os.access(storage_path, os.W_OK)
        else:
            validation_results["storage_path_exists"] = False
            validation_results["storage_path_writable"] = False
        
        return validation_results

# グローバルインスタンス
env_config = EnvironmentConfig()