"""
音声クローン登録ルーター
Qwen3-TTSを使用したカスタム音声の登録・管理
"""

from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import asyncio
from pathlib import Path
import aiofiles
import json
import uuid
from datetime import datetime
import os

import logging

from core.config import settings

router = APIRouter(prefix="/voice-clone", tags=["Voice Clone"])
logger = logging.getLogger(__name__)


def get_tts_client():
    """Qwen3-TTSクライアントを取得する。"""
    from services.qwen_tts_client import Qwen3TTSClient
    return Qwen3TTSClient()


def get_tts_provider_name() -> str:
    """現在のTTSプロバイダー名を取得"""
    return "qwen3-tts"


async def synthesize_with_client(
    client: Any,
    text: str,
    voice_profile: Dict[str, Any],
    language: str = "ja"
) -> bytes:
    """
    Qwen3-TTSクライアントで音声合成を実行する。

    Args:
        client: Qwen3TTSClient
        text: 合成するテキスト
        voice_profile: 音声プロファイル情報
        language: 言語コード

    Returns:
        bytes: WAV音声データ
    """
    profile_id = voice_profile.get('id')
    if not profile_id:
        raise ValueError("Voice profile ID is required")
    return await client.synthesize_with_clone(
        text=text,
        profile_id=profile_id,
        language=language
    )


async def check_client_availability(client: Any) -> Dict[str, Any]:
    """
    Qwen3-TTSクライアントの可用性を確認する。

    Args:
        client: Qwen3TTSClient

    Returns:
        dict: 可用性情報
    """
    is_healthy = await client.check_service_health()
    return {
        'provider': 'qwen3-tts',
        'available': is_healthy,
        'native_service': is_healthy
    }

class VoiceCloneResponse(BaseModel):
    success: bool
    voice_profile_id: Optional[str] = None
    message: str
    error: Optional[str] = None

