"""
OpenVoice V2 Native Service Core
"""

import os
import asyncio
import tempfile
import shutil
import logging
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiofiles
import numpy as np
from datetime import datetime
import uuid

from config import config
from models import VoiceProfile, VoiceCloneResponse, VoiceSynthesisResponse

logger = logging.getLogger(__name__)

# Mac環境でのWhisperモデル設定を最適化
import platform
if platform.system() == 'Darwin':
    import sys
    import importlib
    
    def patch_whisper_model():
        """最適化されたWhisperモデルパッチ"""
        try:
            from faster_whisper import WhisperModel as OriginalWhisperModel
            
            class OptimizedWhisperModel(OriginalWhisperModel):
                def __init__(self, model_size, device="auto", compute_type="auto", **kwargs):
                    # Macの場合、最適化されたCPU設定
                    if device == "cuda" or platform.system() == 'Darwin':
                        logger.info("Mac環境検出: WhisperモデルをCPU最適化モードに変更")
                        device = "cpu"
                        compute_type = "int8"  # CPU最適化
                        # メモリ効率化のためのオプション
                        kwargs.update({
                            'cpu_threads': 4,  # CPU並列化
                            'num_workers': 1,  # メモリ節約
                        })
                    super().__init__(model_size, device=device, compute_type=compute_type, **kwargs)
            
            # モジュールレベルでパッチを適用
            sys.modules['faster_whisper'].WhisperModel = OptimizedWhisperModel
            logger.info("Whisperモデルの最適化パッチ適用完了")
            
        except Exception as e:
            logger.warning(f"Whisperモデルのパッチ適用失敗: {str(e)}")
    
    # 初期化時にパッチを適用
    patch_whisper_model()

