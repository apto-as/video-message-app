#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== D-ID APIキー設定 ===${NC}"

# プロジェクトディレクトリに移動
cd /Users/apto-as/workspace/github.com/apto-as/prototype-app/video-message-app

# 1. backend/.envファイルにD-ID APIキーを追加
echo -e "${YELLOW}D-ID APIキーを設定中...${NC}"

# .envファイルを作成/更新
cat > backend/.env << 'ENV'
# Environment
ENVIRONMENT=docker

# Services URLs
VOICEVOX_URL=http://voicevox:50021
OPENVOICE_SERVICE_URL=http://host.docker.internal:8001

# D-ID API Configuration
D_ID_API_KEY=your-d-id-api-key-here

# Logging
LOG_LEVEL=INFO
ENV

echo -e "${GREEN}✓ backend/.env にAPIキーを設定しました${NC}"

# 2. docker-compose.ymlを更新してAPIキーを環境変数として渡す
echo -e "${YELLOW}docker-compose.yml を更新中...${NC}"

cat > docker-compose.yml << 'COMPOSE'
version: '3.8'

services:
  voicevox:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    container_name: voicevox_engine
    ports:
      - "50021:50021"
    networks:
      - voice_network
    restart: unless-stopped

  backend:
    build: ./backend
    container_name: voice_backend
    ports:
      - "55433:55433"
    volumes:
      - ./data/backend/storage:/app/storage
      - ./backend:/app
    env_file:
      - ./backend/.env
    environment:
      - ENVIRONMENT=docker
      - VOICEVOX_URL=http://voicevox:50021
      - OPENVOICE_SERVICE_URL=http://host.docker.internal:8001
      - D_ID_API_KEY=your-d-id-api-key-here
      - LOG_LEVEL=INFO
    networks:
      - voice_network
    depends_on:
      - voicevox
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: voice_frontend
    ports:
      - "55434:80"
    volumes:
      - ./frontend/build:/usr/share/nginx/html
    environment:
      - REACT_APP_API_BASE_URL=https://3.115.141.166
      - REACT_APP_API_URL=https://3.115.141.166
    networks:
      - voice_network
    depends_on:
      - backend
    restart: unless-stopped

networks:
  voice_network:
    driver: bridge
COMPOSE

echo -e "${GREEN}✓ docker-compose.yml を更新しました${NC}"

# 3. バックエンドのD-IDルーターがAPIキーを正しく使用するか確認
echo -e "${YELLOW}D-IDルーターの設定を確認中...${NC}"

# backend/routers/d_id.pyが存在するか確認
if [ -f "backend/routers/d_id.py" ]; then
    echo -e "${GREEN}✓ D-IDルーターが存在します${NC}"
else
    echo -e "${RED}✗ D-IDルーターが見つかりません。作成します...${NC}"
    
    cat > backend/routers/d_id.py << 'PYTHON'
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import httpx
import os
import base64
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/d-id", tags=["d-id"])

# D-ID API設定
D_ID_API_KEY = os.getenv("D_ID_API_KEY", "")
D_ID_BASE_URL = "https://api.d-id.com"

class VideoGenerationRequest(BaseModel):
    source_image_url: str
    audio_url: str
    script_text: str

@router.post("/upload-source-image")
async def upload_source_image(file: UploadFile = File(...)):
    """画像をD-IDにアップロード"""
    
    if not D_ID_API_KEY:
        logger.error("D-ID API key is not configured")
        raise HTTPException(
            status_code=500,
            detail="D-ID API key is not configured"
        )
    
    try:
        logger.info(f"Uploading image to D-ID: {file.filename}")
        
        async with httpx.AsyncClient() as client:
            # Basic認証ヘッダーを作成
            auth_header = base64.b64encode(D_ID_API_KEY.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": file.content_type or "image/jpeg"
            }
            
            content = await file.read()
            
            response = await client.post(
                f"{D_ID_BASE_URL}/images",
                headers=headers,
                content=content,
                timeout=30.0
            )
            
            if response.status_code == 201:
                logger.info("Image uploaded successfully to D-ID")
                return response.json()
            else:
                logger.error(f"D-ID upload failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"D-ID API error: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-video")
async def generate_video(request: VideoGenerationRequest):
    """D-IDで動画を生成"""
    
    if not D_ID_API_KEY:
        logger.error("D-ID API key is not configured")
        raise HTTPException(
            status_code=500,
            detail="D-ID API key is not configured"
        )
    
    try:
        logger.info("Generating video with D-ID")
        
        async with httpx.AsyncClient() as client:
            auth_header = base64.b64encode(D_ID_API_KEY.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "source_url": request.source_image_url,
                "script": {
                    "type": "audio",
                    "audio_url": request.audio_url
                }
            }
            
            response = await client.post(
                f"{D_ID_BASE_URL}/talks",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code in [200, 201]:
                logger.info("Video generation started successfully")
                return response.json()
            else:
                logger.error(f"D-ID video generation failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"D-ID API error: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video-status/{video_id}")
async def get_video_status(video_id: str):
    """動画生成のステータスを確認"""
    
    if not D_ID_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="D-ID API key is not configured"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            auth_header = base64.b64encode(D_ID_API_KEY.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}"
            }
            
            response = await client.get(
                f"{D_ID_BASE_URL}/talks/{video_id}",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"D-ID API error: {response.text}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
PYTHON
fi

echo -e "${GREEN}=== D-ID APIキー設定完了 ===${NC}"
echo -e "${YELLOW}次のステップ:${NC}"
echo -e "1. バックエンドコンテナを再起動します"
echo -e "2. D-ID機能をテストします"