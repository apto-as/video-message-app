"""
OpenVoice Native Service FastAPI Application
"""

import logging
import asyncio
import aiofiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional

from config import config
from models import (
    VoiceCloneRequest, VoiceSynthesisRequest, VoiceProfile,
    VoiceCloneResponse, VoiceSynthesisResponse, HealthCheckResponse,
    ErrorResponse
)
from openvoice_service import OpenVoiceNativeService

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# サービスインスタンス
openvoice_service = OpenVoiceNativeService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時処理
    logger.info("OpenVoice Native Service 起動中...")
    
    # サービス初期化
    success = await openvoice_service.initialize()
    if not success:
        logger.error("OpenVoice サービスの初期化に失敗しました")
        # 初期化失敗でもサービスは起動を続行（ヘルスチェックで状態確認可能）
    
    logger.info(f"OpenVoice Native Service 起動完了 (Port: {config.port})")
    
    yield
    
    # 終了時処理
    logger.info("OpenVoice Native Service 終了中...")

# FastAPIアプリケーション
app = FastAPI(
    title="OpenVoice Native Service",
    description="MacOS ネイティブ環境で動作するOpenVoice V2 API サービス",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """グローバル例外ハンドラー"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
        ).dict()
    )

@app.get("/", response_model=HealthCheckResponse)
async def root():
    """ルートエンドポイント"""
    return await health_check()

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """ヘルスチェック"""
    status_data = await openvoice_service.get_health_status()
    return HealthCheckResponse(**status_data)

@app.post("/voice-clone/create", response_model=VoiceCloneResponse)
async def create_voice_clone(
    name: str = Form(..., description="音声プロファイル名"),
    language: str = Form(default="ja", description="言語コード"),
    description: Optional[str] = Form(None, description="説明"),
    voice_profile_id: Optional[str] = Form(None, description="プロファイルID（バックエンド指定）"),
    audio_samples: List[UploadFile] = File(..., description="音声サンプル（3つ以上推奨）")
):
    """音声クローン作成"""
    
    # 音声サンプル数チェック
    if len(audio_samples) < 3:
        raise HTTPException(
            status_code=400,
            detail="最低3つの音声サンプルが必要です"
        )
    
    try:
        # 音声データ読み込み
        audio_files = []
        for sample in audio_samples:
            content = await sample.read()
            if len(content) > 10 * 1024 * 1024:  # 10MB制限
                raise HTTPException(
                    status_code=400,
                    detail=f"音声ファイル {sample.filename} が大きすぎます（最大10MB）"
                )
            audio_files.append(content)
        
        # 音声クローン作成
        result = await openvoice_service.create_voice_clone(
            name=name,
            audio_files=audio_files,
            language=language,
            profile_id=voice_profile_id  # バックエンドから指定されたIDを使用
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error or "音声クローンの作成に失敗しました"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声クローン作成エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音声クローン作成中にエラーが発生しました: {str(e)}"
        )

@app.post("/voice-clone/synthesize", response_model=VoiceSynthesisResponse)
async def synthesize_voice(
    text: str = Form(..., description="合成するテキスト"),
    voice_profile_id: str = Form(..., description="音声プロファイルID"),
    language: str = Form(default="ja", description="言語コード"),
    speed: float = Form(default=1.0, description="話速（0.5-2.0）")
):
    """音声合成"""
    
    # パラメータ検証
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="テキストが空です"
        )
    
    if not (0.5 <= speed <= 2.0):
        raise HTTPException(
            status_code=400,
            detail="話速は0.5から2.0の範囲で指定してください"
        )
    
    try:
        # 音声合成実行
        result = await openvoice_service.synthesize_voice(
            text=text,
            voice_profile_id=voice_profile_id,
            language=language,
            speed=speed
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error or "音声合成に失敗しました"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声合成エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音声合成中にエラーが発生しました: {str(e)}"
        )

@app.get("/voice-clone/profiles")
async def list_voice_profiles():
    """音声プロファイル一覧"""
    try:
        profiles = []
        profiles_dir = config.voice_profiles_dir
        
        if profiles_dir.exists():
            for profile_dir in profiles_dir.iterdir():
                if profile_dir.is_dir():
                    profile_file = profile_dir / "profile.json"
                    if profile_file.exists():
                        try:
                            import json
                            async with aiofiles.open(profile_file, 'r', encoding='utf-8') as f:
                                content = await f.read()
                                profile_data = json.loads(content)
                                if profile_data.get('status') == 'ready':
                                    profiles.append(VoiceProfile(**profile_data))
                        except Exception as e:
                            logger.warning(f"プロファイル読み込みエラー: {profile_dir.name} - {str(e)}")
        
        return profiles
        
    except Exception as e:
        logger.error(f"プロファイル一覧取得エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"プロファイル一覧の取得に失敗しました: {str(e)}"
        )

@app.delete("/voice-clone/profiles/{profile_id}")
async def delete_voice_profile(profile_id: str):
    """音声プロファイル削除"""
    try:
        profile_dir = config.voice_profiles_dir / profile_id
        
        if not profile_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="指定されたプロファイルが見つかりません"
            )
        
        # ディレクトリ削除
        import shutil
        shutil.rmtree(profile_dir)
        
        return {
            "success": True,
            "message": f"プロファイル {profile_id} を削除しました"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"プロファイル削除エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"プロファイル削除に失敗しました: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info"
    )