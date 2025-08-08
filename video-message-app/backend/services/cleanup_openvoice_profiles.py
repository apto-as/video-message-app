#!/usr/bin/env python3
"""
OpenVoiceプロファイルのクリーンアップスクリプト
削除されたはずのプロファイルを整理
"""

import asyncio
import json
from pathlib import Path
import shutil

async def cleanup_openvoice_profiles():
    """不要なOpenVoiceプロファイルを削除"""
    
    # パス設定
    project_root = Path(__file__).parents[2]
    metadata_path = project_root / "data" / "backend" / "storage" / "voices" / "voices_metadata.json"
    profiles_dir = project_root / "data" / "backend" / "storage" / "voices" / "profiles"
    
    # 削除対象プロファイル（テスト用プロファイル）
    profiles_to_remove = [
        "openvoice_dd7ae9c7",    # test-direct-clone
        "openvoice_2226c9f8",    # test-existing-samples-clone
        "openvoice_76be75b2",    # test-existing-samples
        "openvoice_2479015f",    # test-existing-samples-clone
        "openvoice_f5d2b70c",    # test-existing-samples-clone
        "openvoice_9f2ed134",    # test-direct-clone
        "openvoice_0fca0b40",    # imoto-test-voice05 (embedding_pathがnull)
        "openvoice_61f49144",    # imoto-test-voice07 (embedding_pathがnull)
    ]
    
    print("OpenVoiceプロファイルクリーンアップ")
    print("=" * 50)
    
    # メタデータファイルを読み込み
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    else:
        print("✗ メタデータファイルが見つかりません")
        return
    
    print(f"現在のプロファイル数: {len(metadata['profiles'])}")
    print("\n削除対象プロファイル:")
    
    deleted_count = 0
    
    for profile_id in profiles_to_remove:
        if profile_id in metadata["profiles"]:
            profile_name = metadata["profiles"][profile_id].get("name", "Unknown")
            print(f"  - {profile_id}: {profile_name}")
            
            # メタデータから削除
            del metadata["profiles"][profile_id]
            
            # プロファイルディレクトリを削除
            profile_dir = profiles_dir / profile_id
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
                print(f"    ✓ ディレクトリ削除: {profile_dir}")
            
            deleted_count += 1
    
    # 有効なプロファイルの確認
    print("\n\n残るプロファイル:")
    for profile_id, profile_data in metadata["profiles"].items():
        name = profile_data.get("name", "Unknown")
        embedding_path = profile_data.get("embedding_path")
        status = "✓ 有効" if embedding_path else "⚠️ 埋め込みなし"
        print(f"  - {profile_id}: {name} [{status}]")
    
    # メタデータファイルを保存
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ クリーンアップ完了")
    print(f"  削除数: {deleted_count}")
    print(f"  残りのプロファイル数: {len(metadata['profiles'])}")

if __name__ == "__main__":
    asyncio.run(cleanup_openvoice_profiles())