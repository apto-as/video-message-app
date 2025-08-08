#!/usr/bin/env python3
"""
OpenVoice Native Service クローニングテスト
既存の音声サンプルを使用してクローニング処理をテスト
"""

import asyncio
import aiofiles
import requests
import json
from pathlib import Path

async def test_voice_cloning():
    # 音声サンプルのパス
    sample_dir = Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/profiles/openvoice_0fca0b40")
    sample_files = [
        sample_dir / "sample_01.wav",
        sample_dir / "sample_02.wav", 
        sample_dir / "sample_03.wav"
    ]
    
    # 音声ファイルを読み込み
    audio_files = []
    for sample_file in sample_files:
        if sample_file.exists():
            async with aiofiles.open(sample_file, 'rb') as f:
                audio_data = await f.read()
                audio_files.append(audio_data)
                print(f"✓ 読み込み完了: {sample_file.name}")
        else:
            print(f"✗ ファイルが見つかりません: {sample_file}")
    
    if len(audio_files) != 3:
        print("エラー: 3つの音声サンプルが必要です")
        return
    
    # OpenVoice Native Service API エンドポイント
    api_url = "http://localhost:8001/voice-clone/create"
    
    # リクエストデータ準備
    files = []
    for i, audio_data in enumerate(audio_files):
        files.append(('audio_samples', (f'sample_{i+1}.wav', audio_data, 'audio/wav')))
    
    data = {
        'name': 'imoto-test-clone-fixed',
        'description': '修正後のクローニングテスト', 
        'language': 'ja'
    }
    
    print("\n🎯 クローニング処理を開始します...")
    print(f"   名前: {data['name']}")
    print(f"   説明: {data['description']}")
    print(f"   言語: {data['language']}")
    print(f"   サンプル数: {len(audio_files)}")
    
    try:
        # POSTリクエスト送信
        response = requests.post(api_url, data=data, files=files)
        
        print(f"\n📡 レスポンスステータス: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ クローニング成功!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get('voice_profile_id'):
                print(f"\n🆔 新しいプロファイルID: {result['voice_profile_id']}")
                
                # プロファイルの詳細を確認
                profile_id = result['voice_profile_id']
                profile_dir = Path(f"/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/openvoice/voice_profiles/{profile_id}")
                
                if profile_dir.exists():
                    profile_json = profile_dir / "profile.json"
                    if profile_json.exists():
                        async with aiofiles.open(profile_json, 'r') as f:
                            profile_data = json.loads(await f.read())
                            print("\n📄 プロファイル詳細:")
                            print(json.dumps(profile_data, indent=2, ensure_ascii=False))
                            
                            # embedding_pathの確認
                            if profile_data.get('embedding_path'):
                                print(f"\n✅ 埋め込みファイル: {profile_data['embedding_path']}")
                            else:
                                print("\n⚠️  埋め込みファイルが設定されていません")
        else:
            print("\n❌ クローニング失敗")
            print(f"エラー詳細: {response.text}")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("OpenVoice Native Service クローニングテスト")
    print("=" * 60)
    asyncio.run(test_voice_cloning())