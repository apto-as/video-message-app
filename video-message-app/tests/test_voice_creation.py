#!/usr/bin/env python3
"""
音声クローン作成の詳細テスト
"""

import asyncio
import sys
from pathlib import Path
import tempfile

# バックエンドパスを追加
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from services.openvoice_hybrid_client import OpenVoiceHybridClient

async def test_voice_creation():
    """音声クローン作成の詳細テスト"""
    
    print("=== 音声クローン作成詳細テスト ===")
    
    # テスト用音声ファイルを作成（サイレント音声）
    import wave
    import struct
    
    test_files = []
    for i in range(3):
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        test_files.append(temp_file.name)
        
        # 1秒間のサイレント音声を作成
        sample_rate = 22050
        duration = 1.0
        frames = int(duration * sample_rate)
        
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2) 
            wav_file.setframerate(sample_rate)
            
            # サイレント音声データ
            for frame in range(frames):
                wav_file.writeframes(struct.pack('<h', 0))
        
        print(f"テスト音声ファイル作成: {temp_file.name}")
    
    try:
        async with OpenVoiceHybridClient() as client:
            
            print(f"\n1. ネイティブサービス利用可能: {client.is_native_available}")
            
            if not client.is_native_available:
                print("❌ ネイティブサービス利用不可 - テスト中止")
                return
            
            print("\n2. 音声クローン作成テスト開始...")
            
            try:
                result = await client.create_voice_clone(
                    name="test-voice",
                    audio_paths=test_files,
                    language="ja",
                    profile_id="test_profile_001"
                )
                
                print("✅ 音声クローン作成成功")
                print(f"   結果: {result}")
                
                if result.get('fallback_mode'):
                    print("⚠️  フォールバックモードで実行されました")
                else:
                    print("✅ ネイティブサービスで正常実行")
                
            except Exception as e:
                print(f"❌ 音声クローン作成エラー: {str(e)}")
                import traceback
                traceback.print_exc()
    
    finally:
        # テストファイル削除
        for test_file in test_files:
            try:
                Path(test_file).unlink()
            except Exception:
                pass
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_voice_creation())