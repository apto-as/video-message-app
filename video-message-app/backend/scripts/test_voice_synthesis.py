#!/usr/bin/env python3
"""
音声合成のテストスクリプト
"""

import asyncio
import logging
from pathlib import Path
import sys

# パスを追加
sys.path.append(str(Path(__file__).parent.parent))

from services.openvoice_hybrid_client import OpenVoiceHybridClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_voice_synthesis():
    """音声合成のテスト"""
    
    # テスト用プロファイル
    test_profile = {
        'id': 'openvoice_9f913e90',
        'name': 'woman-test-voice01',
        'reference_audio_path': '/app/storage/voices/profiles/openvoice_9f913e90/sample_01.wav'
    }
    
    # テストテキスト
    test_text = "こんにちは、テスト音声合成です。正しく動作することを確認します。"
    
    try:
        # クライアント初期化
        client = OpenVoiceHybridClient()
        
        # ヘルスチェック
        logger.info("ヘルスチェック実行...")
        health = await client.native_client.check_service_health()
        logger.info(f"Native Service健全性: {health}")
        
        if health:
            # 音声合成実行
            logger.info(f"音声合成実行: プロファイル={test_profile['id']}")
            result = await client.synthesize_with_clone(
                text=test_text,
                voice_profile=test_profile,
                language='ja'
            )
            
            if result:
                logger.info(f"音声合成成功: {len(result)} bytes")
                
                # ファイルに保存
                output_path = Path("/tmp/test_synthesis.wav")
                with open(output_path, 'wb') as f:
                    f.write(result)
                logger.info(f"音声ファイル保存: {output_path}")
            else:
                logger.error("音声合成失敗: 結果が空")
        else:
            logger.error("Native Serviceが利用できません")
            
    except Exception as e:
        logger.error(f"テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_voice_synthesis())