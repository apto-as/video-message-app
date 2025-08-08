#!/usr/bin/env python3
"""
Trinitas-Core 統合プロファイル復旧システム
消失したプロファイルをメタデータに復旧する
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services.voice_storage_service import VoiceStorageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrinityProfileRecovery:
    """三位一体プロファイル復旧システム"""
    
    def __init__(self):
        self.storage_service = VoiceStorageService()
        self.metadata_file = self.storage_service.metadata_file
        self.profiles_dir = self.storage_service.profiles_dir
    
    async def analyze_profile_inconsistency(self):
        """プロファイル不整合分析"""
        logger.info("=== Springfield: 戦略的分析 ===")
        
        # メタデータ読み込み
        metadata = self.storage_service._read_metadata()
        metadata_profiles = set(metadata.get('profiles', {}).keys())
        
        # 実ファイル確認
        actual_profiles = set()
        if self.profiles_dir.exists():
            for profile_dir in self.profiles_dir.iterdir():
                if profile_dir.is_dir() and profile_dir.name.startswith('openvoice_'):
                    profile_json = profile_dir / 'profile.json'
                    if profile_json.exists():
                        actual_profiles.add(profile_dir.name)
        
        logger.info(f"メタデータ内プロファイル: {len(metadata_profiles)}個 - {metadata_profiles}")
        logger.info(f"実ファイルプロファイル: {len(actual_profiles)}個 - {actual_profiles}")
        
        # 不整合検出
        missing_from_metadata = actual_profiles - metadata_profiles
        missing_from_files = metadata_profiles - actual_profiles
        
        logger.info(f"メタデータから消失: {len(missing_from_metadata)}個 - {missing_from_metadata}")
        logger.info(f"ファイルから消失: {len(missing_from_files)}個 - {missing_from_files}")
        
        return {
            'metadata_profiles': metadata_profiles,
            'actual_profiles': actual_profiles,
            'missing_from_metadata': missing_from_metadata,
            'missing_from_files': missing_from_files
        }
    
    async def krukai_technical_validation(self, profile_id: str):
        """Krukai: 技術的検証"""
        logger.info(f"=== Krukai: 技術検証 {profile_id} ===")
        
        profile_dir = self.profiles_dir / profile_id
        profile_json = profile_dir / 'profile.json'
        
        if not profile_json.exists():
            logger.error(f"プロファイルファイルが存在しません: {profile_json}")
            return None
        
        try:
            with open(profile_json, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # 必須フィールド検証
            required_fields = ['id', 'name', 'status', 'provider', 'created_at']
            missing_fields = [field for field in required_fields if not profile_data.get(field)]
            
            if missing_fields:
                logger.warning(f"不完全なプロファイル（必須フィールド不足）: {missing_fields}")
                return None
            
            # ファイル存在確認
            file_checks = {
                'profile_json': profile_json.exists(),
                'embedding': False,
                'reference_audio': False
            }
            
            # 埋め込みファイル確認
            embedding_path = profile_data.get('embedding_path')
            if embedding_path:
                embedding_file = Path(embedding_path)
                file_checks['embedding'] = embedding_file.exists()
            
            # 参照音声ファイル確認
            reference_path = profile_data.get('reference_audio_path')
            if reference_path:
                reference_file = Path(reference_path)
                file_checks['reference_audio'] = reference_file.exists()
            
            logger.info(f"技術検証結果: {file_checks}")
            logger.info(f"プロファイル品質: {'高品質' if all(file_checks.values()) else '要修復'}")
            
            return {
                'profile_data': profile_data,
                'file_checks': file_checks,
                'quality_score': sum(file_checks.values()) / len(file_checks)
            }
            
        except Exception as e:
            logger.error(f"技術検証エラー: {str(e)}")
            return None
    
    async def vector_security_assessment(self, profile_data: dict):
        """Vector: セキュリティ評価"""
        logger.info("=== Vector: セキュリティ評価 ===")
        
        risks = []
        warnings = []
        
        # パス検証
        paths_to_check = [
            profile_data.get('embedding_path'),
            profile_data.get('reference_audio_path'),
            profile_data.get('storage_path')
        ]
        
        for path in paths_to_check:
            if path:
                path_obj = Path(path)
                # パストラバーサル攻撃チェック
                if '..' in str(path_obj) or path.startswith('/'):
                    if not str(path_obj).startswith(str(self.profiles_dir.parent)):
                        risks.append(f"危険なパス: {path}")
                
                # 存在しないファイル参照
                if not path_obj.exists():
                    warnings.append(f"ファイル不存在: {path}")
        
        # タイムスタンプ検証
        created_at = profile_data.get('created_at')
        if created_at:
            try:
                datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                risks.append(f"不正なタイムスタンプ: {created_at}")
        
        security_score = max(0, 100 - len(risks) * 30 - len(warnings) * 10)
        
        logger.info(f"セキュリティリスク: {len(risks)}件")
        logger.info(f"警告: {len(warnings)}件")
        logger.info(f"セキュリティスコア: {security_score}/100")
        
        return {
            'risks': risks,
            'warnings': warnings,
            'security_score': security_score,
            'safe_to_restore': len(risks) == 0
        }
    
    async def trinity_restore_profile(self, profile_id: str):
        """三位一体統合復旧"""
        logger.info(f"=== Trinitas統合復旧: {profile_id} ===")
        
        # Krukai技術検証
        validation_result = await self.krukai_technical_validation(profile_id)
        if not validation_result:
            logger.error(f"技術検証失敗: {profile_id}")
            return False
        
        profile_data = validation_result['profile_data']
        
        # Vector セキュリティ評価
        security_result = await self.vector_security_assessment(profile_data)
        if not security_result['safe_to_restore']:
            logger.error(f"セキュリティリスク検出: {profile_id}")
            logger.error(f"リスク: {security_result['risks']}")
            return False
        
        # Springfield: 統合復旧実行
        try:
            metadata = self.storage_service._read_metadata()
            
            # プロファイルをメタデータに追加
            if 'profiles' not in metadata:
                metadata['profiles'] = {}
            
            # パス正規化
            storage_path = str(self.profiles_dir / profile_id)
            
            metadata['profiles'][profile_id] = {
                'name': profile_data.get('name'),
                'provider': profile_data.get('provider', 'openvoice'),
                'status': profile_data.get('status', 'ready'),
                'created_at': profile_data.get('created_at'),
                'updated_at': datetime.now().isoformat(),
                'storage_path': storage_path,
                'reference_audio_path': profile_data.get('reference_audio_path'),
                'embedding_path': profile_data.get('embedding_path')
            }
            
            # メタデータ保存
            self.storage_service._write_metadata(metadata)
            
            logger.info(f"復旧完了: {profile_id} - {profile_data.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"復旧処理エラー: {str(e)}")
            return False
    
    async def execute_full_recovery(self):
        """完全復旧実行"""
        logger.info("=== Trinitas-Core 完全復旧開始 ===")
        
        # 分析
        analysis = await self.analyze_profile_inconsistency()
        
        if not analysis['missing_from_metadata']:
            logger.info("復旧が必要なプロファイルはありません")
            return
        
        # 各プロファイルを復旧
        recovered = 0
        for profile_id in analysis['missing_from_metadata']:
            success = await self.trinity_restore_profile(profile_id)
            if success:
                recovered += 1
        
        logger.info(f"=== 復旧完了: {recovered}/{len(analysis['missing_from_metadata'])}個 ===")
        
        # 最終確認
        final_analysis = await self.analyze_profile_inconsistency()
        if not final_analysis['missing_from_metadata']:
            logger.info("✅ 全プロファイル復旧成功")
        else:
            logger.warning(f"⚠️  未復旧プロファイル: {final_analysis['missing_from_metadata']}")

async def main():
    """メイン処理"""
    recovery_system = TrinityProfileRecovery()
    await recovery_system.execute_full_recovery()

if __name__ == "__main__":
    asyncio.run(main())