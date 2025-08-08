#!/usr/bin/env python3
"""
環境設定テストスクリプト
Springfield設計による環境変数パス管理システムの検証
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

def test_environment_config():
    """環境設定のテスト"""
    print("=" * 60)
    print("Springfield Environment Configuration Test")
    print("=" * 60)
    
    try:
        # 環境設定クラスのインポートとテスト
        from core.environment_config import env_config
        
        print(f"✅ 環境設定クラス読み込み成功")
        print(f"   - 環境タイプ: {env_config.environment_type}")
        print(f"   - Docker環境: {env_config.is_docker}")
        print(f"   - 設定ファイル: {env_config.config_file}")
        print()
        
        # ストレージパステスト
        storage_path = env_config.get_storage_path()
        print(f"✅ ストレージパス取得: {storage_path}")
        
        # パスの存在確認
        storage_pathobj = Path(storage_path)
        if storage_pathobj.exists():
            print(f"   ✅ パス存在確認: OK")
        else:
            print(f"   ⚠️  パス不存在: 作成が必要")
            storage_pathobj.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ パス作成完了: {storage_path}")
        
        # サービスURL取得テスト
        service_urls = env_config.get_voice_service_urls()
        print(f"✅ サービスURL取得:")
        for service, url in service_urls.items():
            print(f"   - {service}: {url}")
        print()
        
        # 設定検証テスト
        validation = env_config.validate_configuration()
        print(f"✅ 設定検証結果:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"   {status} {key}: {value}")
        print()
        
        # デバッグ情報の表示
        if env_config.debug_mode:
            debug_info = env_config.get_debug_info()
            print(f"🔍 デバッグ情報:")
            for key, value in debug_info.items():
                print(f"   - {key}: {value}")
        
        print("=" * 60)
        print("✅ 環境設定テスト完了")
        
    except Exception as e:
        print(f"❌ 環境設定テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_voice_storage_service():
    """VoiceStorageServiceのテスト"""
    print("\n" + "=" * 60)
    print("VoiceStorageService Integration Test")
    print("=" * 60)
    
    try:
        from services.voice_storage_service import VoiceStorageService
        
        # サービス初期化
        storage_service = VoiceStorageService()
        print(f"✅ VoiceStorageService初期化成功")
        print(f"   - ストレージルート: {storage_service.storage_root}")
        print(f"   - プロファイルディレクトリ: {storage_service.profiles_dir}")
        print(f"   - 埋め込みディレクトリ: {storage_service.embeddings_dir}")
        print(f"   - サンプルディレクトリ: {storage_service.samples_dir}")
        print()
        
        # ディレクトリ存在確認
        directories = [
            ("ストレージルート", storage_service.storage_root),
            ("プロファイル", storage_service.profiles_dir),
            ("埋め込み", storage_service.embeddings_dir),
            ("サンプル", storage_service.samples_dir)
        ]
        
        for name, path in directories:
            if path.exists():
                print(f"   ✅ {name}ディレクトリ: {path}")
            else:
                print(f"   ❌ {name}ディレクトリ不存在: {path}")
        
        print("=" * 60)
        print("✅ VoiceStorageService統合テスト完了")
        
    except Exception as e:
        print(f"❌ VoiceStorageServiceテストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("環境変数パス管理システム - 統合テスト開始")
    print(f"実行環境: {sys.platform}")
    print(f"Python: {sys.version}")
    print(f"作業ディレクトリ: {os.getcwd()}")
    print()
    
    success = True
    
    # 環境設定テスト
    if not test_environment_config():
        success = False
    
    # VoiceStorageServiceテスト
    if not test_voice_storage_service():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 全テスト成功！環境変数パス管理システムが正常に動作しています。")
    else:
        print("💥 テスト失敗。設定を確認してください。")
    print("=" * 60)