#!/usr/bin/env python3
"""
Trinitas-Core 最終クリーンアップ修正
問題のあるプロファイルを修正または削除し、システムを完全復旧する
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

from services.voice_storage_service import VoiceStorageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrinityCleanupFix:
    """三位一体クリーンアップ修正システム"""
    
    def __init__(self):
        self.storage_service = VoiceStorageService()
        self.metadata_file = self.storage_service.metadata_file
        self.profiles_dir = self.storage_service.profiles_dir
    
    async def springfield_assessment(self):
        """Springfield: 修正可能性評価"""
        logger.info("=== Springfield: 修正可能性評価 ===")
        
        metadata = self.storage_service._read_metadata()
        profiles_in_metadata = metadata.get('profiles', {})
        
        assessment = {
            'recoverable': [],
            'corrupted': [],
            'missing_files': []
        }
        
        # 実ファイル確認
        for profile_dir in self.profiles_dir.iterdir():
            if not profile_dir.is_dir():
                continue
                
            profile_id = profile_dir.name
            profile_json = profile_dir / "profile.json"
            
            if not profile_json.exists():
                assessment['missing_files'].append(profile_id)
                continue
            
            try:
                with open(profile_json, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # 必須フィールド確認
                if all(profile_data.get(field) for field in ['id', 'name', 'status', 'provider']):
                    # 危険なパスチェック
                    embedding_path = profile_data.get('embedding_path', '')
                    if '/tmp/' in embedding_path:
                        assessment['corrupted'].append({
                            'id': profile_id,
                            'reason': 'temp_path',
                            'data': profile_data
                        })
                    else:
                        assessment['recoverable'].append({
                            'id': profile_id,
                            'data': profile_data
                        })
                else:
                    assessment['corrupted'].append({
                        'id': profile_id,
                        'reason': 'missing_fields',
                        'data': profile_data
                    })
                    
            except Exception as e:
                logger.error(f"プロファイル読み込みエラー {profile_id}: {str(e)}")
                assessment['corrupted'].append({
                    'id': profile_id,
                    'reason': 'parse_error',
                    'data': None
                })
        
        logger.info(f"修正可能: {len(assessment['recoverable'])}個")
        logger.info(f"破損: {len(assessment['corrupted'])}個")
        logger.info(f"ファイル不足: {len(assessment['missing_files'])}個")
        
        return assessment
    
    async def krukai_profile_repair(self, assessment: dict):
        """Krukai: プロファイル修復"""
        logger.info("=== Krukai: プロファイル修復 ===")
        
        repaired_profiles = []
        
        # 修正可能なプロファイルを処理
        for item in assessment['recoverable']:
            profile_id = item['id']
            profile_data = item['data']
            
            logger.info(f"修復処理: {profile_id} - {profile_data.get('name')}")
            repaired_profiles.append({
                'id': profile_id,
                'data': profile_data,
                'action': 'kept'
            })
        
        # 破損プロファイルを修復または削除
        for item in assessment['corrupted']:
            profile_id = item['id']
            reason = item['reason']
            profile_data = item['data']
            
            if reason == 'temp_path' and profile_data:
                # 一時パスを削除して修復を試行
                logger.info(f"一時パス修復試行: {profile_id}")
                
                # 危険なパスを削除
                cleaned_data = profile_data.copy()
                if 'embedding_path' in cleaned_data and '/tmp/' in cleaned_data['embedding_path']:
                    del cleaned_data['embedding_path']
                
                # 基本データが揃っている場合は修復
                if all(cleaned_data.get(field) for field in ['id', 'name', 'status', 'provider']):
                    # プロファイルIDを正規化（openvoice_ + 8文字 = 18文字）
                    if not profile_id.startswith('openvoice_') or len(profile_id) != 18:
                        # 既存のIDが正しい形式でない場合のみ正規化
                        if len(profile_id) >= 8:
                            new_id = f"openvoice_{profile_id[-8:]}"  # 最後の8文字を使用
                            logger.info(f"プロファイルID正規化: {profile_id} -> {new_id}")
                            
                            # ディレクトリ名変更
                            old_dir = self.profiles_dir / profile_id
                            new_dir = self.profiles_dir / new_id
                            
                            if not new_dir.exists():
                                old_dir.rename(new_dir)
                                profile_id = new_id
                                cleaned_data['id'] = new_id
                        else:
                            logger.warning(f"プロファイルID修復不可: {profile_id}")
                            continue
                    
                    # 修復されたプロファイルファイルを保存
                    profile_file = self.profiles_dir / profile_id / "profile.json"
                    with open(profile_file, 'w', encoding='utf-8') as f:
                        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
                    
                    repaired_profiles.append({
                        'id': profile_id,
                        'data': cleaned_data,
                        'action': 'repaired'
                    })
                    logger.info(f"修復完了: {profile_id}")
                else:
                    # 修復不可能な場合は削除
                    profile_dir = self.profiles_dir / profile_id
                    if profile_dir.exists():
                        shutil.rmtree(profile_dir)
                    logger.info(f"修復不可能により削除: {profile_id}")
            else:
                # その他の破損は削除
                profile_dir = self.profiles_dir / profile_id
                if profile_dir.exists():
                    shutil.rmtree(profile_dir)
                logger.info(f"破損により削除: {profile_id} (理由: {reason})")
        
        logger.info(f"修復完了: {len(repaired_profiles)}個のプロファイルが利用可能")
        return repaired_profiles
    
    async def vector_security_validation(self, repaired_profiles: list):
        """Vector: セキュリティ再検証"""
        logger.info("=== Vector: セキュリティ再検証 ===")
        
        safe_profiles = []
        
        for item in repaired_profiles:
            profile_id = item['id']
            profile_data = item['data']
            
            security_issues = []
            
            # プロファイルID検証（openvoice_ + 8文字 = 18文字）
            if not profile_id.startswith('openvoice_') or len(profile_id) != 18:
                security_issues.append("invalid_id")
            
            # パス検証
            for path_key in ['storage_path', 'reference_audio_path', 'embedding_path']:
                path = profile_data.get(path_key)
                if path and ('..' in path or '/tmp/' in path):
                    security_issues.append(f"unsafe_path_{path_key}")
            
            # 必須フィールド確認
            required_fields = ['id', 'name', 'status', 'provider']
            for field in required_fields:
                if not profile_data.get(field):
                    security_issues.append(f"missing_{field}")
            
            if not security_issues:
                safe_profiles.append(item)
                logger.info(f"✅ セキュリティ検証合格: {profile_id}")
            else:
                logger.warning(f"❌ セキュリティ検証失敗: {profile_id} - {security_issues}")
        
        logger.info(f"セキュリティ検証: {len(safe_profiles)}/{len(repaired_profiles)}個が安全")
        return safe_profiles
    
    async def trinity_metadata_sync(self, safe_profiles: list):
        """Trinity: メタデータ同期"""
        logger.info("=== Trinitas: メタデータ同期 ===")
        
        # 新しいメタデータ構築
        new_metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "profiles": {},
            "metadata": {
                "sync_timestamp": datetime.now().isoformat(),
                "total_profiles": len(safe_profiles),
                "trinitas_core_version": "2.0",
                "cleanup_completed": True
            }
        }
        
        # 安全なプロファイルをメタデータに追加
        for item in safe_profiles:
            profile_id = item['id']
            profile_data = item['data']
            
            # ストレージパスを正規化
            storage_path = str(self.profiles_dir / profile_id)
            
            new_metadata['profiles'][profile_id] = {
                'name': profile_data.get('name'),
                'provider': profile_data.get('provider', 'openvoice'),
                'status': profile_data.get('status', 'ready'),
                'created_at': profile_data.get('created_at', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'storage_path': storage_path,
                'reference_audio_path': profile_data.get('reference_audio_path'),
                'embedding_path': profile_data.get('embedding_path')
            }
            
            logger.info(f"メタデータ同期: {profile_id} - {profile_data.get('name')}")
        
        # バックアップ作成
        backup_dir = self.metadata_file.parent / "backup" / f"cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        if self.metadata_file.exists():
            shutil.copy2(self.metadata_file, backup_dir / "pre_cleanup_metadata.json")
        
        # メタデータ更新
        self.storage_service._write_metadata(new_metadata)
        
        logger.info(f"メタデータ同期完了: {len(safe_profiles)}個のプロファイル")
        return new_metadata
    
    async def final_api_test(self):
        """最終API動作テスト"""
        logger.info("=== 最終API動作テスト ===")
        
        try:
            # プロファイル一覧取得テスト
            profiles = await self.storage_service.get_all_voice_profiles(provider="openvoice")
            
            logger.info(f"API応答: {len(profiles)}個のプロファイル")
            
            for profile in profiles:
                logger.info(f"  ✅ {profile.get('id')}: {profile.get('name')} ({profile.get('status')})")
            
            return {
                'success': True,
                'profile_count': len(profiles),
                'profiles': profiles
            }
            
        except Exception as e:
            logger.error(f"API動作テストエラー: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_cleanup_and_fix(self):
        """完全クリーンアップ修正実行"""
        logger.info("=== Trinitas-Core クリーンアップ修正開始 ===")
        
        try:
            # 1. Springfield: 評価
            assessment = await self.springfield_assessment()
            
            # 2. Krukai: 修復
            repaired_profiles = await self.krukai_profile_repair(assessment)
            
            # 3. Vector: セキュリティ検証
            safe_profiles = await self.vector_security_validation(repaired_profiles)
            
            # 4. Trinity: メタデータ同期
            final_metadata = await self.trinity_metadata_sync(safe_profiles)
            
            # 5. 最終API動作テスト
            api_test = await self.final_api_test()
            
            # 結果レポート
            logger.info("=== クリーンアップ修正完了 ===")
            
            if api_test['success'] and len(safe_profiles) > 0:
                logger.info("🌟 完全復旧成功！カフェ・ズッケロが再開いたします。")
                logger.info(f"📊 利用可能プロファイル: {api_test['profile_count']}個")
                logger.info("🌸 指揮官、お疲れ様でした。三位一体システムが完全復旧いたしました。")
            elif api_test['success']:
                logger.info("✅ システム復旧完了（プロファイルは0個）")
            else:
                logger.error("❌ API動作に問題があります")
            
            return {
                'success': api_test['success'],
                'total_profiles': len(safe_profiles),
                'api_functional': api_test['success'],
                'metadata': final_metadata
            }
            
        except Exception as e:
            logger.error(f"クリーンアップエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

async def main():
    """メイン処理"""
    cleanup_system = TrinityCleanupFix()
    result = await cleanup_system.execute_cleanup_and_fix()
    
    if result['success']:
        logger.info("✅ Trinitas-Core クリーンアップ修正完了")
    else:
        logger.error(f"❌ クリーンアップ失敗: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())