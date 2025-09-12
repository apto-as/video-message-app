#!/usr/bin/env python3
"""
既存の音声ファイルを使用したOpenVoice直接テスト
"""

import asyncio
import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "openvoice_native"))

from openvoice_service import OpenVoiceNativeService

async def test_with_existing_files():
    """既存の音声ファイルでOpenVoiceをテスト"""
    
    print("=== 既存音声ファイルによるOpenVoice直接テスト ===")
    
    # 既存の音声ファイルパス
    profile_dir = "/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/profiles/openvoice_25c3b29c"
    audio_files = [
        f"{profile_dir}/sample_01.wav",
        f"{profile_dir}/sample_02.wav", 
        f"{profile_dir}/sample_03.wav"
    ]
    
    # ファイル存在確認
    print("\n1. 音声ファイル確認:")
    for audio_file in audio_files:
        if Path(audio_file).exists():
            size = Path(audio_file).stat().st_size / 1024  # KB
            print(f"✅ {Path(audio_file).name}: {size:.1f} KB")
        else:
            print(f"❌ {Path(audio_file).name}: ファイルが見つかりません")
            return
    
    # サービス初期化
    service = OpenVoiceNativeService()
    
    print("\n2. OpenVoice Native Service初期化中...")
    success = await service.initialize()
    if not success:
        print("❌ サービス初期化失敗")
        return
    
    print("✅ サービス初期化成功")
    
    # 音声クローン作成テスト
    print("\n3. 音声クローン作成開始...")
    print("   名前: test-direct-clone")
    print("   言語: ja")
    print("   音声ファイル数: 3")
    
    try:
        # 音声ファイルを読み込み
        audio_data_list = []
        for audio_file in audio_files:
            with open(audio_file, 'rb') as f:
                audio_data_list.append(f.read())
        
        # クローン作成
        result = await service.create_voice_clone(
            name="test-direct-clone",
            audio_files=audio_data_list,
            language="ja"
        )
        
        print("\n4. 結果:")
        if result.success:
            print("✅ 音声クローン作成成功！")
            print(f"   プロファイルID: {result.voice_profile_id}")
            print(f"   メッセージ: {result.message}")
            
            # 音声合成テスト
            print("\n5. 音声合成テスト:")
            test_text = "こんにちは、OpenVoiceのテストです。正常に音声が生成されています。"
            
            synthesis_result = await service.synthesize_voice(
                text=test_text,
                voice_profile_id=result.voice_profile_id,
                language="ja",
                speed=1.0
            )
            
            if synthesis_result.success:
                print("✅ 音声合成成功！")
                print(f"   音声データサイズ: {len(synthesis_result.audio_data) if synthesis_result.audio_data else 0} bytes")
                
                # 音声データを保存
                if synthesis_result.audio_data:
                    import base64
                    audio_bytes = base64.b64decode(synthesis_result.audio_data)
                    output_file = project_root / "test_synthesized_voice.wav"
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
                    print(f"   合成音声保存: {output_file}")
            else:
                print("❌ 音声合成失敗")
                print(f"   エラー: {synthesis_result.error}")
                
        else:
            print("❌ 音声クローン作成失敗")
            print(f"   エラー: {result.error}")
            print(f"   メッセージ: {result.message}")
            
    except Exception as e:
        print(f"❌ エラー発生: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_with_existing_files())