#!/usr/bin/env python3
"""
パス解決のテストスクリプト
"""

import os
import sys
from pathlib import Path

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services.voice_storage_service import VoiceStorageService

def test_path_resolution():
    """パス解決のテスト"""
    
    print(f"環境変数 DOCKER_ENV: {os.environ.get('DOCKER_ENV', 'Not set')}")
    print(f"現在の作業ディレクトリ: {os.getcwd()}")
    print(f"スクリプトパス: {__file__}")
    
    # VoiceStorageService初期化
    storage_service = VoiceStorageService()
    
    print(f"\nVoiceStorageService パス:")
    print(f"storage_root: {storage_service.storage_root}")
    print(f"profiles_dir: {storage_service.profiles_dir}")
    print(f"存在確認: {storage_service.profiles_dir.exists()}")
    
    # プロファイルディレクトリの内容
    if storage_service.profiles_dir.exists():
        print(f"\nプロファイルディレクトリの内容:")
        for item in storage_service.profiles_dir.iterdir():
            print(f"  - {item.name}")
    
    # テストプロファイルのパス
    test_profile_id = "openvoice_9f913e90"
    profile_dir = storage_service.profiles_dir / test_profile_id
    print(f"\nテストプロファイルパス: {profile_dir}")
    print(f"存在確認: {profile_dir.exists()}")
    
    if profile_dir.exists():
        print(f"ディレクトリ内容:")
        for item in profile_dir.iterdir():
            print(f"  - {item.name}")

if __name__ == "__main__":
    test_path_resolution()