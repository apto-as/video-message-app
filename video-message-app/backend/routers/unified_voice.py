"""
統合音声APIルーター
VOICEVOX、OpenVoice、D-IDを統一インターフェースで提供
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import tempfile
import os
from pathlib import Path
import aiofiles

from services.unified_voice_service import (
    UnifiedVoiceService,
    get_unified_voice_service,
    VoiceProvider,
    VoiceType,
    VoiceProfile,
    VoiceSynthesisRequest
)
from middleware.rate_limiter import limiter, SYNTHESIS_LIMIT

router = APIRouter(prefix="/unified-voice", tags=["Unified Voice"])

# === Pydanticモデル ===

class VoiceListRequest(BaseModel):
    provider: Optional[VoiceProvider] = None
    voice_type: Optional[VoiceType] = None
    language: Optional[str] = None

class CloneVoiceRequest(BaseModel):
    voice_name: str = Field(..., min_length=1, max_length=50)
    provider: VoiceProvider = VoiceProvider.OPENVOICE
    language: str = Field(default="ja", pattern="^(ja|en|zh|es|fr|ko)$")

class SynthesisRequestAPI(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    voice_profile_id: Optional[str] = Field(None, description="音声プロファイルID")
    voice_profile: Optional[Dict[str, Any]] = Field(None, description="音声プロファイル")
    speed: float = Field(default=1.0, ge=0.1, le=3.0)
    pitch: float = Field(default=0.0, ge=-0.15, le=0.15)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    intonation: float = Field(default=1.0, ge=0.0, le=2.0, description="抑揚（VOICEVOX専用）")
    emotion: str = Field(default="neutral")
    pause_duration: float = Field(default=0.0, ge=0.0, le=3.0, description="文末の無音ポーズ長（秒）")

# === エンドポイント ===

@router.get("/health")
async def health_check(
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """統合音声サービスのヘルスチェック"""
    try:
        health = await service.health_check()
        return health
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"サービスヘルスチェックエラー: {str(e)}")

@router.get("/voices", response_model=List[VoiceProfile])
async def get_available_voices(
    provider: Optional[VoiceProvider] = None,
    voice_type: Optional[VoiceType] = None,
    language: Optional[str] = None,
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """利用可能な音声一覧を取得"""
    try:
        voices = await service.get_available_voices(
            provider=provider,
            voice_type=voice_type,
            language=language
        )
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声一覧取得エラー: {str(e)}")

@router.post("/reload")
async def reload_profiles(
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """音声プロファイルを再読み込み"""
    try:
        result = await service.reload_profiles()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プロファイル再読み込みエラー: {str(e)}")

@router.get("/voices/{profile_id}")
async def get_voice_profile(
    profile_id: str,
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """特定の音声プロファイルを取得"""
    try:
        profile = await service.get_voice_profile(profile_id)
        
        if profile is None:
            raise HTTPException(status_code=404, detail="音声プロファイルが見つかりません")
        
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声プロファイル取得エラー: {str(e)}")

@router.post("/synthesize")
@limiter.limit(SYNTHESIS_LIMIT)
async def synthesize_speech(
    request_data: SynthesisRequestAPI,
    request: Request,
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """
    音声合成実行（レート制限: 10 requests/minute per user）

    Security:
    - Rate limited to 10 requests/minute per user
    - Prevents abuse and ensures fair resource allocation
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"音声合成リクエスト受信: text={request_data.text[:30]}..., voice_profile={request_data.voice_profile}, voice_profile_id={request_data.voice_profile_id}")

        # 音声プロファイル取得または直接使用
        if request_data.voice_profile:
            # 直接voice_profileオブジェクトが渡された場合、IDから完全なプロファイルを取得
            profile_id = request_data.voice_profile.get('id')
            if profile_id:
                voice_profile = await service.get_voice_profile(profile_id)
                if voice_profile is None:
                    # サービス内にプロファイルが見つからない場合は、Dictから VoiceProfile を作成
                    voice_profile = VoiceProfile(
                        id=profile_id,
                        name=request_data.voice_profile.get('name', 'Unknown'),
                        provider=VoiceProvider(request_data.voice_profile.get('provider', 'openvoice')),
                        voice_type=VoiceType(request_data.voice_profile.get('voice_type', 'cloned')),
                        language=request_data.voice_profile.get('language', 'ja'),
                        voice_file_path=request_data.voice_profile.get('voice_file_path'),
                        metadata=request_data.voice_profile.get('metadata', {})
                    )
            else:
                raise HTTPException(status_code=400, detail="voice_profileにIDが含まれていません")
        elif request_data.voice_profile_id:
            # voice_profile_idから取得
            voice_profile = await service.get_voice_profile(request_data.voice_profile_id)
            if voice_profile is None:
                raise HTTPException(status_code=404, detail="指定された音声プロファイルが見つかりません")
        else:
            raise HTTPException(status_code=400, detail="voice_profileまたはvoice_profile_idが必要です")

        # 音声合成リクエスト作成
        synthesis_request = VoiceSynthesisRequest(
            text=request_data.text,
            voice_profile=voice_profile,
            speed=request_data.speed,
            pitch=request_data.pitch,
            volume=request_data.volume,
            intonation=request_data.intonation,
            emotion=request_data.emotion,
            pause_duration=request_data.pause_duration
        )
        
        # 音声合成実行
        audio_data = await service.synthesize_speech(synthesis_request)
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{voice_profile.provider}_{voice_profile.id}.wav"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声合成エラー: {str(e)}")