class VoiceProfile(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    language: str = "ja"
    created_at: str
    sample_count: int
    status: str  # processing, ready, failed

@router.post("/register", response_model=VoiceCloneResponse)
async def register_voice_clone(
    name: str = Form(..., description="音声プロファイル名"),
    description: str = Form(None, description="説明"),
    language: str = Form(default="ja", description="言語コード"),
    audio_samples: List[UploadFile] = File(..., description="音声サンプル（最低3つ、各10-30秒推奨）")
):
    """自分の声を登録してQwen3-TTSでクローン"""
    
    temp_files = []
    
    try:
        # 音声サンプルの検証
        logger.info(f"音声サンプル数: {len(audio_samples)}")
        logger.info(f"音声サンプル詳細: {[f'{f.filename} ({f.size} bytes)' for f in audio_samples]}")
        
        if len(audio_samples) < 3:
            raise HTTPException(
                status_code=400, 
                detail="最低3つの音声サンプルが必要です"
            )
        
        # プロファイルID生成
        profile_id = f"clone_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"音声クローン登録開始: {name} (ID: {profile_id})")
        
        # 音声ファイルを一時保存
        sample_paths = []
        for i, audio_file in enumerate(audio_samples):
            # ファイルサイズチェック（最大10MB）
            content = await audio_file.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"音声ファイル {audio_file.filename} が大きすぎます（最大10MB）"
                )
            
            # 一時ファイルに保存
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.webm'  # WebM形式として保存
            )
            temp_files.append(temp_file.name)
            
            async with aiofiles.open(temp_file.name, 'wb') as f:
                await f.write(content)
            
            # WebMからWAVに変換
            wav_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.wav'
            )
            temp_files.append(wav_file.name)
            wav_file.close()
            
            # ffmpegで変換（サンプリングレート22050Hz、モノラル、音量正規化）
            import subprocess
            try:
                # 入力ファイル情報をログ出力
                logger.info(f"変換前ファイル: {temp_file.name}, サイズ: {os.path.getsize(temp_file.name)} bytes")
                
                # ffmpeg変換実行（シンプルな変換に変更）
                cmd = [
                    'ffmpeg', '-i', temp_file.name,
                    '-ar', '22050',           # サンプリングレート
                    '-ac', '1',               # モノラル
                    '-acodec', 'pcm_s16le',   # WAV形式
                    '-y',                     # 上書き
                    wav_file.name
                ]
                
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"ffmpeg変換成功: {result.stdout}")
                if result.stderr:
                    logger.warning(f"ffmpeg警告: {result.stderr}")
                
                # 変換後ファイル情報を確認
                if not os.path.exists(wav_file.name) or os.path.getsize(wav_file.name) == 0:
                    raise Exception("変換後ファイルが空または存在しません")
                
                # 変換後ファイル詳細検証
                verify_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', wav_file.name]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                
                if verify_result.returncode == 0:
                    import json
                    probe_data = json.loads(verify_result.stdout)
                    
                    # ストリーム情報を確認
                    streams = probe_data.get('streams', [])
                    if streams:
                        stream = streams[0]
                        logger.info(f"変換後ファイル詳細:")
                        logger.info(f"  - コーデック: {stream.get('codec_name')}")
                        logger.info(f"  - サンプルレート: {stream.get('sample_rate')}")
                        logger.info(f"  - チャンネル数: {stream.get('channels')}")
                        logger.info(f"  - 時間: {stream.get('duration', 'unknown')}秒")
                        
                        # 最小要件チェック
                        duration = float(stream.get('duration', 0))
                        if duration < 1.0:
                            logger.warning(f"音声ファイルが短すぎます: {duration}秒")
                        elif duration > 60.0:
                            logger.warning(f"音声ファイルが長すぎます: {duration}秒")
                    
                    logger.info(f"サンプル {i+1}/{len(audio_samples)} 変換・検証完了 - サイズ: {os.path.getsize(wav_file.name)} bytes")
                else:
                    logger.error(f"変換後ファイル検証失敗: {verify_result.stderr}")
                    raise Exception(f"変換後ファイルの検証に失敗しました: {verify_result.stderr}")
                
                sample_paths.append(wav_file.name)
                
            except subprocess.CalledProcessError as e:
                error_detail = e.stderr.decode() if e.stderr else str(e)
                logger.error(f"音声変換エラー (ffmpeg): {error_detail}")
                logger.error(f"ffmpeg stdout: {e.stdout.decode() if e.stdout else 'None'}")
                raise HTTPException(
                    status_code=500,
                    detail=f"音声ファイルの変換に失敗しました: {error_detail}"
                )
            except Exception as e:
                logger.error(f"音声変換処理エラー: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"音声変換処理でエラーが発生しました: {str(e)}"
                )
        
        # 【重要】まずTTS処理を実行し、成功した場合のみファイル保存を行う
        voice_embedding = None

        # TTSクライアント取得（設定に基づいて自動選択）
        try:
            tts_client = get_tts_client()
            provider_name = get_tts_provider_name()
            logger.info(f"TTSプロバイダー: {provider_name}")
        except ImportError as e:
            logger.error(f"TTSクライアント インポートエラー: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="TTS機能が利用できません"
            )

        try:
            # TTSクライアント初期化
            async with tts_client:
                # 音声特徴抽出とモデル作成
                voice_embedding = await tts_client.create_voice_clone(
                    name=name,
                    audio_paths=sample_paths,
                    language=language,
                    profile_id=profile_id
                )
            
            if not voice_embedding or not voice_embedding.get('success'):
                error_msg = voice_embedding.get('error', '音声クローンの作成に失敗しました') if voice_embedding else '音声クローンの作成に失敗しました'
                logger.error(f"音声クローン作成失敗: {error_msg}")
                logger.error(f"音声クローン結果詳細: {voice_embedding}")
                raise HTTPException(
                    status_code=500,
                    detail=f"音声クローン処理に失敗しました: {error_msg}"
                )
            
            # Native Serviceが返したプロファイルIDを使用（バックエンドIDと同じはず）
            native_profile_id = voice_embedding.get('profile_id')
            if native_profile_id and native_profile_id != profile_id:
                logger.warning(f"プロファイルID不一致: バックエンド={profile_id}, Native={native_profile_id}")
                logger.info(f"バックエンドのIDを使用: {profile_id}")
            logger.info(f"音声クローン作成成功: プロファイルID={profile_id}")
            
        except HTTPException:
            # HTTPExceptionはそのまま再発生
            raise
        except Exception as e:
            logger.error(f"音声クローン処理エラー: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"音声クローン処理に失敗しました: {str(e)}"
            )
        
        # 【成功時のみ】プロファイル情報を保存
        try:
            from services.voice_storage_service import VoiceStorageService
            storage_service = VoiceStorageService()
        except ImportError as e:
            logger.error(f"VoiceStorageService インポートエラー: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="音声ストレージ機能が利用できません"
            )
        
        # プロファイルディレクトリを先に作成
        profile_dir = storage_service.profiles_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # 全ての音声サンプルを永続保存
        saved_sample_paths = []
        reference_audio_path = None
        
        try:
            for i, sample_path in enumerate(sample_paths):
                # 意味のあるファイル名で保存
                sample_filename = f"sample_{i+1:02d}{Path(sample_path).suffix}"
                saved_sample_path = profile_dir / sample_filename
                
                import shutil
                shutil.copy2(sample_path, saved_sample_path)
                saved_sample_paths.append(str(saved_sample_path))
                
                # 最初のファイルを参照音声として設定
                if i == 0:
                    reference_audio_path = str(saved_sample_path)
                
                logger.info(f"音声サンプル {i+1} を永続保存: {saved_sample_path}")
            
            profile_data = {
                "id": profile_id,
                "name": name,
                "description": description,
                "language": language,
                "created_at": datetime.now().isoformat(),
                "sample_count": len(audio_samples),
                "status": "ready",
                "provider": provider_name,
                "voice_type": "cloned",
                # Native Serviceから返された埋め込みファイルパスを使用
                "embedding_path": voice_embedding.get("embedding_path") or voice_embedding.get("path"),
                "reference_audio_path": reference_audio_path,  # 参照音声ファイルパス（1つ目）
                "sample_audio_paths": saved_sample_paths,  # 全ての音声サンプルパス
                "metadata": {
                    "sample_files": [f.filename for f in audio_samples],
                    "processing_time": voice_embedding.get("processing_time", 0),
                    "total_samples_saved": len(saved_sample_paths)
                }
            }
            
            # プロファイルを保存
            saved_path = await storage_service.save_voice_profile(
                profile_id=profile_id,
                profile_data=profile_data
            )
            
            logger.info(f"音声プロファイル保存完了: {saved_path}")
            
            return VoiceCloneResponse(
                success=True,
                voice_profile_id=profile_id,
                message=f"音声クローン「{name}」の登録が完了しました"
            )
            
        except Exception as e:
            # ファイル保存でエラーが発生した場合、作成したディレクトリを削除
            logger.error(f"ファイル保存エラー: {str(e)}")
            try:
                if profile_dir.exists():
                    import shutil
                    shutil.rmtree(profile_dir)
                    logger.info(f"エラー時プロファイルディレクトリ削除: {profile_dir}")
            except Exception as cleanup_error:
                logger.warning(f"プロファイルディレクトリ削除失敗: {cleanup_error}")
            
            raise HTTPException(
                status_code=500,
                detail=f"プロファイルファイル保存に失敗しました: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声クローン登録エラー: {str(e)}")
        return VoiceCloneResponse(
            success=False,
            error=str(e),
            message="音声クローン登録中にエラーが発生しました"
        )
        
    finally:
        # 一時ファイル削除
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"一時ファイル削除失敗: {temp_file} - {str(e)}")

