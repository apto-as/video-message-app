import axios from 'axios';
import { API_CONFIG, getApiEndpoint } from '../config/api.config';

// API設定を統一管理から取得
const API_BASE_URL = API_CONFIG.API_URL;

// VOICEVOX音声合成（2段階処理：音声生成→リップシンク動画生成）
export const generateVideoWithVoicevox = async (imageFile, text, voiceData = null, audioParams = {}, bgmId = null) => {
  try {
    // Step 1: VOICEVOX音声合成
    const voiceRequest = {
      text: text,
      speaker_id: (voiceData && voiceData.speakerId) ? voiceData.speakerId : (voiceData?.id || 3),
      speed_scale: audioParams.speed_scale || 1.0,
      pitch_scale: audioParams.pitch_scale || 0.0,
      intonation_scale: audioParams.intonation_scale || 1.0,
      volume_scale: audioParams.volume_scale || 1.0,
      pause_length: audioParams.pause_duration || 0.0
    };

    const voiceResponse = await axios.post(`${API_BASE_URL}/voicevox/synthesis`, voiceRequest, {
      headers: {
        'Content-Type': 'application/json',
      },
      responseType: 'blob',
      timeout: 30000
    });

    // 音声BlobからURLを作成
    const audioBlob = new Blob([voiceResponse.data], { type: 'audio/wav' });
    const audioUrl = URL.createObjectURL(audioBlob);

    // Step 2: リップシンク動画生成（MuseTalk経由）
    const videoResult = await generateVideoWithLipsync(audioUrl, imageFile, {}, bgmId);

    return {
      success: true,
      video_url: videoResult.video_url,
      audio_url: audioUrl
    };

  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('VOICEVOX動画生成に失敗しました');
    }
  }
};

// Voice Clone音声合成（2段階処理：音声生成→リップシンク動画生成）
export const generateVideoWithClonedVoice = async (imageFile, text, voiceData = null, audioParams = {}, bgmId = null) => {
  try {
    // 【緊急修正】voice_profileオブジェクトとして送信
    const voiceRequest = {
      text: text,
      voice_profile: voiceData ? {
        id: voiceData.id,
        name: voiceData.name || 'Unknown',
        provider: 'voice-clone'
      } : null,
      speed: audioParams.speed || 1.0,
      pitch: audioParams.pitch || 0.0,
      volume: audioParams.volume || 1.0,
      emotion: audioParams.emotion || 'neutral',
      pause_duration: audioParams.pause_duration || 0.0
    };

    // Debug output removed for production

    const voiceResponse = await axios.post(`${API_BASE_URL}/unified-voice/synthesize`, voiceRequest, {
      headers: {
        'Content-Type': 'application/json',
      },
      responseType: 'blob',
      timeout: 180000 // Qwen TTS: first call may take 60+ seconds for model loading
    });

    // 音声BlobからURLを作成
    const audioBlob = new Blob([voiceResponse.data], { type: 'audio/wav' });
    const audioUrl = URL.createObjectURL(audioBlob);

    // Audio synthesis successful

    // Step 2: リップシンク動画生成（MuseTalk経由）
    const videoResult = await generateVideoWithLipsync(audioUrl, imageFile, {}, bgmId);

    return {
      success: true,
      video_url: videoResult.video_url,
      audio_url: audioUrl
    };

  } catch (error) {
    // Log error to monitoring service in production
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('Voice Clone動画生成に失敗しました');
    }
  }
};

// 音声クローン機能
export const cloneVoice = async (audioFile, voiceName, provider = 'voice-clone', language = 'ja') => {
  const formData = new FormData();
  formData.append('audio_file', audioFile);
  formData.append('voice_name', voiceName);
  formData.append('provider', provider);
  formData.append('language', language);

  try {
    const response = await axios.post(`${API_BASE_URL}/unified-voice/clone`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 180000, // 3分タイムアウト（音声クローン処理は時間がかかる）
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('音声クローンに失敗しました');
    }
  }
};


export const getVoices = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/voices`, {
      timeout: 10000, // 10秒タイムアウト
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('音声一覧の取得に失敗しました');
    }
  }
};

export const getCustomVoices = async (userId = 'default') => {
  try {
    const response = await axios.get(`${API_BASE_URL}/voices/custom`, {
      params: { user_id: userId },
      timeout: 10000,
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('カスタム音声一覧の取得に失敗しました');
    }
  }
};

// テスト用音声生成（既存サンプル使用）
export const generateTestVoice = async (text = "こんにちは。これは既存サンプルを使用したテスト音声です。") => {
  try {
    const formData = new FormData();
    formData.append('text', text);

    const response = await axios.post(`${API_BASE_URL}/voice-clone/test-generate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
      timeout: 120000, // 音声生成は時間がかかる
    });

    // 音声BlobからURLを作成
    const audioBlob = new Blob([response.data], { type: 'audio/wav' });
    const audioUrl = URL.createObjectURL(audioBlob);

    // Test voice generation successful

    return {
      success: true,
      audio_url: audioUrl,
      audio_size: audioBlob.size,
      profile_id: response.headers['x-profile-id']
    };

  } catch (error) {
    // Error handling for test voice generation
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('テスト音声生成に失敗しました');
    }
  }
};

// 音声プロファイルテスト
export const testVoiceProfile = async (profileId, text = "こんにちは、音声クローンのテストです") => {
  try {
    const formData = new FormData();
    formData.append('text', text);

    const response = await axios.post(`${API_BASE_URL}/voice-clone/test/${profileId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
      timeout: 60000, // 音声合成は時間がかかる
    });

    // 音声BlobからURLを作成
    const audioBlob = new Blob([response.data], { type: 'audio/wav' });
    const audioUrl = URL.createObjectURL(audioBlob);

    // Voice test successful

    return {
      success: true,
      audio_url: audioUrl,
      audio_size: audioBlob.size,
      profile_name: response.headers['x-profile-name'],
      native_service: response.headers['x-native-service'] === 'true'
    };

  } catch (error) {
    // Error handling for voice test
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('音声テストに失敗しました');
    }
  }
};

// リップシンク動画生成（MuseTalk経由）
export const generateVideoWithLipsync = async (audioUrl, imageFile = null, options = {}, bgmId = null) => {
  try {
    // 画像ファイルが必須であることを確認
    if (!imageFile) {
      throw new Error('リップシンク動画生成には画像ファイルが必要です');
    }

    // 画像をアップロード
    const imageFormData = new FormData();
    imageFormData.append('file', imageFile);

    const imageUploadResponse = await axios.post(`${API_BASE_URL}/lipsync/upload-source-image`, imageFormData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 30000,
    });

    const sourceUrl = imageUploadResponse.data.url;

    // 音声がBlob URLの場合、実際のファイルに変換してアップロード
    let uploadedAudioUrl = audioUrl;
    if (audioUrl.startsWith('blob:')) {
      // Blob URLからBlobを取得
      const audioResponse = await fetch(audioUrl);
      const audioBlob = await audioResponse.blob();

      // BlobをFileに変換
      const audioFile = new File([audioBlob], 'audio.wav', { type: audioBlob.type || 'audio/wav' });

      // 音声をアップロード
      const audioFormData = new FormData();
      audioFormData.append('file', audioFile);

      const audioUploadResponse = await axios.post(`${API_BASE_URL}/lipsync/upload-audio`, audioFormData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000,
      });

      uploadedAudioUrl = audioUploadResponse.data.url;
    }

    // リップシンク動画生成リクエスト（MuseTalk経由）
    const requestData = {
      audio_url: uploadedAudioUrl,
      source_url: sourceUrl,
      ...(bgmId && { bgm_id: bgmId })
    };

    const response = await axios.post(`${API_BASE_URL}/lipsync/generate-video`, requestData, {
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 300000, // 5分タイムアウト（リップシンク処理は時間がかかる）
    });

    return {
      success: true,
      video_url: response.data.result_url,
      video_id: response.data.id,
      status: response.data.status
    };
  } catch (error) {
    // Error handling for lipsync video generation
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('リップシンク動画生成に失敗しました');
    }
  }
};

// リップシンク動画生成のみサポート

// ===== Person Detection API =====

/**
 * 画像から人物を検出
 * @param {File} imageFile - 画像ファイル
 * @param {number} confThreshold - 信頼度閾値 (0.0-1.0)
 * @returns {Promise<Object>} - 検出結果
 */
export const detectPersons = async (imageFile, confThreshold = 0.5) => {
  const formData = new FormData();
  formData.append('image', imageFile);

  try {
    const response = await axios.post(
      `${API_BASE_URL}/person-detection/detect?conf_threshold=${confThreshold}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000,
      }
    );

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('人物検出に失敗しました');
    }
  }
};

/**
 * 選択した人物のみを抽出（背景と他の人物を削除）
 * @param {File} imageFile - 画像ファイル
 * @param {number[]} selectedPersonIds - 残す人物のID配列
 * @param {number} confThreshold - 信頼度閾値
 * @param {number} padding - パディング（ピクセル）
 * @param {boolean} addTransparentPadding - 透明パディングを追加するか（デフォルト: true）
 * @param {number} transparentPaddingSize - 透明パディングのサイズ（ピクセル、デフォルト: 300）
 * @returns {Promise<Object>} - 抽出結果（Base64画像含む）
 */
export const extractSelectedPersons = async (
  imageFile,
  selectedPersonIds,
  confThreshold = 0.5,
  padding = 20,
  addTransparentPadding = true,
  transparentPaddingSize = 300
) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('selected_person_ids', JSON.stringify(selectedPersonIds));
  formData.append('conf_threshold', confThreshold);
  formData.append('padding', padding);
  formData.append('add_transparent_padding', addTransparentPadding);
  formData.append('transparent_padding_size', transparentPaddingSize);

  try {
    const response = await axios.post(
      `${API_BASE_URL}/person-detection/extract-person`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2分タイムアウト（背景削除は時間がかかる）
      }
    );

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('人物抽出に失敗しました');
    }
  }
};

/**
 * Person Detection APIのヘルスチェック
 * @returns {Promise<Object>} - ヘルス状態
 */
export const getPersonDetectionHealth = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/person-detection/health`, {
      timeout: 10000,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'サーバーエラー');
    } else if (error.request) {
      throw new Error('ネットワークエラー');
    } else {
      throw new Error('ヘルスチェックに失敗しました');
    }
  }
};

