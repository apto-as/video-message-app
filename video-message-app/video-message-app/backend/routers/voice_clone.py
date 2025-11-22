"""
音声クローン登録ルーター
OpenVoice V2を使用したカスタム音声の登録
"""

from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from models.schemas import VoiceProfile, VoiceCloneResponse
from core.constants import MAX_AUDIO_SIZE_BYTES

from typing import Optional, List, Dict, Any, Tuple
import tempfile
import asyncio
from pathlib import Path
import aiofiles
import json
import uuid
from datetime import datetime
import os
import subprocess
import shutil

import logging

router = APIRouter(prefix="/voice-clone", tags=["Voice Clone"])
logger = logging.getLogger(__name__)


# ===== ヘルパー関数 =====

async def _validate_audio_samples(
    audio_samples: List[UploadFile],
    min_samples: int = 3
) -> None:
    """音声サンプルを検証

    Args:
        audio_samples: アップロードされた音声ファイル
        min_samples: 最低必要なサンプル数

    Raises:
        HTTPException: 検証失敗時
    """
    logger.info(f"音声サンプル数: {len(audio_samples)}")
    logger.info(f"音声サンプル詳細: {[f'{f.filename} ({f.size} bytes)' for f in audio_samples]}")

    if len(audio_samples) < min_samples:
        raise HTTPException(
            status_code=400,
            detail=f"最低{min_samples}つの音声サンプルが必要です"
        )


async def _convert_audio_to_wav(
    audio_file: UploadFile,
    index: int,
    total_samples: int
) -> Tuple[str, str]:
    """音声ファイルをWAVに変換

    Args:
        audio_file: アップロードされた音声ファイル
        index: サンプル番号（0始まり）
        total_samples: 総サンプル数

    Returns:
        (WebMファイルパス, WAVファイルパス) のタプル

    Raises:
        HTTPException: 変換失敗時
    """
    # ファイルサイズチェック
    content = await audio_file.read()
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"音声ファイル {audio_file.filename} が大きすぎます（最大10MB）"
        )

    # WebMファイルとして一時保存
    webm_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
    async with aiofiles.open(webm_file.name, 'wb') as f:
        await f.write(content)

    # WAVファイル用の一時ファイル
    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    wav_file.close()

    # ffmpegで変換
    try:
        logger.info(f"変換前ファイル: {webm_file.name}, サイズ: {os.path.getsize(webm_file.name)} bytes")

        cmd = [
            'ffmpeg', '-i', webm_file.name,
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

        # 変換後ファイル検証
        _verify_converted_audio(wav_file.name, index, total_samples)

        return webm_file.name, wav_file.name

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


def _verify_converted_audio(wav_path: str, index: int, total_samples: int) -> None:
    """変換後の音声ファイルを検証

    Args:
        wav_path: WAVファイルパス
        index: サンプル番号（0始まり）
        total_samples: 総サンプル数

    Raises:
        Exception: 検証失敗時
    """
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        raise Exception("変換後ファイルが空または存在しません")

    verify_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', wav_path]
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)

    if verify_result.returncode != 0:
        logger.error(f"変換後ファイル検証失敗: {verify_result.stderr}")
        raise Exception(f"変換後ファイルの検証に失敗しました: {verify_result.stderr}")

    probe_data = json.loads(verify_result.stdout)
    streams = probe_data.get('streams', [])

    if not streams:
        raise Exception("音声ストリームが見つかりません")

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

    logger.info(f"サンプル {index+1}/{total_samples} 変換・検証完了 - サイズ: {os.path.getsize(wav_path)} bytes")


async def _create_voice_clone_with_openvoice(
    name: str,
    sample_paths: List[str],
    language: str,
    profile_id: str
) -> Dict[str, Any]:
    """OpenVoiceで音声クローンを作成

    Args:
        name: プロファイル名
        sample_paths: 音声サンプルファイルパス
        language: 言語コード
        profile_id: プロファイルID

    Returns:
        音声クローン作成結果

    Raises:
        HTTPException: 作成失敗時
    """
    try:
        from services.openvoice_hybrid_client import OpenVoiceHybridClient
        openvoice_client = OpenVoiceHybridClient()
    except ImportError as e:
        logger.error(f"OpenVoiceHybridClient インポートエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="OpenVoice機能が利用できません"
        )

    try:
        async with openvoice_client:
            voice_embedding = await openvoice_client.create_voice_clone(
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

        # プロファイルID整合性チェック
        native_profile_id = voice_embedding.get('profile_id')
        if native_profile_id and native_profile_id != profile_id:
            logger.warning(f"プロファイルID不一致: バックエンド={profile_id}, Native={native_profile_id}")
            logger.info(f"バックエンドのIDを使用: {profile_id}")

        logger.info(f"音声クローン作成成功: プロファイルID={profile_id}")
        return voice_embedding

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenVoice処理エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音声クローン処理に失敗しました: {str(e)}"
        )


