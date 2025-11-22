"""
Prosody調整API
音声のイントネーション、速度、アクセント、ポーズを調整する
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from fastapi.responses import Response
from typing import Optional
import logging
from pydantic import BaseModel, Field

from services.prosody_adjuster import (
    ProsodyAdjuster,
    ProsodyConfig,
    get_prosody_adjuster
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/prosody",
    tags=["prosody"],
    responses={404: {"description": "Not found"}}
)


class ProsodyAdjustRequest(BaseModel):
    """Prosody調整リクエスト"""
    pitch_shift: float = Field(
        default=0.0,
        ge=-12.0,
        le=12.0,
        description="ピッチシフト (semitones)"
    )
    speed_rate: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="速度倍率"
    )
    volume_db: float = Field(
        default=0.0,
        ge=-20.0,
        le=20.0,
        description="音量調整 (dB)"
    )
    pause_duration: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="文末ポーズ (秒)"
    )
    preserve_formants: bool = Field(
        default=True,
        description="フォルマント保持"
    )


class ProsodyAdjustResponse(BaseModel):
    """Prosody調整レスポンス"""
    success: bool
    message: str
    duration_original: float
    duration_adjusted: float
    adjustments_applied: dict
    processing_time: float
    audio_url: Optional[str] = None


@router.post("/adjust", response_model=ProsodyAdjustResponse)
async def adjust_prosody(
    audio_file: UploadFile = File(..., description="音声ファイル (WAV, MP3, FLAC等)"),
    pitch_shift: float = Form(0.0, description="ピッチシフト (semitones): -12〜+12"),
    speed_rate: float = Form(1.0, description="速度倍率: 0.5x〜2.0x"),
    volume_db: float = Form(0.0, description="音量調整 (dB): -20〜+20"),
    pause_duration: float = Form(0.0, description="文末ポーズ (秒): 0〜2"),
    preserve_formants: bool = Form(True, description="フォルマント保持")
):
    """
    Prosody調整API

    音声ファイルのピッチ、速度、音量、ポーズを調整します。

    **Parameters**:
    - **audio_file**: 調整する音声ファイル
    - **pitch_shift**: ピッチシフト量 (semitones, -12〜+12)
    - **speed_rate**: 速度倍率 (0.5x〜2.0x)
    - **volume_db**: 音量調整 (dB, -20〜+20)
    - **pause_duration**: 文末ポーズ追加 (秒, 0〜2)
    - **preserve_formants**: フォルマント保持（自然な声質維持）

    **Returns**:
    - 調整済み音声データ (WAV形式, 24kHz)
    """
    try:
        # 音声データ読み込み
        audio_data = await audio_file.read()

        if len(audio_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="音声ファイルが空です"
            )

        # Prosody設定作成
        config = ProsodyConfig(
            pitch_shift=pitch_shift,
            speed_rate=speed_rate,
            volume_db=volume_db,
            pause_duration=pause_duration,
            preserve_formants=preserve_formants
        )

        # Prosody調整実行
        adjuster = get_prosody_adjuster()
        result = adjuster.adjust_prosody(audio_data, config)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prosody調整に失敗しました: {result.error_message}"
            )

        # 調整済み音声を返す（WAV形式、Content-Dispositionヘッダー付き）
        return Response(
            content=result.audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="adjusted_{audio_file.filename}"',
                "X-Original-Duration": str(result.duration_original),
                "X-Adjusted-Duration": str(result.duration_adjusted),
                "X-Processing-Time": str(result.processing_time),
                "X-Sample-Rate": str(result.sample_rate)
            }
        )

    except ValueError as e:
        logger.error(f"パラメータ検証エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Prosody調整エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prosody調整処理中にエラーが発生しました: {str(e)}"
        )


@router.post("/adjust-with-json", response_model=ProsodyAdjustResponse)
async def adjust_prosody_with_json(
    audio_file: UploadFile = File(..., description="音声ファイル"),
    config: str = Form(..., description="Prosody設定 (JSON形式)")
):
    """
    Prosody調整API (JSON設定版)

    JSON形式で一括設定を渡してProsody調整します。

    **Example JSON**:
    ```json
    {
        "pitch_shift": 2.0,
        "speed_rate": 1.2,
        "volume_db": 3.0,
        "pause_duration": 0.5,
        "preserve_formants": true
    }
    ```
    """
    import json

    try:
        # JSON設定パース
        config_dict = json.loads(config)
        prosody_config = ProsodyConfig(**config_dict)

        # 音声データ読み込み
        audio_data = await audio_file.read()

        # Prosody調整実行
        adjuster = get_prosody_adjuster()
        result = adjuster.adjust_prosody(audio_data, prosody_config)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prosody調整に失敗しました: {result.error_message}"
            )

        return Response(
            content=result.audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="adjusted_{audio_file.filename}"',
                "X-Processing-Time": str(result.processing_time)
            }
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON設定のパースに失敗しました: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Prosody調整エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/validate")
async def validate_audio(
    audio_file: UploadFile = File(..., description="検証する音声ファイル")
):
    """
    音声データ検証API

    音声ファイルの妥当性を検証します（サンプルレート、長さ、チャンネル数など）。
    """
    try:
        audio_data = await audio_file.read()

        adjuster = get_prosody_adjuster()
        validation_result = adjuster.validate_audio(audio_data)

        return validation_result

    except Exception as e:
        logger.error(f"音声検証エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health")
async def health_check():
    """
    Prosody調整サービスのヘルスチェック
    """
    try:
        adjuster = get_prosody_adjuster()

        return {
            "status": "healthy",
            "service": "Prosody調整エンジン",
            "supported_formats": adjuster.supported_formats,
            "target_sample_rate": adjuster.target_sample_rate
        }

    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.get("/presets")
async def get_presets():
    """
    Prosody調整プリセット一覧

    よく使われる調整パターンのプリセットを返します。
    """
    presets = {
        "neutral": {
            "name": "ニュートラル（調整なし）",
            "config": {
                "pitch_shift": 0.0,
                "speed_rate": 1.0,
                "volume_db": 0.0,
                "pause_duration": 0.0
            }
        },
        "energetic": {
            "name": "元気・活発",
            "config": {
                "pitch_shift": 1.5,
                "speed_rate": 1.15,
                "volume_db": 2.0,
                "pause_duration": 0.2
            }
        },
        "calm": {
            "name": "落ち着いた",
            "config": {
                "pitch_shift": -1.0,
                "speed_rate": 0.9,
                "volume_db": -1.0,
                "pause_duration": 0.5
            }
        },
        "dramatic": {
            "name": "ドラマチック",
            "config": {
                "pitch_shift": 2.0,
                "speed_rate": 0.85,
                "volume_db": 3.0,
                "pause_duration": 0.8
            }
        },
        "fast_clear": {
            "name": "早口・明瞭",
            "config": {
                "pitch_shift": 0.5,
                "speed_rate": 1.3,
                "volume_db": 1.0,
                "pause_duration": 0.1
            }
        },
        "slow_deep": {
            "name": "ゆっくり・低音",
            "config": {
                "pitch_shift": -3.0,
                "speed_rate": 0.8,
                "volume_db": 0.0,
                "pause_duration": 0.6
            }
        }
    }

    return presets
