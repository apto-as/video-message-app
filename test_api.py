#!/usr/bin/env python3
"""
APIエンドポイントのテストスクリプト
"""
import requests
import base64
from PIL import Image, ImageDraw
import io
import json

def create_test_image_with_background(width=400, height=400):
    """テスト用の人物画像（簡単な図形で模擬）を作成"""
    # RGBAモードで画像を作成（透明度サポート）
    img = Image.new('RGB', (width, height), color='lightblue')  # 背景色
    draw = ImageDraw.Draw(img)
    
    # 人物を模擬した円形（顔）
    face_x, face_y = width // 2, height // 3
    face_radius = 50
    draw.ellipse([
        face_x - face_radius, face_y - face_radius,
        face_x + face_radius, face_y + face_radius
    ], fill='peachpuff', outline='black', width=2)
    
    # 体を模擬した四角形
    body_width, body_height = 60, 100
    body_x = face_x - body_width // 2
    body_y = face_y + face_radius
    draw.rectangle([
        body_x, body_y,
        body_x + body_width, body_y + body_height
    ], fill='blue', outline='black', width=2)
    
    # バイト列に変換
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    return buffer.getvalue()

def create_background_image(width=400, height=400):
    """テスト用の背景画像を作成"""
    img = Image.new('RGB', (width, height), color='green')  # 緑の背景
    draw = ImageDraw.Draw(img)
    
    # 簡単な風景を描画
    # 太陽
    sun_x, sun_y = width - 80, 80
    draw.ellipse([sun_x - 30, sun_y - 30, sun_x + 30, sun_y + 30], fill='yellow')
    
    # 雲
    for i, x in enumerate([100, 200, 300]):
        y = 60 + i * 10
        draw.ellipse([x - 25, y - 15, x + 25, y + 15], fill='white')
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    return buffer.getvalue()

def test_process_image_api():
    """画像処理APIのテスト"""
    print("🧪 画像処理APIのテストを開始...")
    
    # テスト画像を作成
    test_image = create_test_image_with_background()
    background_image = create_background_image()
    
    # APIエンドポイント
    url = "http://localhost:8000/api/video/process-image"
    
    # テスト1: 背景削除のみ
    print("\n📋 テスト1: 背景削除のみ")
    files = {
        'image': ('test_person.jpg', test_image, 'image/jpeg')
    }
    data = {
        'remove_background': True,
        'enhance_quality': True
    }
    
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功: {result.get('processing_info', {})}")
            if 'processed_image' in result:
                print("✅ 処理済み画像データを取得")
        else:
            print(f"❌ エラー: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return False
    
    # テスト2: 背景削除 + 背景合成
    print("\n📋 テスト2: 背景削除 + 背景合成")
    files = {
        'image': ('test_person.jpg', test_image, 'image/jpeg'),
        'background': ('test_background.jpg', background_image, 'image/jpeg')
    }
    data = {
        'remove_background': True,
        'enhance_quality': True
    }
    
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功: {result.get('processing_info', {})}")
            if 'processed_image' in result:
                print("✅ 合成画像データを取得")
                # 結果をファイルに保存（オプション）
                save_result_image(result['processed_image'], 'test_result_composite.jpg')
        else:
            print(f"❌ エラー: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return False
    
    return True

def save_result_image(data_url, filename):
    """処理結果画像をファイルに保存"""
    try:
        # data:image/jpeg;base64,xxx の形式から base64 部分を抽出
        header, encoded = data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
        
        with open(filename, 'wb') as f:
            f.write(image_data)
        print(f"💾 結果画像を保存: {filename}")
    except Exception as e:
        print(f"❌ 画像保存エラー: {e}")

def test_server_health():
    """サーバーのヘルスチェック"""
    print("🏥 サーバーヘルスチェック...")
    
    try:
        # サーバーが起動しているかチェック
        response = requests.get("http://localhost:8000", timeout=5)
        print(f"✅ サーバー応答: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ サーバーに接続できません: {e}")
        print("💡 バックエンドサーバーが起動していることを確認してください:")
        print("   cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app/backend")
        print("   ./run_server.sh")
        return False

if __name__ == "__main__":
    print("🚀 動画メッセージアプリ APIテスト開始\n")
    
    # サーバーヘルスチェック
    if not test_server_health():
        exit(1)
    
    # 画像処理APIテスト
    if test_process_image_api():
        print("\n🎉 全てのAPIテストが成功しました！")
        print("\n📝 次のステップ:")
        print("1. ブラウザで http://localhost:3000 を開く")
        print("2. フロントエンドUIでテストを実行")
        print("3. 実際の写真を使用してテスト")
    else:
        print("\n❌ APIテストに失敗しました")
        print("サーバーログを確認してください")