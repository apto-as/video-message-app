#!/usr/bin/env python3
"""
Trinitas-Core メタデータ同期システム
分散したプロファイルとメタデータを統合する
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
import sys

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrinityMetadataSync:
    """三位一体メタデータ同期システム"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        
        # 2つのストレージ場所
        self.backend_storage = self.project_root / "backend" / "storage" / "voices"
        self.data_storage = self.project_root / "data" / "backend" / "storage" / "voices"
        
        # メタデータファイル
        self.backend_metadata = self.backend_storage / "voices_metadata.json"
        self.data_metadata = self.data_storage / "voices_metadata.json"
        
        # プロファイルディレクトリ
        self.backend_profiles = self.backend_storage / "profiles"
        self.data_profiles = self.data_storage / "profiles"
    
    def read_metadata(self, metadata_file: Path) -> dict:
        """メタデータ読み込み"""
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"profiles": {}}
    
    def write_metadata(self, metadata_file: Path, data: dict):
        """メタデータ書き込み"""
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def springfield_strategic_analysis(self):
        """Springfield: 戦略的分析"""
        logger.info("=== Springfield: 戦略的分析 ===")
        
        # 両方のストレージ状況を確認
        backend_exists = self.backend_storage.exists()
        data_exists = self.data_storage.exists()
        
        logger.info(f"Backend storage: {backend_exists} - {self.backend_storage}")
        logger.info(f"Data storage: {data_exists} - {self.data_storage}")
        
        # メタデータ確認
        backend_metadata = self.read_metadata(self.backend_metadata)
        data_metadata = self.read_metadata(self.data_metadata)
        
        backend_profiles = set(backend_metadata.get('profiles', {}).keys())
        data_profiles = set(data_metadata.get('profiles', {}).keys())
        
        logger.info(f"Backend メタデータプロファイル: {len(backend_profiles)}個 - {backend_profiles}")
        logger.info(f"Data メタデータプロファイル: {len(data_profiles)}個 - {data_profiles}")
        
        # 実ファイル確認
        backend_actual = set()
        data_actual = set()
        
        if self.backend_profiles.exists():
            for profile_dir in self.backend_profiles.iterdir():
                if profile_dir.is_dir() and (profile_dir / "profile.json").exists():
                    backend_actual.add(profile_dir.name)
        
        if self.data_profiles.exists():
            for profile_dir in self.data_profiles.iterdir():
                if profile_dir.is_dir() and (profile_dir / "profile.json").exists():
                    data_actual.add(profile_dir.name)
        
        logger.info(f"Backend 実ファイル: {len(backend_actual)}個 - {backend_actual}")
        logger.info(f"Data 実ファイル: {len(data_actual)}個 - {data_actual}")
        
        return {
            'backend_metadata': backend_metadata,
            'data_metadata': data_metadata,
            'backend_actual': backend_actual,
            'data_actual': data_actual,
            'all_profiles': backend_actual | data_actual | backend_profiles | data_profiles
        }
    
    async def krukai_technical_migration(self, analysis_result: dict):
        """Krukai: 技術的統合"""
        logger.info("=== Krukai: 技術的統合 ===")
        
        # 統合メタデータを作成
        unified_metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "profiles": {}
        }
        
        # 既存メタデータをマージ
        for source_name, metadata in [
            ("backend", analysis_result['backend_metadata']),
            ("data", analysis_result['data_metadata'])
        ]:
            for profile_id, profile_data in metadata.get('profiles', {}).items():
                if profile_id not in unified_metadata['profiles']:
                    unified_metadata['profiles'][profile_id] = profile_data
                    logger.info(f"メタデータ統合: {profile_id} from {source_name}")
        
        # 実ファイルから不足プロファイルを復元
        for profile_dir_path in [self.backend_profiles, self.data_profiles]:
            if not profile_dir_path.exists():
                continue
                
            for profile_dir in profile_dir_path.iterdir():
                if not profile_dir.is_dir():
                    continue
                    
                profile_id = profile_dir.name
                profile_json = profile_dir / "profile.json"
                
                if not profile_json.exists():
                    continue
                
                if profile_id in unified_metadata['profiles']:
                    continue
                
                # プロファイルデータ読み込み
                try:
                    with open(profile_json, 'r', encoding='utf-8') as f:
                        profile_data = json.load(f)
                    
                    # メタデータ用に簡略化
                    unified_metadata['profiles'][profile_id] = {
                        'name': profile_data.get('name', f'recovered-{profile_id}'),
                        'provider': profile_data.get('provider', 'openvoice'),
                        'status': profile_data.get('status', 'ready'),
                        'created_at': profile_data.get('created_at', datetime.now().isoformat()),
                        'updated_at': datetime.now().isoformat(),
                        'storage_path': str(profile_dir),
                        'reference_audio_path': profile_data.get('reference_audio_path'),
                        'embedding_path': profile_data.get('embedding_path')
                    }
                    
                    logger.info(f"実ファイルから復元: {profile_id} - {profile_data.get('name')}")
                    
                except Exception as e:
                    logger.error(f"プロファイル復元エラー {profile_id}: {str(e)}")
        
        logger.info(f"統合完了: {len(unified_metadata['profiles'])}個のプロファイル")
        return unified_metadata
    
    async def vector_security_validation(self, unified_metadata: dict):
        """Vector: セキュリティ検証"""
        logger.info("=== Vector: セキュリティ検証 ===")
        
        risks = []
        warnings = []
        validated_profiles = {}
        
        for profile_id, profile_data in unified_metadata['profiles'].items():
            profile_risks = []
            profile_warnings = []
            
            # パス検証
            paths = [
                profile_data.get('storage_path'),
                profile_data.get('reference_audio_path'),
                profile_data.get('embedding_path')
            ]
            
            for path in paths:
                if not path:
                    continue
                    
                # パストラバーサル検証
                if '..' in path or path.startswith('/tmp'):
                    profile_risks.append(f"危険なパス: {path}")
                
                # ファイル存在確認
                if not Path(path).exists():
                    profile_warnings.append(f"ファイル不存在: {path}")
            
            # プロファイルID検証
            if not profile_id.startswith('openvoice_'):
                profile_risks.append(f"不正なプロファイルID: {profile_id}")
            
            # 必須フィールド確認
            required_fields = ['name', 'provider', 'status']
            for field in required_fields:
                if not profile_data.get(field):
                    profile_warnings.append(f"必須フィールド不足: {field}")
            
            # 安全なプロファイルのみ統合
            if not profile_risks:
                validated_profiles[profile_id] = profile_data
                if profile_warnings:
                    logger.warning(f"警告あり（継続）: {profile_id} - {profile_warnings}")
            else:
                logger.error(f"危険なプロファイル（除外）: {profile_id} - {profile_risks}")
                risks.extend(profile_risks)
            
            warnings.extend(profile_warnings)
        
        logger.info(f"検証完了: {len(validated_profiles)}/{len(unified_metadata['profiles'])}個が安全")
        logger.info(f"リスク: {len(risks)}件, 警告: {len(warnings)}件")
        
        return {
            'validated_profiles': validated_profiles,
            'risks': risks,
            'warnings': warnings,
            'security_score': max(0, 100 - len(risks) * 20 - len(warnings) * 5)
        }
    
    async def trinity_unified_deployment(self, validated_data: dict):
        """三位一体統合デプロイ"""
        logger.info("=== Trinitas統合デプロイ ===")
        
        # 最終統合メタデータ
        final_metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "profiles": validated_data['validated_profiles'],
            "metadata": {
                "sync_timestamp": datetime.now().isoformat(),
                "total_profiles": len(validated_data['validated_profiles']),
                "security_score": validated_data['security_score'],
                "trinitas_core_version": "2.0"
            }
        }
        
        # バックアップ作成
        backup_dir = self.backend_storage.parent / "backup" / f"metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        if self.backend_metadata.exists():
            shutil.copy2(self.backend_metadata, backup_dir / "backend_metadata.json")
        if self.data_metadata.exists():
            shutil.copy2(self.data_metadata, backup_dir / "data_metadata.json")
        
        logger.info(f"バックアップ作成: {backup_dir}")
        
        # 正規位置にメタデータ配置
        self.write_metadata(self.backend_metadata, final_metadata)
        logger.info(f"メタデータ配置: {self.backend_metadata}")
        
        # data/backend のメタデータも更新（互換性のため）
        self.write_metadata(self.data_metadata, final_metadata)
        logger.info(f"互換メタデータ更新: {self.data_metadata}")
        
        # 最終確認
        verification_metadata = self.read_metadata(self.backend_metadata)
        verification_count = len(verification_metadata.get('profiles', {}))
        
        logger.info(f"✅ 統合完了: {verification_count}個のプロファイルが利用可能")
        
        return {
            'success': True,
            'profile_count': verification_count,
            'backup_location': str(backup_dir),
            'primary_metadata': str(self.backend_metadata)
        }
    
    async def execute_full_sync(self):
        """完全同期実行"""
        logger.info("=== Trinitas-Core メタデータ同期開始 ===")
        
        try:
            # 1. Springfield: 戦略分析
            analysis = await self.springfield_strategic_analysis()
            
            # 2. Krukai: 技術統合
            unified_metadata = await self.krukai_technical_migration(analysis)
            
            # 3. Vector: セキュリティ検証
            validation_result = await self.vector_security_validation(unified_metadata)
            
            # 4. Trinity: 統合デプロイ
            deployment_result = await self.trinity_unified_deployment(validation_result)
            
            logger.info("=== 同期完了 ===")
            logger.info(f"プロファイル数: {deployment_result['profile_count']}")
            logger.info(f"バックアップ: {deployment_result['backup_location']}")
            logger.info(f"メタデータ: {deployment_result['primary_metadata']}")
            
            return deployment_result
            
        except Exception as e:
            logger.error(f"同期エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

async def main():
    """メイン処理"""
    sync_system = TrinityMetadataSync()
    result = await sync_system.execute_full_sync()
    
    if result['success']:
        logger.info("🌸 三位一体同期成功 - カフェ・ズッケロでお待ちしております")
    else:
        logger.error(f"❌ 同期失敗: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())