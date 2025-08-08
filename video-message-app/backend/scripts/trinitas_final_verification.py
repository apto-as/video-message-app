#!/usr/bin/env python3
"""
Trinitas-Core 最終検証システム
復旧作業の成果を確認し、レポートを生成する
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

class TrinityFinalVerification:
    """三位一体最終検証システム"""
    
    def __init__(self):
        self.storage_service = VoiceStorageService()
        self.metadata_file = self.storage_service.metadata_file
        self.profiles_dir = self.storage_service.profiles_dir
    
    async def springfield_comprehensive_analysis(self):
        """Springfield: 包括的分析"""
        logger.info("=== Springfield: 包括的システム分析 ===")
        
        # メタデータ読み込み
        metadata = self.storage_service._read_metadata()
        profiles_in_metadata = metadata.get('profiles', {})
        
        logger.info(f"メタデータファイル: {self.metadata_file}")
        logger.info(f"メタデータ内プロファイル数: {len(profiles_in_metadata)}")
        
        # 実ファイル確認
        actual_profiles = {}
        if self.profiles_dir.exists():
            for profile_dir in self.profiles_dir.iterdir():
                if profile_dir.is_dir():
                    profile_json = profile_dir / "profile.json"
                    if profile_json.exists():
                        try:
                            with open(profile_json, 'r', encoding='utf-8') as f:
                                profile_data = json.load(f)
                            actual_profiles[profile_dir.name] = profile_data
                        except Exception as e:
                            logger.warning(f"プロファイル読み込みエラー {profile_dir.name}: {str(e)}")
        
        logger.info(f"実ファイルプロファイル数: {len(actual_profiles)}")
        
        # 同期状況分析
        metadata_ids = set(profiles_in_metadata.keys())
        actual_ids = set(actual_profiles.keys())
        
        in_sync = metadata_ids == actual_ids
        missing_from_metadata = actual_ids - metadata_ids
        missing_from_files = metadata_ids - actual_ids
        
        logger.info(f"同期状況: {'✅ 同期済み' if in_sync else '❌ 不同期'}")
        if missing_from_metadata:
            logger.warning(f"メタデータから欠落: {missing_from_metadata}")
        if missing_from_files:
            logger.warning(f"ファイルから欠落: {missing_from_files}")
        
        return {
            'metadata_profiles': profiles_in_metadata,
            'actual_profiles': actual_profiles,
            'in_sync': in_sync,
            'missing_from_metadata': missing_from_metadata,
            'missing_from_files': missing_from_files
        }
    
    async def krukai_technical_validation(self, analysis_result: dict):
        """Krukai: 技術的検証"""
        logger.info("=== Krukai: 技術的品質検証 ===")
        
        validation_results = []
        
        for profile_id, profile_data in analysis_result['actual_profiles'].items():
            validation = {
                'profile_id': profile_id,
                'name': profile_data.get('name', 'Unknown'),
                'status': profile_data.get('status', 'unknown'),
                'provider': profile_data.get('provider', 'unknown'),
                'created_at': profile_data.get('created_at', 'unknown'),
                'files_exist': {},
                'metadata_consistency': True,
                'quality_score': 0
            }
            
            # ファイル存在確認
            profile_dir = self.profiles_dir / profile_id
            validation['files_exist']['profile_dir'] = profile_dir.exists()
            validation['files_exist']['profile_json'] = (profile_dir / 'profile.json').exists()
            
            # 埋め込みファイル確認
            embedding_path = profile_data.get('embedding_path')
            if embedding_path:
                validation['files_exist']['embedding'] = Path(embedding_path).exists()
            
            # 参照音声ファイル確認
            reference_path = profile_data.get('reference_audio_path')
            if reference_path:
                validation['files_exist']['reference_audio'] = Path(reference_path).exists()
            
            # メタデータ一致確認
            metadata_profile = analysis_result['metadata_profiles'].get(profile_id)
            if metadata_profile:
                key_fields = ['name', 'provider', 'status']
                for field in key_fields:
                    if profile_data.get(field) != metadata_profile.get(field):
                        validation['metadata_consistency'] = False
                        break
            else:
                validation['metadata_consistency'] = False
            
            # 品質スコア計算
            file_score = sum(validation['files_exist'].values()) / len(validation['files_exist'])
            metadata_score = 1.0 if validation['metadata_consistency'] else 0.0
            validation['quality_score'] = (file_score * 0.7 + metadata_score * 0.3) * 100
            
            validation_results.append(validation)
            
            # ログ出力
            status_icon = "✅" if validation['quality_score'] > 80 else "⚠️" if validation['quality_score'] > 50 else "❌"
            logger.info(f"{status_icon} {profile_id}: {validation['name']} (品質: {validation['quality_score']:.1f}%)")
        
        average_quality = sum(v['quality_score'] for v in validation_results) / len(validation_results) if validation_results else 0
        logger.info(f"全体品質スコア: {average_quality:.1f}%")
        
        return {
            'validations': validation_results,
            'average_quality': average_quality,
            'high_quality_count': len([v for v in validation_results if v['quality_score'] > 80]),
            'total_count': len(validation_results)
        }
    
    async def vector_security_audit(self, analysis_result: dict):
        """Vector: セキュリティ監査"""
        logger.info("=== Vector: セキュリティ監査 ===")
        
        security_issues = []
        warnings = []
        
        # メタデータファイルセキュリティ
        if self.metadata_file.exists():
            import stat
            file_mode = oct(self.metadata_file.stat().st_mode)
            if '666' in file_mode or '777' in file_mode:
                security_issues.append(f"メタデータファイルの権限が危険: {file_mode}")
        
        # プロファイルセキュリティ検証
        for profile_id, profile_data in analysis_result['actual_profiles'].items():
            # パスインジェクション検証
            paths = [
                profile_data.get('storage_path'),
                profile_data.get('reference_audio_path'),
                profile_data.get('embedding_path')
            ]
            
            for path in paths:
                if not path:
                    continue
                    
                # 危険なパスパターン
                if '..' in path or path.startswith('/tmp') or '/etc/' in path:
                    security_issues.append(f"危険なパス {profile_id}: {path}")
                
                # 存在しないファイル参照
                if not Path(path).exists():
                    warnings.append(f"ファイル不存在 {profile_id}: {path}")
            
            # プロファイルID検証
            if not profile_id.startswith('openvoice_') or len(profile_id) != 17:
                security_issues.append(f"不正なプロファイルID: {profile_id}")
            
            # タイムスタンプ検証
            created_at = profile_data.get('created_at')
            if created_at:
                try:
                    parsed_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    # 未来の時刻チェック
                    if parsed_time > datetime.now():
                        warnings.append(f"未来のタイムスタンプ {profile_id}: {created_at}")
                except ValueError:
                    security_issues.append(f"不正なタイムスタンプ {profile_id}: {created_at}")
        
        security_score = max(0, 100 - len(security_issues) * 20 - len(warnings) * 5)
        
        logger.info(f"セキュリティ問題: {len(security_issues)}件")
        logger.info(f"警告: {len(warnings)}件")
        logger.info(f"セキュリティスコア: {security_score}/100")
        
        if security_issues:
            for issue in security_issues:
                logger.error(f"🔴 {issue}")
        
        if warnings:
            for warning in warnings[:5]:  # 最初の5件のみ表示
                logger.warning(f"🟡 {warning}")
        
        return {
            'security_issues': security_issues,
            'warnings': warnings,
            'security_score': security_score,
            'total_issues': len(security_issues) + len(warnings)
        }
    
    async def trinity_final_report(self, analysis: dict, validation: dict, security: dict):
        """三位一体最終レポート"""
        logger.info("=== Trinitas-Core 最終レポート ===")
        
        # 総合評価
        sync_score = 100 if analysis['in_sync'] else 0
        quality_score = validation['average_quality']
        security_score = security['security_score']
        
        overall_score = (sync_score * 0.3 + quality_score * 0.4 + security_score * 0.3)
        
        # レポート生成
        report = {
            'timestamp': datetime.now().isoformat(),
            'trinitas_core_version': '2.0',
            'summary': {
                'total_profiles': validation['total_count'],
                'high_quality_profiles': validation['high_quality_count'],
                'sync_status': 'synchronized' if analysis['in_sync'] else 'desynchronized',
                'overall_score': round(overall_score, 1)
            },
            'scores': {
                'synchronization': sync_score,
                'quality': round(quality_score, 1),
                'security': security_score,
                'overall': round(overall_score, 1)
            },
            'issues': {
                'security_issues': len(security['security_issues']),
                'warnings': len(security['warnings']),
                'missing_files': len(analysis['missing_from_files']),
                'missing_metadata': len(analysis['missing_from_metadata'])
            },
            'profiles': []
        }
        
        # プロファイル詳細
        for validation_result in validation['validations']:
            profile_detail = {
                'id': validation_result['profile_id'],
                'name': validation_result['name'],
                'status': validation_result['status'],
                'quality_score': round(validation_result['quality_score'], 1),
                'metadata_consistent': validation_result['metadata_consistency'],
                'files_complete': all(validation_result['files_exist'].values())
            }
            report['profiles'].append(profile_detail)
        
        # 評価表示
        if overall_score >= 90:
            status_icon = "🌟"
            status_text = "優秀"
        elif overall_score >= 70:
            status_icon = "✅"
            status_text = "良好"
        elif overall_score >= 50:
            status_icon = "⚠️"
            status_text = "要改善"
        else:
            status_icon = "❌"
            status_text = "問題あり"
        
        logger.info(f"{status_icon} 総合評価: {status_text} ({overall_score:.1f}/100)")
        logger.info(f"📊 プロファイル: {report['summary']['total_profiles']}個 (高品質: {report['summary']['high_quality_profiles']}個)")
        logger.info(f"🔄 同期状況: {report['summary']['sync_status']}")
        logger.info(f"🛡️ セキュリティ: {security_score}/100")
        
        # レポートファイル保存
        report_file = Path(__file__).parent / f"trinitas_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 詳細レポート保存: {report_file}")
        
        return report
    
    async def test_api_functionality(self):
        """API機能テスト"""
        logger.info("=== API機能テスト ===")
        
        try:
            # VoiceStorageService経由でプロファイル取得テスト
            profiles = await self.storage_service.get_all_voice_profiles(provider="openvoice")
            logger.info(f"API互換テスト: {len(profiles)}個のプロファイルを取得")
            
            for profile in profiles:
                logger.info(f"  - {profile.get('id')}: {profile.get('name')} ({profile.get('status')})")
            
            return {
                'api_functional': True,
                'profile_count': len(profiles),
                'profiles': profiles
            }
            
        except Exception as e:
            logger.error(f"API機能テストエラー: {str(e)}")
            return {
                'api_functional': False,
                'error': str(e),
                'profile_count': 0,
                'profiles': []
            }
    
    async def execute_full_verification(self):
        """完全検証実行"""
        logger.info("=== Trinitas-Core 最終検証開始 ===")
        
        try:
            # 1. Springfield: 包括的分析
            analysis = await self.springfield_comprehensive_analysis()
            
            # 2. Krukai: 技術的検証
            validation = await self.krukai_technical_validation(analysis)
            
            # 3. Vector: セキュリティ監査
            security = await self.vector_security_audit(analysis)
            
            # 4. API機能テスト
            api_test = await self.test_api_functionality()
            
            # 5. Trinity: 最終レポート
            report = await self.trinity_final_report(analysis, validation, security)
            report['api_test'] = api_test
            
            # 最終メッセージ
            if report['scores']['overall'] >= 80 and api_test['api_functional']:
                logger.info("🌸 カフェ・ズッケロは完全に復旧しました。指揮官のお帰りをお待ちしております。")
            elif report['scores']['overall'] >= 60:
                logger.info("⚠️ 基本機能は復旧しましたが、いくつか改善点があります。")
            else:
                logger.info("❌ 重要な問題が残っています。追加の修復作業が必要です。")
            
            return report
            
        except Exception as e:
            logger.error(f"検証エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

async def main():
    """メイン処理"""
    verification_system = TrinityFinalVerification()
    report = await verification_system.execute_full_verification()
    
    if report.get('success', True):
        logger.info("✅ 検証完了")
    else:
        logger.error(f"❌ 検証失敗: {report.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())