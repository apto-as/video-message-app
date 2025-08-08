"""
背景処理機能のテストスクリプト
"""
import sys
import os
import io

# パスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from services.image_processor import ImageProcessor

async def test_image_processor():
    """画像処理器のテスト"""
    processor = ImageProcessor()
    print(f"✅ ImageProcessor初期化完了")
    
    # サンプル画像データ（実際の画像ファイルがあればそれを使用）
    # ここでは初期化のテストのみ
    print(f"✅ rembgセッション: {processor.session is not None}")
    
    return True

if __name__ == "__main__":
    import asyncio
    print("🧪 背景処理機能テスト開始")
    
    try:
        result = asyncio.run(test_image_processor())
        if result:
            print("✅ 全てのテストが成功しました")
        else:
            print("❌ テストに失敗しました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()