@router.get("/profiles", response_model=List[VoiceProfile])
async def get_voice_profiles():
    """登録済み音声プロファイル一覧を取得"""
    try:
        from services.voice_storage_service import VoiceStorageService
        storage_service = VoiceStorageService()
        # 現在のプロバイダーと互換性のあるプロファイルを取得
        # qwen3-ttsプロファイルと旧openvoice_*プロファイルの両方を取得（後方互換性）
        current_provider = get_tts_provider_name()
        profiles = await storage_service.get_all_voice_profiles(provider=current_provider)
        # 旧openvoice_*プロファイルも追加（Qwen3-TTSでも使用可能）
        if current_provider == "qwen3-tts":
            legacy_profiles = await storage_service.get_all_voice_profiles(provider="openvoice")
            profiles.extend(legacy_profiles)
        
        return [
            VoiceProfile(**profile)
            for profile in profiles
            if profile.get("status") == "ready"
        ]
        
    except Exception as e:
        logger.error(f"プロファイル取得エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"プロファイル取得に失敗しました: {str(e)}"
        )

@router.delete("/profiles/{profile_id}")
async def delete_voice_profile(profile_id: str):
    """音声プロファイルを削除"""
    try:
        from services.voice_storage_service import VoiceStorageService
        storage_service = VoiceStorageService()
        success = await storage_service.delete_voice_profile(profile_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="指定されたプロファイルが見つかりません"
            )
        
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

