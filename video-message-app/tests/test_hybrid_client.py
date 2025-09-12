#!/usr/bin/env python3
"""
OpenVoice Hybrid Client テスト
"""

import asyncio
import sys
from pathlib import Path

# バックエンドパスを追加
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from services.openvoice_hybrid_client import OpenVoiceHybridClient

async def test_hybrid_client():
    """ハイブリッドクライアントのテスト"""
    
    print("=== OpenVoice Hybrid Client テスト ===")
    
    async with OpenVoiceHybridClient() as client:
        
        # サービス可用性チェック
        print("\n1. サービス可用性チェック")
        availability = await client.check_service_availability()
        print(f"   ネイティブサービス: {availability['native_service']}")
        print(f"   フォールバックモード: {availability['fallback_mode']}")
        print(f"   推奨アクション: {availability['recommended_action']}")
        
        # ネイティブサービス利用可能性
        print(f"\n2. ネイティブサービス利用可能: {client.is_native_available}")
        
        if not client.is_native_available:
            print("❌ ネイティブサービスが利用できません")
            print("   フォールバック処理が実行されます")
        else:
            print("✅ ネイティブサービス利用可能")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_hybrid_client())