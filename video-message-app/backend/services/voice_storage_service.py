"""
音声ストレージサービス
音声プロファイルとクローンデータの安全な管理
"""

import json
import os
import aiofiles
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class VoiceStorageService:
    """音声プロファイルとクローンデータの管理サービス"""
    
    def __init__(self, storage_root: str = None):
        # 【Springfield改良】環境変数による統合パス管理システム
        if storage_root is None:
            from core.environment_config import env_config
            
            # 環境設定から取得
            current_file = Path(__file__).resolve()
            backend_root = current_file.parents[1]  # backend/services -> backend
            fallback_path = str(backend_root / "storage" / "voices")
            
            storage_root = env_config.get_storage_path(fallback_path)
            
            # デバッグ情報の出力
            if env_config.debug_mode:
                debug_info = env_config.get_debug_info()
                logger.info(f"環境設定情報: {debug_info}")
                
                validation = env_config.validate_configuration()
                logger.info(f"設定検証結果: {validation}")
            
            logger.info(f"ストレージパス確定: {storage_root} (環境: {env_config.environment_type})")
        
        self.storage_root = Path(storage_root)
        self.profiles_dir = self.storage_root / "profiles"
        self.embeddings_dir = self.storage_root / "embeddings"
        self.samples_dir = self.storage_root / "samples"
        self.metadata_file = self.storage_root / "voices_metadata.json"
        
        logger.info(f"VoiceStorageService初期化: {self.storage_root}")
        
        # ディレクトリ作成
        self._ensure_directories()
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        try:
            for directory in [self.storage_root, self.profiles_dir, 
                             self.embeddings_dir, self.samples_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # メタデータファイル初期化
            if not self.metadata_file.exists():
                self._write_metadata({
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "profiles": {}
                })
                
        except Exception as e:
            logger.error(f"ディレクトリ作成エラー: {str(e)}")
            raise
    
    def _write_metadata(self, data: Dict):
        """メタデータファイルを書き込み"""
        try:
            # 一時ファイルに書き込んでから置き換える（アトミック操作）
            temp_file = self.metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # ファイルを置き換え
            temp_file.replace(self.metadata_file)
            logger.info(f"メタデータファイル更新完了: {self.metadata_file}")
            
            # 書き込み確認
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                if profile_id := data.get('profiles', {}):
                    for pid in profile_id:
                        if pid in saved_data.get('profiles', {}):
                            logger.info(f"プロファイル {pid} の保存を確認")
                        else:
                            logger.error(f"プロファイル {pid} の保存に失敗")
                            
        except Exception as e:
            logger.error(f"メタデータ書き込みエラー: {str(e)}")
            raise
    
    def _read_metadata(self) -> Dict:
        """メタデータファイルを読み込み"""
        try:
            if not self.metadata_file.exists():
                return {"version": "1.0", "profiles": {}}
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"メタデータ読み込みエラー: {str(e)}")
            return {"version": "1.0", "profiles": {}}
    
    async def save_voice_profile(
        self, 
        profile_id: str, 
        profile_data: Dict[str, Any]
    ) -> str:
        """音声プロファイルを保存"""
        try:
            # プロファイルディレクトリ作成
            profile_dir = self.profiles_dir / profile_id
            profile_dir.mkdir(exist_ok=True)
            
            # プロファイルデータファイル
            profile_file = profile_dir / "profile.json"
            
            # データに追加情報を付与
            enhanced_data = {
                **profile_data,
                "storage_path": str(profile_dir),
                "updated_at": datetime.now().isoformat()
            }
            
            # プロファイルファイルを保存
            async with aiofiles.open(profile_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(enhanced_data, ensure_ascii=False, indent=2))
            
            # メタデータを更新
            metadata = self._read_metadata()
            
            # profilesキーが存在しない場合は初期化
            if "profiles" not in metadata:
                metadata["profiles"] = {}
                
            metadata["profiles"][profile_id] = {
                "name": profile_data.get("name"),
                "provider": profile_data.get("provider"),
                "status": profile_data.get("status"),
                "created_at": profile_data.get("created_at"),
                "updated_at": enhanced_data["updated_at"],
                "storage_path": str(profile_dir),
                "reference_audio_path": profile_data.get("reference_audio_path"),
                "embedding_path": profile_data.get("embedding_path")
            }
            
            logger.info(f"メタデータ更新: プロファイルID={profile_id}, パス={self.metadata_file}")
            self._write_metadata(metadata)
            
            logger.info(f"音声プロファイル保存完了: {profile_id}")
            return str(profile_file)
            
        except Exception as e:
            logger.error(f"プロファイル保存エラー: {str(e)}")
            raise
    
    async def get_voice_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """音声プロファイルを取得"""
        try:
            profile_file = self.profiles_dir / profile_id / "profile.json"
            
            if not profile_file.exists():
                return None
            
            async with aiofiles.open(profile_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                profile_data = json.loads(content)
                
                # 【緊急修正】パス正規化 - コンテナ内パスを実際のパスに変換
                if 'reference_audio_path' in profile_data:
                    original_path = profile_data['reference_audio_path']
                    if original_path and original_path.startswith('/app/storage'):
                        # /app/storage -> 実際のプロジェクトディレクトリに変換
                        local_path = original_path.replace('/app/storage/voices', str(self.storage_root))
                        if Path(local_path).exists():
                            profile_data['reference_audio_path'] = local_path
                            logger.info(f"パス正規化: {original_path} -> {local_path}")
                        else:
                            logger.warning(f"参照音声ファイルが見つかりません: {local_path}")
                
                return profile_data
                
        except Exception as e:
            logger.error(f"プロファイル取得エラー: {str(e)}")
            return None
    
    async def get_all_voice_profiles(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """全音声プロファイルを取得"""
        try:
            profiles = []
            metadata = self._read_metadata()
            
            for profile_id, profile_meta in metadata["profiles"].items():
                if provider and profile_meta.get("provider") != provider:
                    continue
                
                profile_data = await self.get_voice_profile(profile_id)
                if profile_data:
                    profiles.append(profile_data)
            
            return profiles
            
        except Exception as e:
            logger.error(f"プロファイル一覧取得エラー: {str(e)}")
            return []
    
    async def delete_voice_profile(self, profile_id: str) -> bool:
        """音声プロファイルを削除"""
        try:
            profile_dir = self.profiles_dir / profile_id
            deleted_files = False
            
            # メタデータを先に読み込み
            metadata = self._read_metadata()
            
            if not profile_dir.exists():
                logger.warning(f"プロファイルディレクトリが存在しません: {profile_dir}")
                # メタデータに存在する場合は続行
                if profile_id not in metadata.get("profiles", {}):
                    logger.error(f"プロファイル {profile_id} は存在しません")
                    return False
            
            # ディレクトリとファイルを削除（存在する場合）
            if profile_dir.exists():
                logger.info(f"プロファイルディレクトリ削除: {profile_dir}")
                shutil.rmtree(profile_dir)
                deleted_files = True
            
            # メタデータから削除
            if profile_id in metadata.get("profiles", {}):
                # 埋め込みパスを保存
                embedding_path = metadata["profiles"][profile_id].get("embedding_path")
                del metadata["profiles"][profile_id]
                self._write_metadata(metadata)
                logger.info(f"メタデータからプロファイル削除: {profile_id}")
            
            # 関連する埋め込みファイルも削除
            embedding_file = self.embeddings_dir / f"{profile_id}.pt"
            if embedding_file.exists():
                embedding_file.unlink()
                logger.info(f"埋め込みファイル削除: {embedding_file}")
            
            # ファイルもメタデータも削除されたか、またはメタデータから削除された場合は成功
            if deleted_files or profile_id not in metadata.get("profiles", {}):
                logger.info(f"音声プロファイル削除完了: {profile_id}")
                return True
            else:
                logger.error(f"プロファイル削除失敗: {profile_id}")
                return False
            
        except Exception as e:
            logger.error(f"プロファイル削除エラー: {str(e)}")
            return False
    
    async def save_voice_embedding(
        self, 
        profile_id: str, 
        embedding_data: bytes
    ) -> str:
        """音声埋め込みデータを保存"""
        try:
            embedding_file = self.embeddings_dir / f"{profile_id}.pt"
            
            async with aiofiles.open(embedding_file, 'wb') as f:
                await f.write(embedding_data)
            
            logger.info(f"音声埋め込み保存完了: {profile_id}")
            return str(embedding_file)
            
        except Exception as e:
            logger.error(f"埋め込み保存エラー: {str(e)}")
            raise
    
    async def get_voice_embedding(self, profile_id: str) -> Optional[bytes]:
        """音声埋め込みデータを取得"""
        try:
            embedding_file = self.embeddings_dir / f"{profile_id}.pt"
            
            if not embedding_file.exists():
                return None
            
            async with aiofiles.open(embedding_file, 'rb') as f:
                return await f.read()
                
        except Exception as e:
            logger.error(f"埋め込み取得エラー: {str(e)}")
            return None
    
    async def save_audio_samples(
        self, 
        profile_id: str, 
        audio_files: List[bytes],
        filenames: List[str]
    ) -> List[str]:
        """音声サンプルファイルを保存"""
        try:
            sample_dir = self.samples_dir / profile_id
            sample_dir.mkdir(exist_ok=True)
            
            saved_paths = []
            
            for i, (audio_data, filename) in enumerate(zip(audio_files, filenames)):
                # 安全なファイル名に変換
                safe_filename = f"sample_{i:02d}_{uuid.uuid4().hex[:8]}.wav"
                sample_file = sample_dir / safe_filename
                
                async with aiofiles.open(sample_file, 'wb') as f:
                    await f.write(audio_data)
                
                saved_paths.append(str(sample_file))
            
            logger.info(f"音声サンプル保存完了: {profile_id} ({len(saved_paths)}ファイル)")
            return saved_paths
            
        except Exception as e:
            logger.error(f"サンプル保存エラー: {str(e)}")
            raise
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """ストレージ使用状況を取得"""
        try:
            def get_dir_size(directory: Path) -> int:
                """ディレクトリサイズを取得"""
                total_size = 0
                if directory.exists():
                    for dirpath, dirnames, filenames in os.walk(directory):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)
                return total_size
            
            metadata = self._read_metadata()
            
            stats = {
                "total_profiles": len(metadata["profiles"]),
                "active_profiles": len([
                    p for p in metadata["profiles"].values() 
                    if p.get("status") == "ready"
                ]),
                "storage_size": {
                    "profiles": get_dir_size(self.profiles_dir),
                    "embeddings": get_dir_size(self.embeddings_dir),
                    "samples": get_dir_size(self.samples_dir),
                    "total": get_dir_size(self.storage_root)
                },
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"ストレージ統計エラー: {str(e)}")
            return {}
    
    async def cleanup_orphaned_files(self) -> Dict[str, int]:
        """孤立したファイルをクリーンアップ"""
        try:
            metadata = self._read_metadata()
            active_profiles = set(metadata["profiles"].keys())
            
            cleaned = {
                "profiles": 0,
                "embeddings": 0,
                "samples": 0
            }
            
            # 孤立したプロファイルディレクトリを削除
            if self.profiles_dir.exists():
                for profile_dir in self.profiles_dir.iterdir():
                    if profile_dir.is_dir() and profile_dir.name not in active_profiles:
                        shutil.rmtree(profile_dir)
                        cleaned["profiles"] += 1
            
            # 孤立した埋め込みファイルを削除
            if self.embeddings_dir.exists():
                for embedding_file in self.embeddings_dir.glob("*.pt"):
                    profile_id = embedding_file.stem
                    if profile_id not in active_profiles:
                        embedding_file.unlink()
                        cleaned["embeddings"] += 1
            
            # 孤立したサンプルディレクトリを削除
            if self.samples_dir.exists():
                for sample_dir in self.samples_dir.iterdir():
                    if sample_dir.is_dir() and sample_dir.name not in active_profiles:
                        shutil.rmtree(sample_dir)
                        cleaned["samples"] += 1
            
            logger.info(f"クリーンアップ完了: {cleaned}")
            return cleaned
            
        except Exception as e:
            logger.error(f"クリーンアップエラー: {str(e)}")
            return {"profiles": 0, "embeddings": 0, "samples": 0}