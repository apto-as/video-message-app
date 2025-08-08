import os
import uuid
import json
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import UploadFile
import mutagen
from mutagen import File as MutagenFile

class VoiceManager:
    def __init__(self, storage_path: str = "./storage/voices"):
        self.storage_path = Path(storage_path)
        self.metadata_file = self.storage_path / "voices_metadata.json"
        self._ensure_storage_directory()
        
    def _ensure_storage_directory(self):
        """ストレージディレクトリの作成"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # メタデータファイルが存在しない場合は作成
        if not self.metadata_file.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict:
        """メタデータファイルの読み込み"""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_metadata(self, metadata: Dict):
        """メタデータファイルの保存"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def validate_audio_file(self, file: UploadFile) -> Tuple[bool, str]:
        """音声ファイルのバリデーション"""
        # ファイル形式の確認
        supported_formats = [
            'audio/mpeg',     # MP3
            'audio/wav',      # WAV
            'audio/flac',     # FLAC
            'audio/mp4',      # MP4 audio / M4A
            'audio/m4a',      # M4A (alternative MIME type)
            'audio/x-m4a',    # M4A (alternative MIME type)
            'audio/aac'       # AAC (sometimes used for M4A)
        ]
        
        # MIMEタイプでの検証
        is_valid_mime = file.content_type in supported_formats
        
        # ファイル拡張子での補完検証
        file_extension = Path(file.filename).suffix.lower()
        supported_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.mp4', '.aac']
        is_valid_extension = file_extension in supported_extensions
        
        if not is_valid_mime and not is_valid_extension:
            return False, f"サポートされていないファイル形式です。対応形式: MP3, WAV, FLAC, M4A, MP4"
        
        # ファイルサイズの確認（10MB制限）
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size and file.size > max_size:
            return False, f"ファイルサイズが大きすぎます。最大{max_size // (1024*1024)}MBまで対応しています。"
        
        return True, ""
    
    async def save_audio_file(self, file: UploadFile, user_id: str = "default") -> Tuple[str, Dict]:
        """音声ファイルの保存"""
        # バリデーション
        is_valid, error_message = self.validate_audio_file(file)
        if not is_valid:
            raise ValueError(error_message)
        
        # ユニークIDの生成
        voice_id = str(uuid.uuid4())
        
        # ファイル拡張子の決定
        file_extension = self._get_file_extension(file.content_type)
        filename = f"{voice_id}{file_extension}"
        file_path = self.storage_path / filename
        
        # ファイルの保存
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 音声ファイルのメタデータ取得
        audio_info = self._get_audio_info(file_path)
        
        # メタデータの作成
        voice_metadata = {
            "voice_id": voice_id,
            "user_id": user_id,
            "original_filename": file.filename,
            "file_path": str(file_path),
            "upload_date": datetime.now().isoformat(),
            "file_size": len(content),
            "content_type": file.content_type,
            "duration": audio_info.get("duration", 0),
            "sample_rate": audio_info.get("sample_rate", 0),
            "did_voice_id": None,  # D-IDから返されるIDは後で設定
            "status": "uploaded"  # uploaded, processing, ready, error
        }
        
        # メタデータの保存
        metadata = self._load_metadata()
        metadata[voice_id] = voice_metadata
        self._save_metadata(metadata)
        
        return voice_id, voice_metadata
    
    def _get_file_extension(self, content_type: str) -> str:
        """コンテンツタイプから拡張子を取得"""
        extension_map = {
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/flac': '.flac',
            'audio/mp4': '.mp4',
            'audio/m4a': '.m4a'
        }
        return extension_map.get(content_type, '.mp3')
    
    def _get_audio_info(self, file_path: Path) -> Dict:
        """音声ファイルの情報を取得"""
        try:
            audio_file = MutagenFile(file_path)
            if audio_file is not None:
                return {
                    "duration": getattr(audio_file.info, 'length', 0),
                    "sample_rate": getattr(audio_file.info, 'sample_rate', 0),
                    "bitrate": getattr(audio_file.info, 'bitrate', 0)
                }
        except Exception as e:
            print(f"音声ファイル情報の取得に失敗: {e}")
        
        return {"duration": 0, "sample_rate": 0, "bitrate": 0}
    
    def get_voice_list(self, user_id: str = "default") -> List[Dict]:
        """ユーザーの音声リストを取得"""
        metadata = self._load_metadata()
        user_voices = [
            voice for voice in metadata.values() 
            if voice.get("user_id") == user_id
        ]
        
        # アップロード日時でソート（新しい順）
        user_voices.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        return user_voices
    
    def get_voice_metadata(self, voice_id: str) -> Optional[Dict]:
        """特定の音声のメタデータを取得"""
        metadata = self._load_metadata()
        return metadata.get(voice_id)
    
    def update_voice_metadata(self, voice_id: str, updates: Dict):
        """音声のメタデータを更新"""
        metadata = self._load_metadata()
        if voice_id in metadata:
            metadata[voice_id].update(updates)
            self._save_metadata(metadata)
    
    def delete_voice(self, voice_id: str, user_id: str = "default") -> bool:
        """音声の削除"""
        metadata = self._load_metadata()
        voice_data = metadata.get(voice_id)
        
        if not voice_data or voice_data.get("user_id") != user_id:
            return False
        
        # ファイルの削除
        try:
            file_path = Path(voice_data["file_path"])
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"ファイル削除エラー: {e}")
        
        # メタデータから削除
        del metadata[voice_id]
        self._save_metadata(metadata)
        
        return True
    
    def get_voice_file_path(self, voice_id: str) -> Optional[Path]:
        """音声ファイルのパスを取得"""
        voice_data = self.get_voice_metadata(voice_id)
        if voice_data:
            return Path(voice_data["file_path"])
        return None
    
    def get_storage_stats(self) -> Dict:
        """ストレージ使用状況を取得"""
        metadata = self._load_metadata()
        total_files = len(metadata)
        total_size = sum(voice.get("file_size", 0) for voice in metadata.values())
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }