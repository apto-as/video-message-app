#!/usr/bin/env python3
"""
プロファイル削除のテストスクリプト
"""

import asyncio
import logging
import sys
from pathlib import Path

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services.voice_storage_service import VoiceStorageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_delete_profile():
    """プロファイル削除のテスト"""
    
    # 削除するプロファイルID
    profile_id = "openvoice_1cc144c1"  # 実際に存在するプロファイル
    
    # VoiceStorageService初期化
    storage_service = VoiceStorageService()
    
    # 削除前の状態確認
    profile_dir = storage_service.profiles_dir / profile_id
    logger.info(f"削除前プロファイルディレクトリ: {profile_dir}")
    logger.info(f"存在確認: {profile_dir.exists()}")
    
    # 削除実行
    try:
        logger.info(f"プロファイル削除実行: {profile_id}")
        success = await storage_service.delete_voice_profile(profile_id)
        logger.info(f"削除結果: {success}")
    except Exception as e:
        logger.error(f"削除エラー: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 削除後の状態確認
    logger.info(f"削除後存在確認: {profile_dir.exists()}")

if __name__ == "__main__":
    asyncio.run(test_delete_profile())