async def _save_voice_profile(
    profile_id: str,
    name: str,
    description: Optional[str],
    language: str,
    audio_samples: List[UploadFile],
    sample_paths: List[str],
    voice_embedding: Dict[str, Any]
) -> str:
    """音声プロファイルを保存

    Args:
        profile_id: プロファイルID
        name: プロファイル名
        description: 説明
        language: 言語コード
        audio_samples: 元の音声ファイル
        sample_paths: 変換済み音声サンプルパス
        voice_embedding: 音声クローン結果

    Returns:
        保存先パス

    Raises:
        HTTPException: 保存失敗時
    """
    try:
        from services.voice_storage_service import VoiceStorageService
        storage_service = VoiceStorageService()
    except ImportError as e:
        logger.error(f"VoiceStorageService インポートエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="音声ストレージ機能が利用できません"
        )

    # プロファイルディレクトリ作成
    profile_dir = storage_service.profiles_dir / profile_id
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 音声サンプルを永続保存
        saved_sample_paths = []
        reference_audio_path = None

        for i, sample_path in enumerate(sample_paths):
            sample_filename = f"sample_{i+1:02d}{Path(sample_path).suffix}"
            saved_sample_path = profile_dir / sample_filename

            shutil.copy2(sample_path, saved_sample_path)
            saved_sample_paths.append(str(saved_sample_path))

            # 最初のファイルを参照音声として設定
            if i == 0:
                reference_audio_path = str(saved_sample_path)

            logger.info(f"音声サンプル {i+1} を永続保存: {saved_sample_path}")

        # プロファイルデータ作成
        profile_data = {
            "id": profile_id,
            "name": name,
            "description": description,
            "language": language,
            "created_at": datetime.now().isoformat(),
            "sample_count": len(audio_samples),
            "status": "ready",
            "provider": "openvoice",
            "voice_type": "cloned",
            "embedding_path": voice_embedding.get("embedding_path") or voice_embedding.get("path"),
            "reference_audio_path": reference_audio_path,
            "sample_audio_paths": saved_sample_paths,
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
        return saved_path

    except Exception as e:
        # ファイル保存エラー時、作成したディレクトリを削除
        logger.error(f"ファイル保存エラー: {str(e)}")
        try:
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
                logger.info(f"エラー時プロファイルディレクトリ削除: {profile_dir}")
        except Exception as cleanup_error:
            logger.warning(f"プロファイルディレクトリ削除失敗: {cleanup_error}")

        raise HTTPException(
            status_code=500,
            detail=f"プロファイルファイル保存に失敗しました: {str(e)}"
        )


# ===== メインエンドポイント =====


@router.post("/register", response_model=VoiceCloneResponse)
async def register_voice_clone(
    name: str = Form(..., description="音声プロファイル名"),
    description: str = Form(None, description="説明"),
    language: str = Form(default="ja", description="言語コード"),
    audio_samples: List[UploadFile] = File(..., description="音声サンプル（最低3つ、各10-30秒推奨）")
):
    """自分の声を登録してOpenVoice V2でクローン"""
    temp_files = []

    try:
        # 1. 音声サンプルの検証
        await _validate_audio_samples(audio_samples)

        # 2. プロファイルID生成
        profile_id = f"openvoice_{uuid.uuid4().hex[:8]}"
        logger.info(f"音声クローン登録開始: {name} (ID: {profile_id})")

        # 3. 音声ファイルをWAVに変換
        sample_paths = []
        for i, audio_file in enumerate(audio_samples):
            webm_path, wav_path = await _convert_audio_to_wav(audio_file, i, len(audio_samples))
            temp_files.extend([webm_path, wav_path])
            sample_paths.append(wav_path)

        # 4. OpenVoiceで音声クローンを作成
        voice_embedding = await _create_voice_clone_with_openvoice(
            name=name,
            sample_paths=sample_paths,
            language=language,
            profile_id=profile_id
        )

        # 5. プロファイル情報を保存
        await _save_voice_profile(
            profile_id=profile_id,
            name=name,
            description=description,
            language=language,
            audio_samples=audio_samples,
            sample_paths=sample_paths,
            voice_embedding=voice_embedding
        )

        return VoiceCloneResponse(
            success=True,
            voice_profile_id=profile_id,
            message=f"音声クローン「{name}」の登録が完了しました"
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
        profiles = await storage_service.get_all_voice_profiles(provider="openvoice")
        
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
        
        # OpenVoice ハイブリッドクライアントで処理
        from services.openvoice_hybrid_client import OpenVoiceHybridClient
        
        async with OpenVoiceHybridClient() as openvoice_client:
            # 音声クローン作成
            voice_embedding = await openvoice_client.create_voice_clone(
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
            
            # 音声合成
            audio_data = await openvoice_client.synthesize_with_clone(
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
        
        # OpenVoice ハイブリッドクライアントで音声合成（遅延インポート）
        from services.openvoice_hybrid_client import OpenVoiceHybridClient
        
        async with OpenVoiceHybridClient() as openvoice_client:
            # サービス可用性をログ出力
            availability = await openvoice_client.check_service_availability()
            logger.info(f"OpenVoiceサービス状態: {availability}")
            
            audio_data = await openvoice_client.synthesize_with_clone(
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
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # ASCII変換失敗時はprofile_idを使用
            logger.warning(f"Profile名のASCII変換失敗: {e}")
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