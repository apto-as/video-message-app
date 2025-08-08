#!/usr/bin/env python3
"""
生成された音声ファイルを新しいプロファイルとして登録
"""

import asyncio
import sys
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "openvoice_native"))

from openvoice_service import OpenVoiceNativeService

async def register_new_profile():
    """生成された音声ファイルを新しいプロファイルとして登録"""
    
    print("=== 音声プロファイル登録 ===")
    
    # 既存の音声ファイル（成功したクローン元）
    source_dir = "/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/profiles/openvoice_25c3b29c"
    audio_files = [
        f"{source_dir}/sample_01.wav",
        f"{source_dir}/sample_02.wav", 
        f"{source_dir}/sample_03.wav"
    ]
    
    # 新しいプロファイル設定
    profile_name = "imoto-test-voice02"
    profile_id = f"openvoice_{uuid.uuid4().hex[:8]}"
    
    print(f"プロファイル名: {profile_name}")
    print(f"プロファイルID: {profile_id}")
    
    # ファイル存在確認
    print("\n1. 元音声ファイル確認:")
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
    
    try:
        # 音声ファイルを読み込み
        audio_data_list = []
        for audio_file in audio_files:
            with open(audio_file, 'rb') as f:
                audio_data_list.append(f.read())
        
        print("\n3. 音声クローン作成開始...")
        
        # クローン作成
        result = await service.create_voice_clone(
            name=profile_name,
            audio_files=audio_data_list,
            language="ja"
        )
        
        print("\n4. 結果:")
        if result.success:
            print("✅ 音声クローン作成成功！")
            print(f"   プロファイルID: {result.voice_profile_id}")
            print(f"   メッセージ: {result.message}")
            
            # プロファイル情報をバックエンド形式で保存
            backend_profile_dir = Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/profiles") / result.voice_profile_id
            backend_profile_dir.mkdir(parents=True, exist_ok=True)
            
            # 音声ファイルをコピー
            saved_sample_paths = []
            for i, audio_file in enumerate(audio_files):
                dest_path = backend_profile_dir / f"sample_{i+1:02d}.wav"
                shutil.copy2(audio_file, dest_path)
                saved_sample_paths.append(str(dest_path))
                print(f"   音声ファイルコピー: sample_{i+1:02d}.wav")
            
            # 埋め込みファイルのパスを取得
            native_profile_dir = Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/profiles") / result.voice_profile_id
            embedding_files = list(Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/openvoice").glob("voice_clone_*.pkl"))
            latest_embedding = max(embedding_files, key=lambda x: x.stat().st_mtime) if embedding_files else None
            
            # バックエンド用プロファイル作成
            profile_data = {
                "id": result.voice_profile_id,
                "name": profile_name,
                "description": "生成されたクローン音声",
                "language": "ja",
                "created_at": datetime.now().isoformat(),
                "sample_count": 3,
                "status": "ready",
                "provider": "openvoice",
                "voice_type": "cloned",
                "embedding_path": str(latest_embedding) if latest_embedding else None,
                "reference_audio_path": saved_sample_paths[0],
                "sample_audio_paths": saved_sample_paths,
                "metadata": {
                    "sample_files": [f"sample_{i+1:02d}.wav" for i in range(3)],
                    "processing_time": 0.5,
                    "total_samples_saved": 3,
                    "source": "manual_registration"
                }
            }
            
            # プロファイル保存
            profile_file = backend_profile_dir / "profile.json"
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ バックエンド用プロファイル保存完了: {profile_file}")
            
            # テスト音声合成
            print("\n5. テスト音声合成:")
            test_text = "こんにちは、私は新しく登録されたimoto-test-voice02です。"
            
            synthesis_result = await service.synthesize_voice(
                text=test_text,
                voice_profile_id=result.voice_profile_id,
                language="ja",
                speed=1.0
            )
            
            if synthesis_result.success:
                print("✅ テスト音声合成成功！")
                
                # 音声データを保存
                if synthesis_result.audio_data:
                    import base64
                    audio_bytes = base64.b64decode(synthesis_result.audio_data)
                    output_file = project_root / f"test_{profile_name}_voice.wav"
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
                    print(f"   テスト音声保存: {output_file}")
            else:
                print("❌ テスト音声合成失敗")
                print(f"   エラー: {synthesis_result.error}")
            
        else:
            print("❌ 音声クローン作成失敗")
            print(f"   エラー: {result.error}")
            print(f"   メッセージ: {result.message}")
            
    except Exception as e:
        print(f"❌ エラー発生: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 登録完了 ===")

if __name__ == "__main__":
    asyncio.run(register_new_profile())