@router.post("/clone", response_model=VoiceProfile)
async def clone_voice(
    voice_name: str,
    provider: VoiceProvider,
    language: str = "ja",
    audio_file: UploadFile = File(...),
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """音声クローン実行"""
    
    # ファイル形式チェック
    if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="音声ファイルをアップロードしてください")
    
    try:
        # 音声データ読み込み
        audio_data = await audio_file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="空の音声ファイルです")
        
        # ファイルサイズチェック（100MB制限）
        if len(audio_data) > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="ファイルサイズが大きすぎます（100MB以下）")
        
        # 音声クローン実行
        voice_profile = await service.clone_voice(
            voice_name=voice_name,
            reference_audio=audio_data,
            provider=provider,
            language=language
        )
        
        return voice_profile
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声クローンエラー: {str(e)}")

@router.get("/providers")
async def get_providers():
    """利用可能なプロバイダー一覧"""
    return {
        "providers": [
            {
                "id": "voicevox",
                "name": "VOICEVOX",
                "description": "日本語特化音声合成エンジン",
                "features": ["preset_voices", "japanese_native", "real_time"],
                "languages": ["ja"]
            },
            {
                "id": "openvoice",
                "name": "OpenVoice V2",
                "description": "オープンソース音声クローンエンジン",
                "features": ["voice_cloning", "multilingual", "mit_license"],
                "languages": ["ja", "en", "zh", "es", "fr", "ko"]
            }
        ]
    }

@router.get("/voice-types")
async def get_voice_types():
    """音声タイプ一覧"""
    return {
        "voice_types": [
            {
                "id": "preset",
                "name": "プリセット音声",
                "description": "事前に用意された音声"
            },
            {
                "id": "cloned",
                "name": "クローン音声",
                "description": "参照音声から生成された音声"
            },
            {
                "id": "custom",
                "name": "カスタム音声",
                "description": "ユーザーがカスタマイズした音声"
            }
        ]
    }

@router.post("/test")
async def test_synthesis():
    """音声合成テスト（デバッグ用）"""
    test_text = "統合音声サービスのテストです。VOICEVOX、OpenVoice、D-IDの統合が正常に動作しています。"
    
    try:
        service = await get_unified_voice_service()
        
        # ヘルスチェック
        health = await service.health_check()
        
        # 利用可能な音声を取得
        voices = await service.get_available_voices()
        
        test_results = {
            "message": "統合音声サービステスト",
            "text": test_text,
            "health": health,
            "available_voices": len(voices),
            "voice_summary": {}
        }
        
        # プロバイダー別集計
        for voice in voices:
            provider = voice.provider
            if provider not in test_results["voice_summary"]:
                test_results["voice_summary"][provider] = 0
            test_results["voice_summary"][provider] += 1
        
        return test_results
        
    except Exception as e:
        return {
            "error": f"統合音声サービステストエラー: {str(e)}",
            "text": test_text
        }

# === バックグラウンドタスク ===

@router.post("/clone/background")
async def clone_voice_background(
    background_tasks: BackgroundTasks,
    voice_name: str,
    provider: VoiceProvider,
    language: str = "ja",
    audio_file: UploadFile = File(...),
    service: UnifiedVoiceService = Depends(get_unified_voice_service)
):
    """バックグラウンド音声クローン（大きなファイル用）"""
    
    # ファイル形式チェック
    if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="音声ファイルをアップロードしてください")
    
    try:
        # 音声データ読み込み
        audio_data = await audio_file.read()
        
        # 一時ファイルに保存
        temp_dir = Path("/tmp/voice_clones")
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"{voice_name}_{provider}_{language}.wav"
        
        async with temp_file.open('wb') as f:
            await f.write(audio_data)
        
        # バックグラウンドタスクとして実行
        task_id = f"clone_{voice_name}_{provider}_{int(asyncio.get_event_loop().time())}"
        
        background_tasks.add_task(
            _background_clone_task,
            service=service,
            task_id=task_id,
            voice_name=voice_name,
            audio_file_path=str(temp_file),
            provider=provider,
            language=language
        )
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "音声クローンをバックグラウンドで実行中です",
            "estimated_time": "2-5分"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"バックグラウンド音声クローンエラー: {str(e)}")

async def _background_clone_task(
    service: UnifiedVoiceService,
    task_id: str,
    voice_name: str,
    audio_file_path: str,
    provider: VoiceProvider,
    language: str
):
    """バックグラウンド音声クローンタスク"""
    try:
        # 音声ファイル読み込み
        async with aiofiles.open(audio_file_path, 'rb') as f:
            audio_data = await f.read()
        
        # 音声クローン実行
        voice_profile = await service.clone_voice(
            voice_name=voice_name,
            reference_audio=audio_data,
            provider=provider,
            language=language
        )
        
        print(f"バックグラウンド音声クローン完了: {task_id} -> {voice_profile.id}")
        
    except Exception as e:
        print(f"バックグラウンド音声クローンエラー: {task_id} -> {str(e)}")
        
    finally:
        # 一時ファイル削除
        try:
            os.unlink(audio_file_path)
        except:
            pass

# === エラーハンドラー ===
# 注意: APIRouterレベルのexception_handlerは使用不可
# エラーハンドリングは各エンドポイント内で個別に実装