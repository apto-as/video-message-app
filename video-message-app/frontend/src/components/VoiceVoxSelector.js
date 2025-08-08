import React, { useState, useEffect } from 'react';
import './VoiceVoxSelector.css';

// API URLの設定（環境変数から取得、デフォルトは55433）
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:55433';

const VoiceVoxSelector = ({ onVoiceSelect, selectedVoice, showCloneOption = true }) => {
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('voicevox');
  const [testText, setTestText] = useState('こんにちは、VOICEVOXの音声テストです。');
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    loadVoices();
  }, [activeTab]);

  const loadVoices = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let endpoint;
      
      switch (activeTab) {
        case 'voicevox':
          endpoint = '/api/voicevox/speakers/popular';
          break;
        case 'openvoice':
          endpoint = '/api/unified-voice/voices?provider=openvoice';
          break;
        default:
          endpoint = '/api/unified-voice/voices';
      }
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      
      if (!response.ok) {
        throw new Error(`音声一覧の取得に失敗しました: ${response.status}`);
      }
      
      const data = await response.json();
      setVoices(Array.isArray(data) ? data : []);
      
    } catch (err) {
      setError(err.message);
      setVoices([]);
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceSelect = (voice) => {
    const voiceData = {
      id: voice.id || voice.style_id,
      name: voice.name || `${voice.speaker_name} (${voice.style_name})`,
      provider: activeTab,
      speakerId: voice.style_id || voice.speaker_id,
      language: voice.language || 'ja',
      metadata: voice
    };
    
    onVoiceSelect(voiceData);
  };

  const testVoice = async (voice) => {
    if (isPlaying) return;
    
    setIsPlaying(true);
    
    try {
      let endpoint;
      let requestBody;
      
      if (activeTab === 'voicevox') {
        endpoint = '/api/voicevox/synthesis';
        requestBody = {
          text: testText,
          speaker_id: voice.style_id,
          speed_scale: 1.0,
          preset: 'normal'
        };
      } else {
        endpoint = '/api/unified-voice/synthesize';
        requestBody = {
          text: testText,
          voice_profile: {
            id: voice.id,
            name: voice.name,
            provider: activeTab,
            voice_type: voice.voice_type || 'preset',
            language: voice.language || 'ja',
            speaker_id: voice.style_id
          },
          speed: 1.0
        };
      }
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error('音声テストに失敗しました');
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
      
    } catch (err) {
      setError(`音声テストエラー: ${err.message}`);
      setIsPlaying(false);
    }
  };

  const renderVoiceCard = (voice, index) => {
    const isSelected = selectedVoice && 
      (selectedVoice.id === voice.id || selectedVoice.id === voice.style_id);
    
    return (
      <div 
        key={voice.id || voice.style_id || index}
        className={`voice-card ${isSelected ? 'selected' : ''}`}
        onClick={() => handleVoiceSelect(voice)}
      >
        <div className="voice-info">
          <h4 className="voice-name">
            {voice.name || `${voice.speaker_name} (${voice.style_name})`}
          </h4>
          
          {voice.language && (
            <span className="voice-language">{voice.language.toUpperCase()}</span>
          )}
          
          {voice.voice_type && (
            <span className={`voice-type ${voice.voice_type}`}>
              {voice.voice_type === 'preset' ? 'プリセット' : 
               voice.voice_type === 'cloned' ? 'クローン' : 'カスタム'}
            </span>
          )}
        </div>
        
        <div className="voice-actions">
          <button
            className="test-button"
            onClick={(e) => {
              e.stopPropagation();
              testVoice(voice);
            }}
            disabled={isPlaying}
            title="音声をテスト"
          >
            {isPlaying ? '🔄' : '🔊'}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="voicevox-selector">
      <div className="selector-header">
        <h3>🎙️ 音声選択</h3>
        
        <div className="voice-tabs">
          <button
            className={`tab ${activeTab === 'voicevox' ? 'active' : ''}`}
            onClick={() => setActiveTab('voicevox')}
          >
            VOICEVOX
          </button>
          
          {showCloneOption && (
            <>
              <button
                className={`tab ${activeTab === 'openvoice' ? 'active' : ''}`}
                onClick={() => setActiveTab('openvoice')}
              >
                OpenVoice
              </button>
            </>
          )}
        </div>
      </div>

      {activeTab === 'voicevox' && (
        <div className="test-section">
          <label>テスト文章:</label>
          <input
            type="text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="音声テスト用の文章を入力"
            className="test-input"
          />
        </div>
      )}

      <div className="voices-container">
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>音声一覧を読み込み中...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <p>❌ {error}</p>
            <button onClick={loadVoices} className="retry-button">
              再試行
            </button>
          </div>
        )}

        {!loading && !error && voices.length === 0 && (
          <div className="empty-state">
            <p>利用可能な音声がありません</p>
            {activeTab !== 'voicevox' && (
              <p className="hint">
                音声クローンを作成してください
              </p>
            )}
          </div>
        )}

        {!loading && !error && voices.length > 0 && (
          <div className="voices-grid">
            {voices.map(renderVoiceCard)}
          </div>
        )}
      </div>

      {selectedVoice && (
        <div className="selected-voice-info">
          <h4>選択中の音声:</h4>
          <p><strong>{selectedVoice.name}</strong></p>
          <p>プロバイダー: {selectedVoice.provider?.toUpperCase()}</p>
          {selectedVoice.language && (
            <p>言語: {selectedVoice.language.toUpperCase()}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceVoxSelector;