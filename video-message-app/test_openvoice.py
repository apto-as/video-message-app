#!/usr/bin/env python3
"""
OpenVoice Native Service 直接テスト
"""

import asyncio
import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "openvoice_native"))

from openvoice_service import OpenVoiceNativeService

async def test_voice_synthesis():
    """音声合成の直接テスト"""
    
    print("=== OpenVoice Native Service 直接テスト ===")
    
    # サービス初期化
    service = OpenVoiceNativeService()
    
    print("1. サービス初期化中...")
    success = await service.initialize()
    if not success:
        print("❌ サービス初期化失敗")
        return
    
    print("✅ サービス初期化成功")
    
    # 既存の音声プロファイル確認
    print("\n2. 既存の音声プロファイル確認...")
    profiles_dir = service.config.voice_profiles_dir
    
    profile_dirs = [d for d in profiles_dir.iterdir() if d.is_dir()]
    if not profile_dirs:
        print("❌ 音声プロファイルが見つかりません")
        return
    
    for profile_dir in profile_dirs:
        profile_file = profile_dir / "profile.json"
        if profile_file.exists():
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                print(f"📁 プロファイル: {profile_data['id']} - {profile_data['name']}")
                print(f"   作成日時: {profile_data['created_at']}")
                print(f"   埋め込みパス: {profile_data['embedding_path']}")
                
                # 埋め込みファイルの存在確認
                embedding_path = Path(profile_data['embedding_path'])
                if embedding_path.exists():
                    print(f"   ✅ 埋め込みファイル存在")
                else:
                    print(f"   ❌ 埋め込みファイル未検出: {embedding_path}")
                    continue
                
                # 音声合成テスト
                print(f"\n3. 音声合成テスト: {profile_data['id']}")
                test_text = "こんにちは、これはOpenVoiceのテストです。"
                
                result = await service.synthesize_voice(
                    text=test_text,
                    voice_profile_id=profile_data['id'],
                    language="ja",
                    speed=1.0
                )
                
                if result.success:
                    print("✅ 音声合成成功")
                    print(f"   メッセージ: {result.message}")
                    print(f"   音声データサイズ: {len(result.audio_data) if result.audio_data else 0} bytes")
                    
                    # Base64音声データをファイルに保存してテスト
                    if result.audio_data:
                        import base64
                        audio_bytes = base64.b64decode(result.audio_data)
                        test_output = project_root / f"test_output_{profile_data['id']}.wav"
                        with open(test_output, 'wb') as f:
                            f.write(audio_bytes)
                        print(f"   テスト音声保存: {test_output}")
                    
                else:
                    print("❌ 音声合成失敗")
                    print(f"   エラー: {result.error}")
                    print(f"   メッセージ: {result.message}")
                
                break  # 最初のプロファイルでテスト
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_voice_synthesis())