#!/usr/bin/env python3
"""
埋め込みパスを修正するスクリプト
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_embedding_paths():
    """埋め込みパスを修正"""
    
    # メタデータファイルパス
    metadata_file = Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/backend/storage/voices/voices_metadata.json")
    
    if not metadata_file.exists():
        logger.error(f"メタデータファイルが見つかりません: {metadata_file}")
        return
    
    # メタデータ読み込み
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    profiles = metadata.get('profiles', {})
    updated = False
    
    for profile_id, profile_data in profiles.items():
        # 現在のembedding_path
        current_path = profile_data.get('embedding_path')
        
        if current_path:
            # タイムスタンプから正しいパスを推測
            if '_20250802_173947.pkl' in current_path:
                # このタイムスタンプは17:39ですが、プロファイルの作成時刻は08:39
                # おそらくUTC/JSTの違い（9時間差）
                # プロファイルIDで確認
                if profile_id == 'openvoice_9f913e90':
                    # OpenVoice Native Serviceで作成されたファイルを探す
                    native_profile_dir = Path("/Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/data/openvoice_native/voice_profiles")
                    
                    # プロファイルを探す
                    if native_profile_dir.exists():
                        for dir_path in native_profile_dir.iterdir():
                            if dir_path.is_dir():
                                profile_file = dir_path / "profile.json"
                                if profile_file.exists():
                                    with open(profile_file, 'r', encoding='utf-8') as f:
                                        native_profile = json.load(f)
                                    
                                    # 名前で一致を確認
                                    if native_profile.get('name') == profile_data.get('name'):
                                        native_embedding_path = native_profile.get('embedding_path')
                                        if native_embedding_path:
                                            # Docker用パスに変換
                                            if '/storage/openvoice/' in native_embedding_path:
                                                path_parts = native_embedding_path.split('/storage/openvoice/')
                                                if len(path_parts) > 1:
                                                    new_path = f"/app/storage/openvoice/{path_parts[1]}"
                                                    profile_data['embedding_path'] = new_path
                                                    logger.info(f"修正: {profile_id} - {current_path} -> {new_path}")
                                                    updated = True
    
    # 更新された場合は保存
    if updated:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info("メタデータファイルを更新しました")
    else:
        logger.info("更新が必要なプロファイルはありませんでした")

if __name__ == "__main__":
    fix_embedding_paths()