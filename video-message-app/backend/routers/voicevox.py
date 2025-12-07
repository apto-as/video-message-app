"""
VOICEVOX音声合成APIルーター
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import tempfile
import os
from pathlib import Path

from services.voicevox_client import (
    VOICEVOXClient, 
    get_voicevox_client, 
    VOICE_PRESETS
)

router = APIRouter(prefix="/voicevox", tags=["VOICEVOX"])

# === Pydanticモデル ===

class SpeakerInfo(BaseModel):
    speaker_name: str
    style_name: str
    style_id: int
    speaker_uuid: str
    order: Optional[int] = None

class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="合成する文章")
    speaker_id: int = Field(default=1, ge=0, description="話者ID")
    speed_scale: float = Field(default=1.0, ge=0.1, le=3.0, description="話速")
    pitch_scale: float = Field(default=0.0, ge=-0.15, le=0.15, description="音高")
    intonation_scale: float = Field(default=1.0, ge=0.0, le=2.0, description="抑揚")
    volume_scale: float = Field(default=1.0, ge=0.0, le=2.0, description="音量")
    pause_length: float = Field(default=0.0, ge=0.0, le=3.0, description="文末の無音ポーズ長（秒）")
    preset: Optional[str] = Field(default=None, description="音声プリセット")

class BatchSynthesisRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=20, description="合成するテキスト配列")
    speaker_id: int = Field(default=1, ge=0, description="話者ID")
    speed_scale: float = Field(default=1.0, ge=0.1, le=3.0, description="話速")
    pitch_scale: float = Field(default=0.0, ge=-0.15, le=0.15, description="音高")
    intonation_scale: float = Field(default=1.0, ge=0.0, le=2.0, description="抑揚")
    volume_scale: float = Field(default=1.0, ge=0.0, le=2.0, description="音量")

class SpeechTimeEstimation(BaseModel):
    text: str
    estimated_time: float
    character_count: int

# === エンドポイント ===

@router.get("/health")
async def health_check():
    """VOICEVOX Engineのヘルスチェック"""
    try:
        async with await get_voicevox_client() as client:
            health = await client.health_check()
            return health
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"VOICEVOX Engine接続エラー: {str(e)}")

@router.get("/speakers", response_model=List[SpeakerInfo])
async def get_speakers():
    """利用可能な話者一覧を取得"""
    try:
        async with await get_voicevox_client() as client:
            speakers = await client.get_speakers()
            
            # レスポンス形式に変換
            speaker_list = []
            for speaker in speakers:
                for style in speaker.get('styles', []):
                    speaker_list.append(SpeakerInfo(
                        speaker_name=speaker.get('name', ''),
                        style_name=style.get('name', ''),
                        style_id=style.get('id', 0),
                        speaker_uuid=speaker.get('speaker_uuid', '')
                    ))
            
            return speaker_list
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"話者情報取得エラー: {str(e)}")

@router.get("/speakers/popular", response_model=List[SpeakerInfo])
async def get_popular_speakers():
    """人気話者一覧を取得"""
    try:
        async with await get_voicevox_client() as client:
            speakers = await client.get_popular_speakers()
            
            return [SpeakerInfo(
                speaker_name=speaker['speaker_name'],
                style_name=speaker['style_name'],
                style_id=speaker['style_id'],
                speaker_uuid=speaker['speaker_uuid'],
                order=speaker['order']
            ) for speaker in speakers]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"人気話者取得エラー: {str(e)}")

@router.get("/speaker/{speaker_id}")
async def get_speaker_info(speaker_id: int):
    """特定話者の詳細情報を取得"""
    try:
        async with await get_voicevox_client() as client:
            speaker_info = await client.get_speaker_info(speaker_id)
            
            if speaker_info is None:
                raise HTTPException(status_code=404, detail="話者が見つかりません")
            
            return speaker_info
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"話者情報取得エラー: {str(e)}")

@router.post("/synthesis")
async def synthesize_speech(request: VoiceSynthesisRequest):
    """テキストから音声を合成

    Args:
        request: VoiceSynthesisRequest with pause_length for adding silence at end
    """
    try:
        async with await get_voicevox_client() as client:
            # プリセット適用
            params = {
                'speed_scale': request.speed_scale,
                'pitch_scale': request.pitch_scale,
                'intonation_scale': request.intonation_scale,
                'volume_scale': request.volume_scale,
                'pause_length': request.pause_length
            }

            if request.preset and request.preset in VOICE_PRESETS:
                preset_params = VOICE_PRESETS[request.preset]
                params.update(preset_params)

            # 音声合成実行
            audio_data = await client.text_to_speech(
                text=request.text,
                speaker_id=request.speaker_id,
                **params
            )
            
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=speech.wav"
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声合成エラー: {str(e)}")

@router.post("/synthesis/batch")
async def batch_synthesize_speech(request: BatchSynthesisRequest):
    """複数テキストの一括音声合成"""
    try:
        async with await get_voicevox_client() as client:
            params = {
                'speed_scale': request.speed_scale,
                'pitch_scale': request.pitch_scale,
                'intonation_scale': request.intonation_scale,
                'volume_scale': request.volume_scale
            }
            
            audio_results = await client.batch_synthesis(
                texts=request.texts,
                speaker_id=request.speaker_id,
                **params
            )
            
            # 一時ディレクトリに音声ファイルを保存
            temp_dir = tempfile.mkdtemp()
            file_paths = []
            
            for i, audio_data in enumerate(audio_results):
                if audio_data:  # 空でない場合のみ保存
                    file_path = os.path.join(temp_dir, f"speech_{i:03d}.wav")
                    await client.save_audio(audio_data, file_path)
                    file_paths.append(file_path)
            
            return {
                "message": f"{len(file_paths)}個の音声ファイルを生成しました",
                "file_count": len(file_paths),
                "temp_directory": temp_dir
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"一括音声合成エラー: {str(e)}")

@router.post("/estimate", response_model=SpeechTimeEstimation)
async def estimate_speech_time(text: str, speaker_id: int = 1):
    """発話時間推定"""
    try:
        async with await get_voicevox_client() as client:
            estimated_time = await client.estimate_speech_time(text, speaker_id)
            
            return SpeechTimeEstimation(
                text=text,
                estimated_time=estimated_time,
                character_count=len(text)
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"発話時間推定エラー: {str(e)}")

@router.get("/presets")
async def get_voice_presets():
    """音声プリセット一覧を取得"""
    return {
        "presets": VOICE_PRESETS,
        "available_presets": list(VOICE_PRESETS.keys())
    }

@router.post("/test")
async def test_voice_synthesis():
    """音声合成テスト（デバッグ用）"""
    test_text = "こんにちは、VOICEVOXの音声合成テストです。"
    
    try:
        async with await get_voicevox_client() as client:
            # ヘルスチェック
            health = await client.health_check()
            if health['status'] != 'healthy':
                return {"error": "VOICEVOX Engine is not healthy", "health": health}
            
            # テスト音声合成
            audio_data = await client.text_to_speech(test_text, speaker_id=1)
            
            return {
                "message": "音声合成テスト成功",
                "text": test_text,
                "audio_size": len(audio_data),
                "health": health
            }
            
    except Exception as e:
        return {
            "error": f"音声合成テストエラー: {str(e)}",
            "text": test_text
        }

# === 依存関数 ===

async def get_client():
    """DIコンテナ用のクライアント取得"""
    return await get_voicevox_client()

# === エラーハンドラー ===
# 注意: APIRouterレベルのexception_handlerは使用不可
# エラーハンドリングは各エンドポイント内で個別に実装