@router.post("/test-generate")
async def test_generate_voice_with_existing_samples(
    text: str = Form(default="こんにちは。これは既存サンプルを使用したテスト音声です。", description="テスト文章")
):
    """既存のサンプル音声ファイルを使用して音声生成テスト"""
    try:
        logger.info("既存サンプルファイルでの音声生成テスト開始")
        
        # 既存のサンプルファイルを使用
        base_path = "/app/storage/voices/profiles/openvoice_def9ad8f"
        sample_files = [
            f"{base_path}/sample_01.wav",
            f"{base_path}/sample_02.wav", 
            f"{base_path}/sample_03.wav"
        ]
        
        # ファイル存在確認
        for f in sample_files:
            if not Path(f).exists():
                raise HTTPException(status_code=404, detail=f"サンプルファイルが見つかりません: {f}")
        
        # TTSクライアントで処理（設定に基づいて自動選択）
        tts_client = get_tts_client()

        async with tts_client:
            # 音声クローン作成
            voice_embedding = await tts_client.create_voice_clone(
                name="test-existing-samples-clone",
                audio_paths=sample_files,
                language="ja",
                profile_id=f"test_existing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            if not voice_embedding or not voice_embedding.get('success'):
                raise HTTPException(status_code=500, detail="音声クローン作成に失敗しました")

            logger.info(f"テスト用音声クローン作成成功: {voice_embedding.get('profile_id')}")

            # テスト用プロファイル
            test_profile = {
                'id': voice_embedding.get('profile_id'),
                'name': 'test-existing-samples-clone',
                'reference_audio_path': sample_files[0]
            }

            # 音声合成（クライアントの違いを吸収）
            audio_data = await synthesize_with_client(
                client=tts_client,
                text=text,
                voice_profile=test_profile,
                language="ja"
            )
            
            if not audio_data or len(audio_data) < 1000:
                raise HTTPException(status_code=500, detail="音声合成に失敗しました")
            
            logger.info(f"テスト音声合成成功: {len(audio_data)} bytes")
            
            # 音声データをHTTPレスポンスとして返却
            from fastapi.responses import Response
            
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f"attachment; filename=test_voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav",
                    "X-Audio-Size": str(len(audio_data)),
                    "X-Profile-ID": voice_embedding.get('profile_id'),
                    "X-Test-Success": "true"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"テスト音声生成エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"テスト音声生成に失敗しました: {str(e)}"
        )

@router.post("/test/{profile_id}")
async def test_voice_profile(
    profile_id: str,
    text: str = Form(default="こんにちは、音声クローンのテストです", description="テスト文章")
):
    """音声プロファイルをテスト"""
    try:
        logger.info(f"音声プロファイルテスト開始: {profile_id}")
        
        # voices_metadata.jsonから直接プロファイル取得
        metadata_path = Path("/app/storage/voices/voices_metadata.json")
        
        if not metadata_path.exists():
            logger.error("voices_metadata.jsonが見つかりません")
            raise HTTPException(status_code=500, detail="音声メタデータファイルが見つかりません")
        
        async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            metadata = json.loads(content)
        
        profile = metadata.get('profiles', {}).get(profile_id)
        
        if not profile:
            logger.error(f"プロファイルが見つかりません: {profile_id}")
            raise HTTPException(
                status_code=404,
                detail="指定されたプロファイルが見つかりません"
            )
        
        # プロファイルにIDを追加（synthesize_with_cloneで必要）
        profile['id'] = profile_id
        
        logger.info(f"プロファイル取得成功: {profile.get('name')} (ID: {profile_id}, 参照音声: {profile.get('reference_audio_path')})")
        
        # TTSクライアントで音声合成（設定に基づいて自動選択）
        tts_client = get_tts_client()

        async with tts_client:
            # サービス可用性をログ出力
            availability = await check_client_availability(tts_client)
            logger.info(f"TTSサービス状態: {availability}")

            audio_data = await synthesize_with_client(
                client=tts_client,
                text=text,
                voice_profile=profile,
                language=profile.get("language", "ja")
            )
        
        if not audio_data:
            logger.error("音声合成結果が空です")
            raise Exception("音声合成に失敗しました")
        
        logger.info(f"音声合成成功: {len(audio_data)} bytes")
        
        # 【緊急修正】音声データをHTTPレスポンスとして直接返却
        from fastapi.responses import Response
        
        # プロファイル名を安全にエンコード（ASCII文字のみを許可）
        profile_name = profile.get('name', 'Unknown')
        try:
            # ASCII文字に変換可能か確認
            safe_profile_name = profile_name.encode('ascii', 'ignore').decode('ascii')
            if not safe_profile_name:
                safe_profile_name = profile_id  # 変換できない場合はIDを使用
        except:
            safe_profile_name = profile_id
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=voice_test_{profile_id}.wav",
                "X-Audio-Size": str(len(audio_data)),
                "X-Profile-Name": safe_profile_name,
                "X-Profile-Id": profile_id,
                "X-Native-Service": str(availability.get('native_service', False)),
                "X-Test-Success": "true"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音声テストエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音声テストに失敗しました: {str(e)}"
        )