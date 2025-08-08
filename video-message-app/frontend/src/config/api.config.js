// API Configuration - 統一的なAPI設定管理
// このファイルがすべてのAPI URLの唯一の管理場所

const getApiBaseUrl = () => {
  // 環境変数から取得、EC2用にHTTPSを使用
  const baseUrl = process.env.REACT_APP_API_BASE_URL || 'https://3.115.141.166';
  
  // baseUrlが既に/apiを含んでいる場合は削除
  const cleanUrl = baseUrl.replace(/\/api\/?$/, '');
  
  return cleanUrl;
};

export const API_CONFIG = {
  BASE_URL: getApiBaseUrl(),
  API_URL: `${getApiBaseUrl()}/api`,
  
  // 各エンドポイントの定義
  ENDPOINTS: {
    // Health check
    HEALTH: '/health',
    
    // VoiceVox関連
    VOICEVOX_SPEAKERS: '/voicevox/speakers',
    VOICEVOX_SPEAKERS_POPULAR: '/voicevox/speakers/popular',
    VOICEVOX_SYNTHESIS: '/voicevox/synthesis',
    
    // Voice Clone関連
    VOICE_CLONE_PROFILES: '/voice-clone/profiles',
    VOICE_CLONE_REGISTER: '/voice-clone/register',
    VOICE_CLONE_TEST: '/voice-clone/test',
    
    // Unified Voice関連
    UNIFIED_VOICE_LIST: '/unified-voice/voices',
    UNIFIED_VOICE_SYNTHESIZE: '/unified-voice/synthesize',
    UNIFIED_VOICE_CLONE: '/unified-voice/clone',
    
    // D-ID関連
    DID_UPLOAD_IMAGE: '/d-id/upload-source-image',
    DID_UPLOAD_AUDIO: '/d-id/upload-audio',
    DID_GENERATE_VIDEO: '/d-id/generate-video',
    
    // Background Processing
    PROCESS_IMAGE: '/process-image',
    PROCESS_BACKGROUND: '/background/process',
  }
};

// APIエンドポイントの完全なURLを取得する関数
export const getApiEndpoint = (endpoint) => {
  return `${API_CONFIG.API_URL}${endpoint}`;
};

// デバッグ用（開発時のみ）
if (process.env.NODE_ENV === 'development') {
  console.log('API Configuration:', {
    BASE_URL: API_CONFIG.BASE_URL,
    API_URL: API_CONFIG.API_URL,
    ENV_VAR: process.env.REACT_APP_API_BASE_URL
  });
}

export default API_CONFIG;