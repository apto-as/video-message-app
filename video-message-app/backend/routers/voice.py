from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from services.voice_manager import VoiceManager
from typing import Optional, List
import os
from pathlib import Path

router = APIRouter()
voice_manager = VoiceManager()

@router.post("/upload")
async def upload_voice(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    user_id: str = Form(default="default")
):
    """音声ファイルをアップロードしてカスタム音声を作成"""
    try:
        # ファイルのバリデーション
        is_valid, error_message = voice_manager.validate_audio_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # 音声ファイルの保存
        voice_id, voice_metadata = await voice_manager.save_audio_file(file, user_id)
        
        # 名前が指定されている場合は更新
        if name:
            voice_manager.update_voice_metadata(voice_id, {"name": name})
            voice_metadata["name"] = name
        
        return {
            "success": True,
            "voice_id": voice_id,
            "message": "音声ファイルのアップロードが完了しました",
            "voice_data": {
                "voice_id": voice_metadata["voice_id"],
                "name": voice_metadata.get("name", voice_metadata["original_filename"]),
                "original_filename": voice_metadata["original_filename"],
                "upload_date": voice_metadata["upload_date"],
                "duration": voice_metadata.get("duration", 0),
                "file_size": voice_metadata["file_size"],
                "status": voice_metadata["status"]
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"音声ファイルのアップロードに失敗しました: {str(e)}"
        )

@router.get("/custom")
async def get_custom_voices(user_id: str = Query(default="default")):
    """ユーザーのカスタム音声一覧を取得"""
    try:
        voices = voice_manager.get_voice_list(user_id)
        
        # レスポンス用にデータを整形
        voice_list = []
        for voice in voices:
            voice_list.append({
                "voice_id": voice["voice_id"],
                "name": voice.get("name", voice["original_filename"]),
                "original_filename": voice["original_filename"],
                "upload_date": voice["upload_date"],
                "duration": voice.get("duration", 0),
                "file_size": voice["file_size"],
                "status": voice["status"],
            })
        
        return {
            "success": True,
            "voices": voice_list,
            "total_count": len(voice_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"カスタム音声一覧の取得に失敗しました: {str(e)}"
        )

@router.delete("/{voice_id}")
async def delete_custom_voice(
    voice_id: str,
    user_id: str = Query(default="default")
):
    """カスタム音声を削除"""
    try:
        success = voice_manager.delete_voice(voice_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="指定された音声が見つかりません"
            )
        
        return {
            "success": True,
            "message": "カスタム音声を削除しました"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"カスタム音声の削除に失敗しました: {str(e)}"
        )

@router.get("/{voice_id}/preview")
async def preview_voice(
    voice_id: str,
    user_id: str = Query(default="default")
):
    """音声ファイルのプレビュー（ダウンロード）"""
    try:
        voice_data = voice_manager.get_voice_metadata(voice_id)
        
        if not voice_data or voice_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=404,
                detail="指定された音声が見つかりません"
            )
        
        file_path = voice_manager.get_voice_file_path(voice_id)
        
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="音声ファイルが見つかりません"
            )
        
        # ファイルを返す
        return FileResponse(
            path=file_path,
            filename=voice_data["original_filename"],
            media_type=voice_data["content_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"音声プレビューの取得に失敗しました: {str(e)}"
        )


@router.get("/stats")
async def get_voice_stats(user_id: str = Query(default="default")):
    """音声ストレージの使用状況を取得"""
    try:
        stats = voice_manager.get_storage_stats()
        user_voices = voice_manager.get_voice_list(user_id)
        
        user_stats = {
            "user_voice_count": len(user_voices),
            "user_total_size_mb": round(
                sum(voice.get("file_size", 0) for voice in user_voices) / (1024 * 1024), 2
            )
        }
        
        return {
            "success": True,
            "global_stats": stats,
            "user_stats": user_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"統計情報の取得に失敗しました: {str(e)}"
        )