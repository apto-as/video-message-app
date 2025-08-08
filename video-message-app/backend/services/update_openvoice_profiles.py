#!/usr/bin/env python3
"""
OpenVoiceプロファイルをOpenVoice Native Serviceから取得して更新するスクリプト
"""

import asyncio
import requests
import json
from pathlib import Path

async def update_openvoice_profiles():
    """OpenVoice Native Serviceからプロファイルを取得してメタデータを更新"""
    
    # OpenVoice Native Service APIエンドポイント
    api_url = "http://localhost:8001/voice-clone/profiles"
    
    try:
        # プロファイル一覧を取得
        response = requests.get(api_url)
        if response.status_code == 200:
            profiles = response.json()
            print(f"✓ {len(profiles)} 個のプロファイルを取得しました")
            
            # メタデータファイルのパス
            metadata_path = Path(__file__).parents[2] / "data" / "backend" / "storage" / "voices" / "voices_metadata.json"
            
            # 既存のメタデータを読み込み
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = {"profiles": {}}
            
            # OpenVoiceプロファイルを更新
            for profile in profiles:
                profile_id = profile["id"]
                
                # Docker環境用のパスに変換
                storage_path = f"/app/storage/voices/profiles/{profile_id}"
                reference_audio_path = f"/app/storage/voices/profiles/{profile_id}/sample_01.wav"
                
                # 埋め込みパスも変換
                embedding_path = None
                if profile.get("embedding_path"):
                    # ローカルパスからDocker用パスに変換
                    embedding_filename = Path(profile["embedding_path"]).name
                    embedding_path = f"/app/storage/openvoice/{embedding_filename}"
                
                metadata["profiles"][profile_id] = {
                    "name": profile["name"],
                    "provider": "openvoice",
                    "status": profile.get("status", "ready"),
                    "created_at": profile.get("created_at"),
                    "updated_at": profile.get("created_at"),
                    "storage_path": storage_path,
                    "reference_audio_path": reference_audio_path,
                    "embedding_path": embedding_path,
                    "description": profile.get("description", profile["name"]),
                    "sample_count": profile.get("sample_count", 3),
                    "language": profile.get("language", "ja")
                }
                
                print(f"  - {profile_id}: {profile['name']}")
            
            # メタデータファイルを保存
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ メタデータファイルを更新しました: {metadata_path}")
            
        else:
            print(f"✗ プロファイル取得失敗: {response.status_code}")
            
    except Exception as e:
        print(f"✗ エラー: {str(e)}")

if __name__ == "__main__":
    print("OpenVoiceプロファイル更新スクリプト")
    print("=" * 40)
    asyncio.run(update_openvoice_profiles())