class OpenVoiceNativeService:
    """OpenVoice V2 ネイティブサービス"""
    
    def __init__(self):
        self.config = config
        self._initialized = False
        self._tone_color_converter = None
        self._se_extractor = None
        self._models = {}
        
    async def initialize(self) -> bool:
        """サービス初期化"""
        try:
            logger.info("OpenVoice Native Service 初期化開始...")
            
            # モデルファイル確認
            if not await self._check_model_files():
                logger.error("必要なモデルファイルが見つかりません")
                return False
            
            # OpenVoiceライブラリのインポート
            if not await self._import_openvoice():
                logger.error("OpenVoiceライブラリのインポートに失敗")
                return False
            
            # モデル初期化
            if not await self._initialize_models():
                logger.error("モデルの初期化に失敗")
                return False
            
            self._initialized = True
            logger.info("OpenVoice Native Service 初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"初期化エラー: {str(e)}")
            return False
    
    async def _check_model_files(self) -> bool:
        """必要なモデルファイルの存在確認"""
        required_files = [
            self.config.checkpoint_path,
            self.config.config_path,
            self.config.japanese_speaker_path,
            self.config.english_speaker_path
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"不足モデルファイル: {missing_files}")
            return False
        
        logger.info("必要なモデルファイルを確認しました")
        return True
    
    async def _import_openvoice(self) -> bool:
        """OpenVoiceライブラリのインポート"""
        try:
            # NumPyバージョンチェック
            import numpy as np
            logger.info(f"NumPy version: {np.__version__}")
            
            # 遅延インポート
            global ToneColorConverter, se_extractor, TTS
            
            # OpenVoice V2のインポートパスを調整
            import sys
            openvoice_path = os.path.join(os.path.dirname(__file__), "OpenVoiceV2")
            if os.path.exists(openvoice_path) and openvoice_path not in sys.path:
                sys.path.insert(0, openvoice_path)
                logger.info(f"Added OpenVoice path: {openvoice_path}")
            
            from openvoice.api import ToneColorConverter
            from openvoice import se_extractor
            from melo.api import TTS
            
            # EC2環境でのse_extractorのWhisperModelをパッチ
            import time
            import openvoice.se_extractor as se_module
            from faster_whisper import WhisperModel
            
            # 元の関数を保存
            original_split_audio_whisper = se_module.split_audio_whisper
            
            def patched_split_audio_whisper(audio_path, audio_name, target_dir='processed'):
                """パッチされたsplit_audio_whisper - EC2でGPUを正しく使用"""
                # se_moduleを関数内でインポート（スコープ問題を解決）
                import openvoice.se_extractor as se_mod
                import os
                import time
                if se_mod.model is None:
                    # EC2環境でGPUが利用可能かチェック
                    import torch
                    is_ec2 = os.path.exists('/home/ec2-user')
                    
                    if is_ec2 and torch.cuda.is_available():
                        device = "cuda"
                        compute_type = "float16"
                        logger.info(f"EC2環境: WhisperModelをGPUで初期化 (device={device}, compute_type={compute_type})")
                    else:
                        device = "cpu"
                        compute_type = "int8"
                        logger.info(f"WhisperModelをCPUで初期化 (device={device}, compute_type={compute_type})")
                    
                    init_start = time.time()
                    se_mod.model = WhisperModel(
                        se_mod.model_size,
                        device=device,
                        compute_type=compute_type,
                        cpu_threads=4 if device == "cpu" else 0,
                        num_workers=1
                    )
                    logger.info(f"WhisperModel初期化完了: {time.time() - init_start:.2f}秒")
                
                # 元の処理の詳細なタイミング付き実行
                from pydub import AudioSegment
                
                logger.info(f"音声ファイル読み込み開始: {audio_path}")
                load_start = time.time()
                audio = AudioSegment.from_file(audio_path)
                max_len = len(audio)
                logger.info(f"音声ファイル読み込み完了: {time.time() - load_start:.2f}秒, 長さ: {max_len/1000:.2f}秒")
                
                target_folder = os.path.join(target_dir, audio_name)
                
                # Transcribe with timing
                transcribe_start = time.time()
                logger.info(f"Whisper transcribe開始")
                segments, info = se_mod.model.transcribe(audio_path, beam_size=5, word_timestamps=True)
                segments = list(segments)
                logger.info(f"Whisper transcribe完了: {time.time() - transcribe_start:.2f}秒, セグメント数: {len(segments)}")
                
                # ディレクトリ作成
                os.makedirs(target_folder, exist_ok=True)
                wavs_folder = os.path.join(target_folder, 'wavs')
                os.makedirs(wavs_folder, exist_ok=True)
                
                # セグメント処理
                segment_start = time.time()
                s_ind = 0
                start_time = None
                saved_count = 0
                
                for k, w in enumerate(segments):
                    if k == 0:
                        start_time = max(0, w.start)
                    
                    end_time = w.end
                    
                    if len(w.words) > 0:
                        confidence = sum([s.probability for s in w.words]) / len(w.words)
                    else:
                        confidence = 0.
                    
                    text = w.text.replace('...', '')
                    
                    audio_seg = audio[int(start_time * 1000) : min(max_len, int(end_time * 1000) + 80)]
                    
                    fname = f"{audio_name}_seg{s_ind}.wav"
                    
                    save = audio_seg.duration_seconds > 1.5 and \
                            audio_seg.duration_seconds < 20. and \
                            len(text) >= 2 and len(text) < 200
                    
                    if save:
                        output_file = os.path.join(wavs_folder, fname)
                        audio_seg.export(output_file, format='wav')
                        saved_count += 1
                    
                    if k < len(segments) - 1:
                        start_time = max(0, segments[k+1].start - 0.08)
                    
                    s_ind = s_ind + 1
                
                logger.info(f"セグメント処理完了: {time.time() - segment_start:.2f}秒, 保存: {saved_count}個")
                return wavs_folder
            
            # モンキーパッチを適用
            se_module.split_audio_whisper = patched_split_audio_whisper
            logger.info("se_extractorのWhisperModelパッチ適用完了")
            
            logger.info("OpenVoiceライブラリのインポートに成功")
            return True
            
        except ImportError as e:
            logger.error(f"OpenVoiceインポートエラー: {str(e)}")
            # 詳細なインポートエラー情報
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _initialize_models(self) -> bool:
        """OpenVoiceモデルの初期化"""
        try:
            import torch
            
            # デバイス設定
            device = self.config.device
            logger.info(f"使用デバイス: {device}")
            
            # ToneColorConverter初期化
            self._tone_color_converter = ToneColorConverter(
                self.config.config_path, 
                device=device
            )
            self._tone_color_converter.load_ckpt(self.config.checkpoint_path)
            
            # TTS初期化
            self._models['ja'] = TTS(language='JP', device=device)
            self._models['en'] = TTS(language='EN', device=device)
            
            logger.info("OpenVoiceモデルの初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"モデル初期化エラー: {str(e)}")
            return False
    
    async def create_voice_clone(
        self, 
        name: str, 
        audio_files: List[bytes], 
        language: str = "ja",
        profile_id: Optional[str] = None
    ) -> VoiceCloneResponse:
        """音声クローン作成"""
        import time
        total_start = time.time()
        
        if not self._initialized:
            return VoiceCloneResponse(
                success=False,
                error="サービスが初期化されていません",
                message="OpenVoice Native Serviceの初期化が必要です"
            )
        
        # プロファイルID生成（バックエンドから指定された場合はそれを使用）
        if not profile_id:
            profile_id = f"openvoice_{uuid.uuid4().hex[:8]}"
        temp_files = []
        
        try:
            logger.info(f"音声クローン作成開始: {name} (ID: {profile_id})")
            
            # 音声ファイルを一時保存
            save_start = time.time()
            audio_paths = []
            for i, audio_data in enumerate(audio_files):
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=f"_sample_{i}.wav",
                    dir=self.config.temp_dir
                )
                temp_files.append(temp_file.name)
                
                async with aiofiles.open(temp_file.name, 'wb') as f:
                    await f.write(audio_data)
                
                audio_paths.append(temp_file.name)
            
            logger.info(f"音声ファイル保存完了: {time.time() - save_start:.2f}秒")
            
            # 最適化された音声特徴抽出
            extract_start = time.time()
            embedding_result = await self._extract_voice_embedding(audio_paths, language)
            logger.info(f"音声特徴抽出完了: {time.time() - extract_start:.2f}秒")
            if not embedding_result or 'embeddings' not in embedding_result:
                raise Exception("音声特徴の抽出に失敗しました")
            
            # 並列処理結果から最適な埋め込みを作成
            processed_embedding = await self._create_final_embedding(
                embedding_result, language
            )
            
            # プロファイル保存
            save_profile_start = time.time()
            profile = await self._save_voice_profile(
                profile_id, name, language, audio_paths, processed_embedding
            )
            logger.info(f"プロファイル保存完了: {time.time() - save_profile_start:.2f}秒")
            logger.info(f"=== 音声クローン作成総時間: {time.time() - total_start:.2f}秒 ===")
            
            # バックエンド用に埋め込みファイルのパスを返却
            return VoiceCloneResponse(
                success=True,
                voice_profile_id=profile_id,
                embedding_path=str(profile.embedding_path),  # 埋め込みファイルパスを追加
                message=f"音声クローン「{name}」の作成が完了しました"
            )
            
        except Exception as e:
            logger.error(f"音声クローン作成エラー: {str(e)}")
            return VoiceCloneResponse(
                success=False,
                error=str(e),
                message="音声クローンの作成に失敗しました"
            )
        
        finally:
            # 一時ファイル削除
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
    
    async def _extract_voice_embedding(
        self, 
        audio_paths: List[str], 
        language: str
    ) -> Optional[Dict]:
        """最適化された音声特徴抽出（並列処理・高速化）"""
        import time
        start_time = time.time()
        
        try:
            # 並列処理のためのプロファイリング
            logger.info(f"音声特徴抽出開始: {len(audio_paths)}サンプルを並列処理")
            
            # 音声ファイルの事前チェック（高速）
            valid_paths = []
            for audio_path in audio_paths:
                if not os.path.exists(audio_path):
                    logger.warning(f"音声ファイルが見つかりません: {audio_path}")
                    continue
                valid_paths.append(audio_path)
            
            if not valid_paths:
                raise Exception("有効な音声ファイルがありません")
            
            # 並列処理用のタスクを作成
            tasks = []
            for i, audio_path in enumerate(valid_paths):
                task = self._extract_single_embedding_optimized(audio_path, i)
                tasks.append(task)
            
            # 並列実行（最大3並列）
            import asyncio
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果の処理
            embeddings = []
            audio_names = []
            successful_extractions = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"サンプル {i+1} 処理失敗: {str(result)}")
                    continue
                
                if result and 'embedding' in result:
                    embeddings.append(result['embedding'])
                    audio_names.append(result['audio_name'])
                    successful_extractions += 1
                    logger.info(f"音声サンプル {i+1}/{len(valid_paths)} 処理完了")
            
            if successful_extractions == 0:
                raise Exception("すべての音声特徴抽出に失敗しました")
            
            elapsed_time = time.time() - start_time
            logger.info(f"音声特徴抽出完了: {successful_extractions}サンプル, 処理時間: {elapsed_time:.2f}秒")
            
            return {
                'embeddings': embeddings,
                'audio_names': audio_names,
                'processing_time': elapsed_time,
                'success_count': successful_extractions
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"音声特徴抽出エラー ({elapsed_time:.2f}秒): {str(e)}")
            return None
    
    async def _extract_single_embedding_optimized(self, audio_path: str, index: int) -> Optional[Dict]:
        """単一音声の最適化された特徴抽出"""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"音声特徴抽出開始: {audio_path}")
            
            # 音声ファイルの詳細情報を取得（高速）
            try:
                import librosa
                y, sr = librosa.load(audio_path, sr=22050)  # 固定サンプリングレートで高速化
                duration = len(y) / sr
                rms_energy = np.sqrt(np.mean(y**2))
                logger.info(f"音声ファイル詳細 - Duration: {duration:.2f}s, Energy: {rms_energy:.6f}, SR: {sr}Hz")
                
                # 早期品質チェック
                if duration < 1.0:
                    logger.warning(f"音声が短すぎます: {duration:.2f}秒")
                if rms_energy < 0.001:
                    logger.warning(f"音声エネルギーが低すぎます: {rms_energy:.6f}")
                        
            except Exception as info_error:
                logger.warning(f"音声ファイル情報取得失敗: {str(info_error)}")
            
            # 最適化されたWhisper処理
            try:
                import tempfile
                import shutil
                
                # メモリ内処理で一時ファイル最小化
                temp_dir = tempfile.mkdtemp(prefix=f"openvoice_opt_{index}_")
                temp_audio_path = os.path.join(temp_dir, f"temp_{os.path.basename(audio_path)}")
                
                # 高速ファイルコピー
                shutil.copy2(audio_path, temp_audio_path)
                
                # EC2環境では簡易モードを試す
                is_ec2 = os.path.exists('/home/ec2-user')
                
                if is_ec2 and os.getenv('OPENVOICE_FAST_MODE', 'false').lower() == 'true':
                    # 高速モード: Whisperをスキップして直接音声特徴を抽出
                    logger.info(f"高速モード: Whisperをスキップ (index={index})")
                    se_start = time.time()
                    
                    # 音声ファイルを直接処理（セグメント化せずに全体を使用）
                    audio_segs = [temp_audio_path]
                    se_save_path = os.path.join(temp_dir, 'se.pth')
                    reference_se = self._tone_color_converter.extract_se(audio_segs, se_save_path=se_save_path)
                    audio_name = f"fast_mode_{index}"
                    
                    logger.info(f"高速モード完了: {time.time() - se_start:.2f}秒")
                else:
                    # 通常モード: se_extractorを使用（最適化済み）
                    se_start = time.time()
                    logger.info(f"se_extractor.get_se開始 (index={index})")
                    reference_se, audio_name = se_extractor.get_se(
                        temp_audio_path, 
                        self._tone_color_converter, 
                        vad=False  # VADを無効化（Whisper処理）
                    )
                    logger.info(f"se_extractor.get_se完了: {time.time() - se_start:.2f}秒")
                
                # 一時ファイルを即座に削除
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                elapsed_time = time.time() - start_time
                logger.info(f"音声特徴抽出成功（最適化モード）: {audio_name} ({elapsed_time:.2f}秒)")
                
                return {
                    'embedding': reference_se,
                    'audio_name': audio_name,
                    'processing_time': elapsed_time
                }
                
            except Exception as extract_error:
                # フォールバック: 簡易処理（軽量化）
                logger.error(f"音声特徴抽出失敗: {str(extract_error)}")
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
                
                # 最適化失敗時の軽量フォールバック
                logger.info("フォールバック：軽量モードを試行")
                raise extract_error  # 完全にエラーとして扱う
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"音声特徴抽出完全失敗 ({elapsed_time:.2f}秒): {str(e)}")
            return None
    
    async def _create_final_embedding(
        self, 
        embedding_result: Dict, 
        language: str
    ) -> Dict:
        """並列処理結果から最終的な埋め込みを作成"""
        try:
            embeddings = embedding_result['embeddings']
            audio_names = embedding_result['audio_names']
            processing_time = embedding_result['processing_time']
            
            if not embeddings:
                raise Exception("有効な埋め込みがありません")
            
            # 複数サンプルの場合は平均化（MPSデバイス対応）
            if len(embeddings) > 1:
                logger.info(f"複数サンプルの平均化開始: {len(embeddings)}サンプル")
                
                # MPSデバイスの場合、CPUに移動してからNumPy変換
                cpu_embeddings = []
                for emb in embeddings:
                    if hasattr(emb, 'cpu'):
                        cpu_emb = emb.cpu().numpy() if hasattr(emb, 'numpy') else emb.cpu()
                        cpu_embeddings.append(cpu_emb)
                    else:
                        cpu_embeddings.append(emb)
                
                # 数値的な平均化
                averaged_embedding = np.mean(cpu_embeddings, axis=0)
                logger.info("埋め込み平均化完了")
            else:
                # 単一サンプルの場合
                emb = embeddings[0]
                if hasattr(emb, 'cpu'):
                    averaged_embedding = emb.cpu().numpy() if hasattr(emb, 'numpy') else emb.cpu()
                else:
                    averaged_embedding = emb
            
            return {
                'embedding': averaged_embedding,
                'language': language,
                'sample_count': len(embeddings),
                'audio_names': audio_names,
                'processing_time': processing_time,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"最終埋め込み作成エラー: {str(e)}")
            raise e
    
    async def _save_voice_profile(
        self, 
        profile_id: str, 
        name: str, 
        language: str, 
        audio_paths: List[str], 
        embedding: Dict
    ) -> VoiceProfile:
        """音声プロファイル保存"""
        
        # プロファイルディレクトリ作成
        profile_dir = self.config.voice_profiles_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # 参照音声ファイル保存
        reference_path = None
        for i, audio_path in enumerate(audio_paths):
            saved_path = profile_dir / f"sample_{i+1:02d}.wav"
            shutil.copy2(audio_path, saved_path)
            if i == 0:
                reference_path = str(saved_path)
        
        # 埋め込み保存（公式方式に準拠）
        embedding_filename = f"voice_clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        embedding_path = self.config.storage_dir / "openvoice" / embedding_filename
        embedding_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(embedding_path, 'wb') as f:
            await f.write(pickle.dumps(embedding))
        
        # プロファイル情報
        profile_data = {
            'id': profile_id,
            'name': name,
            'language': language,
            'created_at': datetime.now().isoformat(),
            'status': 'ready',
            'sample_count': len(audio_paths),
            'embedding_path': str(embedding_path),
            'reference_audio_path': reference_path
        }
        
        # プロファイル保存
        profile_file = profile_dir / "profile.json"
        async with aiofiles.open(profile_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(profile_data, ensure_ascii=False, indent=2))
        
        return VoiceProfile(**profile_data)
    
    async def synthesize_voice(
        self, 
        text: str, 
        voice_profile_id: str, 
        language: str = "ja",
        speed: float = 1.0
    ) -> VoiceSynthesisResponse:
        """音声合成"""
        
        if not self._initialized:
            return VoiceSynthesisResponse(
                success=False,
                error="サービスが初期化されていません",
                message="OpenVoice Native Serviceの初期化が必要です"
            )
        
        try:
            # プロファイル読み込み
            profile = await self._load_voice_profile(voice_profile_id)
            if not profile:
                return VoiceSynthesisResponse(
                    success=False,
                    error="音声プロファイルが見つかりません",
                    message=f"プロファイルID: {voice_profile_id}"
                )
            
            # 埋め込み読み込み
            embedding = await self._load_voice_embedding(profile['embedding_path'])
            if not embedding:
                return VoiceSynthesisResponse(
                    success=False,
                    error="音声埋め込みの読み込みに失敗",
                    message="埋め込みファイルが破損している可能性があります"
                )
            
            # 音声合成実行
            audio_data = await self._synthesize_with_embedding(
                text, embedding, language, speed
            )
            
            if not audio_data:
                return VoiceSynthesisResponse(
                    success=False,
                    error="音声合成に失敗しました",
                    message="OpenVoice V2による合成処理でエラーが発生"
                )
            
            # Base64エンコード
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            return VoiceSynthesisResponse(
                success=True,
                audio_data=audio_b64,
                message="音声合成が完了しました"
            )
            
        except Exception as e:
            logger.error(f"音声合成エラー: {str(e)}")
            return VoiceSynthesisResponse(
                success=False,
                error=str(e),
                message="音声合成処理中にエラーが発生しました"
            )
    
    async def _load_voice_profile(self, profile_id: str) -> Optional[Dict]:
        """音声プロファイル読み込み"""
        try:
            profile_file = self.config.voice_profiles_dir / profile_id / "profile.json"
            if not profile_file.exists():
                return None
            
            async with aiofiles.open(profile_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"プロファイル読み込みエラー: {str(e)}")
            return None
    
    async def _load_voice_embedding(self, embedding_path: str) -> Optional[Dict]:
        """音声埋め込み読み込み"""
        try:
            # Dockerパスからローカルパスに変換
            if embedding_path.startswith('/app/'):
                # /app/storage/... をローカルパスに変換
                local_path = embedding_path.replace('/app/storage/', str(self.config.storage_dir) + '/')
                logger.info(f"パス変換: {embedding_path} -> {local_path}")
                embedding_path = local_path
            
            # ファイル存在確認
            if not os.path.exists(embedding_path):
                logger.error(f"埋め込みファイルが存在しません: {embedding_path}")
                return None
            
            async with aiofiles.open(embedding_path, 'rb') as f:
                content = await f.read()
                return pickle.loads(content)
        except Exception as e:
            logger.error(f"埋め込み読み込みエラー: {str(e)}")
            return None
    
    async def _synthesize_with_embedding(
        self, 
        text: str, 
        embedding: Dict, 
        language: str, 
        speed: float
    ) -> Optional[bytes]:
        """埋め込みを使用した音声合成（OpenVoice V2公式方式）"""
        try:
            import torch
            
            # TTSモデル取得
            tts_model = self._models.get(language, self._models['ja'])
            
            # 一時ファイル生成
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # 基本音声生成
                speaker_ids = tts_model.hps.data.spk2id
                speaker_key = list(speaker_ids.keys())[0]
                speaker_id = speaker_ids[speaker_key]
                
                # MPS バックエンドの問題回避
                if torch.backends.mps.is_available() and self.config.device == 'cpu':
                    torch.backends.mps.is_available = lambda: False
                
                tts_model.tts_to_file(text, speaker_id, temp_path, speed=speed)
                
                # ベーススピーカー埋め込み読み込み（公式方式）
                speaker_key_normalized = speaker_key.lower().replace('_', '-')
                base_speaker_path = self.config.speakers_dir / f"{speaker_key_normalized}.pth"
                
                if not base_speaker_path.exists():
                    # フォールバック：日本語ベーススピーカー
                    base_speaker_path = self.config.speakers_dir / "jp.pth"
                
                source_se = torch.load(str(base_speaker_path), map_location=self.config.device)
                
                # 音色変換（公式方式：src_se=ベース, tgt_se=ターゲット）
                output_path = temp_path.replace('.wav', '_converted.wav')
                
                # 埋め込みをTensorに変換（MPS対応）
                import torch
                if isinstance(embedding['embedding'], np.ndarray):
                    tgt_se_tensor = torch.from_numpy(embedding['embedding']).to(self.config.device)
                else:
                    tgt_se_tensor = embedding['embedding']
                
                self._tone_color_converter.convert(
                    audio_src_path=temp_path,
                    src_se=source_se,  # ベーススピーカー埋め込み
                    tgt_se=tgt_se_tensor,  # ターゲット（クローン）埋め込み
                    output_path=output_path,
                    message="@OpenVoiceClone"  # 公式サンプルに準拠
                )
                
                # 結果読み込み
                async with aiofiles.open(output_path, 'rb') as f:
                    audio_data = await f.read()
                
                return audio_data
                
            finally:
                # 一時ファイル削除
                for path in [temp_path, temp_path.replace('.wav', '_converted.wav')]:
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"音声合成エラー: {str(e)}")
            return None
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        model_files_status = {
            'checkpoint': os.path.exists(self.config.checkpoint_path),
            'config': os.path.exists(self.config.config_path),
            'japanese_speaker': os.path.exists(self.config.japanese_speaker_path),
            'english_speaker': os.path.exists(self.config.english_speaker_path)
        }
        
        return {
            'status': 'healthy' if self._initialized else 'initializing',
            'service': 'OpenVoice Native Service',
            'version': '1.0.0',
            'openvoice_available': self._initialized,
            'pytorch_device': self.config.device,
            'model_files_status': model_files_status
        }