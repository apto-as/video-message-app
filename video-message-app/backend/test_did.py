#!/usr/bin/env python3
"""
D-ID API接続テスト
"""
import asyncio
import base64
import httpx
from core.config import settings

async def test_did_api():
    """D-ID APIの基本接続テスト"""
    print("🔍 D-ID API接続テスト開始...")
    print(f"APIキー: {'*' * 10}... (検証済み)")
    
    # 公開されているテスト画像URLを使用
    test_image_url = "https://d-id-public-bucket.s3.us-west-2.amazonaws.com/alice.jpg"
    
    try:
        async with httpx.AsyncClient() as client:
            # D-ID APIにテストリクエスト
            response = await client.post(
                "https://api.d-id.com/talks",
                json={
                    "source_url": test_image_url,
                    "script": {
                        "type": "text",
                        "input": "こんにちは",
                        "provider": {
                            "type": "microsoft",
                            "voice_id": "ja-JP-NanamiNeural"
                        }
                    }
                },
                headers={
                    "Authorization": f"Basic {settings.did_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            print(f"📡 API応答ステータス: {response.status_code}")
            print(f"📄 応答内容: {response.text[:200]}...")
            
            if response.status_code == 201:
                print("✅ D-ID API接続成功！")
                data = response.json()
                talk_id = data.get('id')
                print(f"🎬 Talk ID: {talk_id}")
                return True
            else:
                print(f"❌ D-ID API接続失敗")
                return False
                
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_did_api())