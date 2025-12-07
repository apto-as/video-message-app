"""
VOICEVOX統合クライアント
日本語特化音声合成システム
"""

import httpx
import asyncio
import json
import base64
import io
from typing import Dict, List, Optional, Union
from pathlib import Path
import aiofiles

class VOICEVOXClient:
    """VOICEVOX Engine APIクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:50021"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
        self._speakers_cache: Optional[List[Dict]] = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, str]:
        """VOICEVOX Engineのヘルスチェック"""
        try:
            response = await self.client.get(f"{self.base_url}/version")
            response.raise_for_status()
            return {"status": "healthy", "version": response.text.strip('"')}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_speakers(self) -> List[Dict]:
        """利用可能な話者一覧を取得"""
        if self._speakers_cache is None:
            try:
                response = await self.client.get(f"{self.base_url}/speakers")
                response.raise_for_status()
                self._speakers_cache = response.json()
            except Exception as e:
                raise Exception(f"話者情報の取得に失敗: {str(e)}")
        
        return self._speakers_cache
    
    async def get_speaker_info(self, speaker_id: int) -> Optional[Dict]:
        """特定の話者情報を取得"""
        speakers = await self.get_speakers()
        
        for speaker in speakers:
            for style in speaker.get('styles', []):
                if style.get('id') == speaker_id:
                    return {
                        'speaker_name': speaker.get('name'),
                        'speaker_uuid': speaker.get('speaker_uuid'),
                        'style_name': style.get('name'),
                        'style_id': style.get('id'),
                        'version': speaker.get('version')
                    }
        return None
    
    async def audio_query(self, text: str, speaker_id: int) -> Dict:
        """音声クエリを生成（音声合成の前処理）"""
        try:
            params = {
                'text': text,
                'speaker': speaker_id
            }
            
            response = await self.client.post(
                f"{self.base_url}/audio_query",
                params=params
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise Exception(f"音声クエリ生成エラー: {str(e)}")
    
    async def synthesis(self, audio_query: Dict, speaker_id: int) -> bytes:
        """音声合成実行"""
        try:
            params = {'speaker': speaker_id}
            headers = {'Content-Type': 'application/json'}
            
            response = await self.client.post(
                f"{self.base_url}/synthesis",
                params=params,
                json=audio_query,
                headers=headers
            )
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            raise Exception(f"音声合成エラー: {str(e)}")
    
    async def text_to_speech(
        self,
        text: str,
        speaker_id: int = 1,  # デフォルト: 四国めたん（ノーマル）
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
        volume_scale: float = 1.0,
        pause_length: float = 0.0  # 追加ポーズ長（秒）
    ) -> bytes:
        """テキストから音声を生成（ワンストップAPI）

        Args:
            text: 読み上げるテキスト
            speaker_id: 話者ID
            speed_scale: 速度（0.5-2.0）
            pitch_scale: ピッチ（-0.15-0.15）
            intonation_scale: 抑揚（0.0-2.0）
            volume_scale: 音量（0.0-2.0）
            pause_length: 文末などのポーズに追加する長さ（秒、0.0-3.0）
        """

        # 1. 音声クエリ生成
        audio_query = await self.audio_query(text, speaker_id)

        # 2. パラメータ調整
        audio_query['speedScale'] = speed_scale
        audio_query['pitchScale'] = pitch_scale
        audio_query['intonationScale'] = intonation_scale
        audio_query['volumeScale'] = volume_scale

        # 3. ポーズ長の調整（pause_moraのvowel_lengthを増加）
        if pause_length > 0.0:
            for accent_phrase in audio_query.get('accent_phrases', []):
                pause_mora = accent_phrase.get('pause_mora')
                if pause_mora:
                    # 既存のポーズ長に追加
                    original_length = pause_mora.get('vowel_length', 0.0)
                    pause_mora['vowel_length'] = original_length + pause_length

        # 4. 音声合成
        return await self.synthesis(audio_query, speaker_id)
    
    async def save_audio(
        self, 
        audio_data: bytes, 
        file_path: str,
        format: str = "wav"
    ) -> str:
        """音声データをファイルに保存"""
        
        if format.lower() not in ['wav', 'mp3']:
            raise ValueError("サポートされていない形式です。wav または mp3 を指定してください。")
        
        # ファイル拡張子を確認・修正
        path = Path(file_path)
        if path.suffix.lower() != f'.{format.lower()}':
            file_path = str(path.with_suffix(f'.{format.lower()}'))
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(audio_data)
            return file_path
        except Exception as e:
            raise Exception(f"音声ファイル保存エラー: {str(e)}")
    
    async def get_popular_speakers(self) -> List[Dict]:
        """よく使われる話者を推奨順で取得"""
        speakers = await self.get_speakers()
        
        # 人気の話者を選定（ID順）
        popular_speaker_ids = [
            1,  # 四国めたん（ノーマル）
            3,  # 春日部つむぎ（ノーマル）
            2,  # ずんだもん（ノーマル）
            20, # もち子さん（ノーマル）
            8,  # 春日部つむぎ（ささやき）
            10, # 雨晴はう（ノーマル）
            14, # 冥鳴ひまり（ノーマル）
            16, # No.7（ノーマル）
        ]
        
        popular_speakers = []
        for speaker in speakers:
            for style in speaker.get('styles', []):
                if style.get('id') in popular_speaker_ids:
                    popular_speakers.append({
                        'speaker_name': speaker.get('name'),
                        'style_name': style.get('name'),
                        'style_id': style.get('id'),
                        'speaker_uuid': speaker.get('speaker_uuid'),
                        'order': popular_speaker_ids.index(style.get('id'))
                    })
        
        # 推奨順でソート
        return sorted(popular_speakers, key=lambda x: x['order'])
    
    async def batch_synthesis(
        self, 
        texts: List[str], 
        speaker_id: int = 1,
        **synthesis_params
    ) -> List[bytes]:
        """複数テキストの一括音声合成"""
        
        audio_results = []
        
        for text in texts:
            try:
                audio_data = await self.text_to_speech(text, speaker_id, **synthesis_params)
                audio_results.append(audio_data)
            except Exception as e:
                # エラーの場合は空のバイトデータを追加
                print(f"音声合成エラー (テキスト: '{text}'): {str(e)}")
                audio_results.append(b'')
        
        return audio_results
    
    async def estimate_speech_time(self, text: str, speaker_id: int = 1) -> float:
        """発話時間の推定（秒）"""
        try:
            audio_query = await self.audio_query(text, speaker_id)
            
            # accent_phrasesから発話時間を計算
            total_time = 0.0
            for accent_phrase in audio_query.get('accent_phrases', []):
                for mora in accent_phrase.get('moras', []):
                    total_time += mora.get('vowel_length', 0.0)
                    consonant_length = mora.get('consonant_length')
                    if consonant_length:
                        total_time += consonant_length
                
                # ポーズ時間も追加
                pause_mora = accent_phrase.get('pause_mora')
                if pause_mora:
                    total_time += pause_mora.get('vowel_length', 0.0)
            
            return total_time
            
        except Exception as e:
            # エラー時は文字数ベースの推定（日本語: 約3文字/秒）
            return len(text) / 3.0


# ユーティリティ関数
async def get_voicevox_client(base_url: str = None) -> VOICEVOXClient:
    """VOICEVOXクライアントを取得"""
    import os
    
    if base_url is None:
        base_url = os.getenv('VOICEVOX_BASE_URL', 'http://localhost:50021')
    
    return VOICEVOXClient(base_url)


# 音声品質設定プリセット
VOICE_PRESETS = {
    'normal': {
        'speed_scale': 1.0,
        'pitch_scale': 0.0,
        'intonation_scale': 1.0,
        'volume_scale': 1.0
    },
    'slow': {
        'speed_scale': 0.8,
        'pitch_scale': 0.0,
        'intonation_scale': 1.1,
        'volume_scale': 1.0
    },
    'fast': {
        'speed_scale': 1.3,
        'pitch_scale': 0.0,
        'intonation_scale': 0.9,
        'volume_scale': 1.0
    },
    'gentle': {
        'speed_scale': 0.9,
        'pitch_scale': -0.1,
        'intonation_scale': 0.8,
        'volume_scale': 0.9
    },
    'energetic': {
        'speed_scale': 1.2,
        'pitch_scale': 0.1,
        'intonation_scale': 1.2,
        'volume_scale': 1.1
    }
}