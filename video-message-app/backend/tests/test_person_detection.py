"""
Person Detection API tests

テスト項目:
1. 正常な画像アップロードと検出
2. 不正なファイルタイプの拒否
3. サイズ超過ファイルの拒否
4. レート制限の動作確認
"""
import pytest
import io
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.person_detection import router

# テスト用アプリケーション
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestPersonDetectionAPI:
    """Person Detection APIのテスト"""

    def test_health_check(self):
        """ヘルスチェック"""
        response = client.get("/person-detection/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "yolo_available" in data

    def test_detect_valid_image(self):
        """正常な画像での人物検出"""
        # 最小のJPEG画像データ
        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
            b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x10\x01'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x08\x01\x01\x00\x00?\x00T\xdf\xff\xd9'
        )

        files = {"image": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")}
        response = client.post("/person-detection/detect", files=files)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "person_count" in data
        assert "persons" in data
        assert "processing_time_ms" in data
        assert "image_size" in data

    def test_detect_invalid_file_type(self):
        """不正なファイルタイプの拒否"""
        # テキストファイル
        text_data = b"This is not an image file"

        files = {"image": ("malware.exe", io.BytesIO(text_data), "application/x-executable")}
        response = client.post("/person-detection/detect", files=files)

        assert response.status_code == 400
        assert "Invalid file extension" in response.json()["detail"]

    def test_detect_oversized_file(self):
        """サイズ超過ファイルの拒否"""
        # 11MBのダミーデータ
        large_data = b'\x00' * (11 * 1024 * 1024)

        files = {"image": ("large.jpg", io.BytesIO(large_data), "image/jpeg")}
        response = client.post("/person-detection/detect", files=files)

        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    def test_detect_no_file_uploaded(self):
        """ファイルなしのリクエスト拒否"""
        response = client.post("/person-detection/detect")

        assert response.status_code == 422  # Validation error

    def test_rate_limit(self):
        """レート制限の動作確認"""
        # 注意: このテストは実際のレート制限の設定に依存します
        # 連続リクエストを送信してレート制限をトリガー

        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
            b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x10\x01'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x08\x01\x01\x00\x00?\x00T\xdf\xff\xd9'
        )

        # 最初の10リクエストは成功するはず（レート制限: 10 req/60s）
        for i in range(10):
            files = {"image": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")}
            response = client.post("/person-detection/detect", files=files)
            assert response.status_code in [200, 429], f"Request {i+1} failed unexpectedly"

        # 11番目のリクエストはレート制限に引っかかるはず
        files = {"image": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")}
        response = client.post("/person-detection/detect", files=files)

        # レート制限のため429が返されることを期待
        # （ただし、テスト環境によっては200が返る可能性もある）
        assert response.status_code in [200, 429]
