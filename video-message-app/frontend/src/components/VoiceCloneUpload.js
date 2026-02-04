import React, { useState, useRef, useEffect } from 'react';
import './VoiceCloneUpload.css';
import { getApiEndpoint, API_CONFIG } from '../config/api.config.js';

const VoiceCloneUpload = ({ onUploadComplete, onProfileUpdate }) => {
  const [activeTab, setActiveTab] = useState('create'); // 'create' or 'manage'
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [profileName, setProfileName] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('ja');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [voiceProfiles, setVoiceProfiles] = useState([]);
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);

  // プロファイル一覧を読み込み
  const loadVoiceProfiles = async () => {
    setLoadingProfiles(true);
    try {
      const apiUrl = getApiEndpoint(API_CONFIG.ENDPOINTS.VOICE_CLONE_PROFILES);
      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error('プロファイル一覧の取得に失敗しました');
      }
      
      const profiles = await response.json();
      setVoiceProfiles(profiles);
    } catch (err) {
      setError(err.message);
      console.error('プロファイル読み込みエラー:', err);
    } finally {
      setLoadingProfiles(false);
    }
  };

  // プロファイル削除
  const deleteVoiceProfile = async (profileId) => {
    if (!window.confirm('この音声プロファイルを削除しますか？この操作は元に戻せません。')) {
      return;
    }

    try {
      const apiUrl = `${getApiEndpoint(API_CONFIG.ENDPOINTS.VOICE_CLONE_PROFILES)}/${profileId}`;
      const response = await fetch(apiUrl, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('プロファイルの削除に失敗しました');
      }

      const result = await response.json();
      
      if (result.success) {
        setSuccess('プロファイルが削除されました');
        await loadVoiceProfiles(); // 一覧を再読み込み
        // 親コンポーネントにプロファイル更新を通知
        if (onProfileUpdate) {
          onProfileUpdate();
        }
      } else {
        throw new Error(result.message || 'プロファイルの削除に失敗しました');
      }
    } catch (err) {
      setError(err.message);
      console.error('プロファイル削除エラー:', err);
    }
  };

  // テスト用音声生成（既存サンプル使用）
  const generateTestVoice = async () => {
    try {
      const testText = 'こんにちは。これは既存サンプルを使用したテスト音声です。音声クローン機能が正常に動作しているかを確認しています。';
      
      // 専用のAPIメソッドを使用
      const { generateTestVoice: apiGenerateTestVoice } = await import('../services/api');
      const result = await apiGenerateTestVoice(testText);
      
      if (result.success && result.audio_url) {
        // 音声を再生
        const audio = new Audio(result.audio_url);
        audio.play().then(() => {
          console.log('テスト音声再生開始');
          console.log('Audio size:', result.audio_size, 'bytes');
          console.log('Profile ID:', result.profile_id);
        }).catch(playError => {
          console.error('音声再生エラー:', playError);
          throw new Error('音声の再生に失敗しました');
        });
        
        setSuccess(`テスト音声を再生しました (${result.audio_size} bytes, プロファイル: ${result.profile_id})`);
      } else {
        throw new Error('テスト音声データの取得に失敗しました');
      }
      
    } catch (err) {
      const errorMessage = `テスト音声生成失敗: ${err.message}`;
      setError(errorMessage);
      console.error('テスト音声生成エラー:', {
        error: err,
        errorMessage: err.message
      });
    }
  };

  // プロファイルテスト（音声合成テスト）
  const testVoiceProfile = async (profileId, profileName) => {
    try {
      const testText = 'こんにちは、これは音声プロファイルのテストです。';
      
      // 専用のAPIメソッドを使用
      const { testVoiceProfile: apiTestVoiceProfile } = await import('../services/api');
      const result = await apiTestVoiceProfile(profileId, testText);
      
      if (result.success && result.audio_url) {
        // 音声を再生
        const audio = new Audio(result.audio_url);
        audio.play().then(() => {
          console.log('音声再生開始');
          console.log('Audio size:', result.audio_size, 'bytes');
          console.log('Profile name:', result.profile_name);
          console.log('Native service used:', result.native_service);
        }).catch(playError => {
          console.error('音声再生エラー:', playError);
          throw new Error('音声の再生に失敗しました');
        });
        
        setSuccess(`「${profileName}」のテスト音声を再生しました (${result.audio_size} bytes)`);
      } else {
        throw new Error('音声データの取得に失敗しました');
      }
      
    } catch (err) {
      const errorMessage = `音声テスト失敗: ${err.message}`;
      setError(errorMessage);
      console.error('音声テストエラー:', {
        profileId,
        profileName,
        error: err,
        errorMessage: err.message
      });
    }
  };

  // コンポーネントマウント時にプロファイル一覧を読み込み
  useEffect(() => {
    if (activeTab === 'manage') {
      loadVoiceProfiles();
    }
  }, [activeTab]);

  // 録音開始
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const fileName = `録音_${new Date().toLocaleTimeString('ja-JP')}.wav`;
        
        setRecordings(prev => [...prev, {
          blob: audioBlob,
          url: audioUrl,
          name: fileName,
          duration: '録音完了'
        }]);
        
        // ストリームを停止
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError('マイクへのアクセスが拒否されました');
      console.error('録音エラー:', err);
    }
  };

  // 録音停止
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // ファイル選択
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const audioFiles = files.filter(file => 
      file.type.startsWith('audio/') || file.name.match(/\.(mp3|wav|m4a|ogg)$/i)
    );
    
    if (audioFiles.length === 0) {
      setError('音声ファイルを選択してください');
      return;
    }
    
    setUploadedFiles(prev => [...prev, ...audioFiles]);
    setError(null);
  };

  // サンプル削除
  const removeSample = (index, type) => {
    if (type === 'recording') {
      setRecordings(prev => prev.filter((_, i) => i !== index));
    } else {
      setUploadedFiles(prev => prev.filter((_, i) => i !== index));
    }
  };

  // 音声クローン登録
  const handleSubmit = async () => {
    const totalSamples = recordings.length + uploadedFiles.length;
    
    if (totalSamples < 3) {
      setError('最低3つの音声サンプルが必要です（10-30秒推奨）');
      return;
    }
    
    if (!profileName.trim()) {
      setError('プロファイル名を入力してください');
      return;
    }
    
    setIsUploading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const formData = new FormData();
      formData.append('name', profileName);
      formData.append('description', description);
      formData.append('language', language);
      
      // 録音データを追加
      for (let i = 0; i < recordings.length; i++) {
        const file = new File([recordings[i].blob], recordings[i].name, {
          type: 'audio/wav'
        });
        formData.append('audio_samples', file);
      }
      
      // アップロードファイルを追加
      for (const file of uploadedFiles) {
        formData.append('audio_samples', file);
      }
      
      const apiUrl = getApiEndpoint(API_CONFIG.ENDPOINTS.VOICE_CLONE_REGISTER);
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '音声クローン登録に失敗しました');
      }
      
      const result = await response.json();
      
      if (result.success) {
        setSuccess(`音声クローン「${profileName}」の登録が完了しました！`);
        
        // リセット
        setRecordings([]);
        setUploadedFiles([]);
        setProfileName('');
        setDescription('');
        
        // 親コンポーネントに通知
        if (onUploadComplete) {
          onUploadComplete(result.voice_profile_id);
        }
        
        // 管理タブのプロファイル一覧も更新
        if (activeTab === 'manage') {
          await loadVoiceProfiles();
        }
      } else {
        throw new Error(result.message || '登録に失敗しました');
      }
      
    } catch (err) {
      setError(err.message);
      console.error('音声クローン登録エラー:', err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="voice-clone-upload">
      <h2>🎙️ 音声クローン管理</h2>
      
      {/* タブナビゲーション */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'create' ? 'active' : ''}`}
          onClick={() => setActiveTab('create')}
        >
          ➕ 新規作成
        </button>
        <button
          className={`tab-button ${activeTab === 'manage' ? 'active' : ''}`}
          onClick={() => setActiveTab('manage')}
        >
          📚 プロファイル管理
        </button>
      </div>

      {/* エラー/成功メッセージ */}
      {error && (
        <div className="error-message">
          ❌ {error}
          <button onClick={() => setError(null)} className="close-button">×</button>
        </div>
      )}
      
      {success && (
        <div className="success-message">
          ✅ {success}
          <button onClick={() => setSuccess(null)} className="close-button">×</button>
        </div>
      )}

      {/* 新規作成タブ */}
      {activeTab === 'create' && (
        <div className="create-tab">
          {/* プロファイル情報 */}
      <div className="profile-section">
        <h3>プロファイル情報</h3>
        <div className="form-group">
          <label>プロファイル名 *</label>
          <input
            type="text"
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
            placeholder="例: 私の声"
            required
          />
        </div>
        
        <div className="form-group">
          <label>説明（オプション）</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="この音声プロファイルの説明"
            rows={2}
          />
        </div>
        
        <div className="form-group">
          <label>言語</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="ja">日本語</option>
            <option value="en">英語</option>
            <option value="zh">中国語</option>
            <option value="ko">韓国語</option>
          </select>
        </div>
      </div>

      {/* 録音セクション */}
      <div className="recording-section">
        <h3>音声サンプル収集</h3>
        <p className="instruction">
          高品質な音声クローンのため、3つ以上の音声サンプル（各10-30秒）を提供してください。
          静かな環境で、自然な声で話してください。
        </p>
        
        <div className="recording-controls">
          <button
            className={`record-button ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopRecording : startRecording}
          >
            {isRecording ? '⏹️ 録音停止' : '🎙️ 録音開始'}
          </button>
          
          <button
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
          >
            📁 ファイルを選択
          </button>
          
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
        
        {isRecording && (
          <div className="recording-indicator">
            <span className="pulse"></span>
            録音中... 10-30秒程度お話しください
          </div>
        )}
      </div>

      {/* サンプルリスト */}
      <div className="samples-section">
        <h3>音声サンプル ({recordings.length + uploadedFiles.length}/3)</h3>
        
        {recordings.length === 0 && uploadedFiles.length === 0 ? (
          <p className="no-samples">音声サンプルがありません</p>
        ) : (
          <div className="samples-list">
            {recordings.map((recording, index) => (
              <div key={`rec-${index}`} className="sample-item">
                <span className="sample-name">🎙️ {recording.name}</span>
                <audio controls src={recording.url} />
                <button
                  className="remove-button"
                  onClick={() => removeSample(index, 'recording')}
                >
                  ✕
                </button>
              </div>
            ))}
            
            {uploadedFiles.map((file, index) => (
              <div key={`file-${index}`} className="sample-item">
                <span className="sample-name">📁 {file.name}</span>
                <span className="sample-size">
                  ({(file.size / 1024 / 1024).toFixed(1)} MB)
                </span>
                <button
                  className="remove-button"
                  onClick={() => removeSample(index, 'file')}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 送信ボタン */}
      <div className="submit-section">
        <button
          className="submit-button"
          onClick={handleSubmit}
          disabled={
            isUploading || 
            recordings.length + uploadedFiles.length < 3 ||
            !profileName.trim()
          }
        >
          {isUploading ? '🔄 処理中...' : '🚀 音声クローンを作成'}
        </button>
      </div>

      {/* 推奨事項 */}
      <div className="tips-section">
        <h4>💡 推奨事項</h4>
        <ul>
          <li>静かな環境で録音してください</li>
          <li>マイクから適切な距離（20-30cm）を保ってください</li>
          <li>自然な話し方で、様々なトーンを含めてください</li>
          <li>各サンプルは10-30秒程度が理想的です</li>
          <li>異なる文章を読むことで、より良い結果が得られます</li>
        </ul>
      </div>
        </div>
      )}

      {/* プロファイル管理タブ */}
      {activeTab === 'manage' && (
        <div className="manage-tab">
          <div className="manage-header">
            <h3>📚 登録済み音声プロファイル</h3>
            <div className="header-buttons">
              <button 
                onClick={generateTestVoice}
                className="test-voice-button"
                title="既存サンプルでテスト音声を生成"
              >
                🎵 テスト音声生成
              </button>
              <button 
                onClick={loadVoiceProfiles}
                className="refresh-button"
                disabled={loadingProfiles}
              >
                {loadingProfiles ? '🔄 読み込み中...' : '🔄 更新'}
              </button>
            </div>
          </div>

          {loadingProfiles ? (
            <div className="loading-state">
              <div className="loading-spinner">🔄</div>
              <p>プロファイルを読み込み中...</p>
            </div>
          ) : voiceProfiles.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎙️</div>
              <p>まだ音声プロファイルが登録されていません</p>
              <p>「新規作成」タブから音声クローンを作成してください</p>
            </div>
          ) : (
            <div className="profiles-list">
              {voiceProfiles.map((profile) => (
                <div key={profile.id} className="profile-item">
                  <div className="profile-info">
                    <div className="profile-header">
                      <div className="profile-icon">🔊</div>
                      <div className="profile-details">
                        <div className="profile-name">{profile.name}</div>
                        <div className="profile-meta">
                          <span>ID: {profile.id}</span>
                          {profile.language && (
                            <>
                              <span> • </span>
                              <span>言語: {profile.language}</span>
                            </>
                          )}
                          {profile.created_at && (
                            <>
                              <span> • </span>
                              <span>作成: {new Date(profile.created_at).toLocaleDateString('ja-JP')}</span>
                            </>
                          )}
                        </div>
                        {profile.description && (
                          <div className="profile-description">
                            {profile.description}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="profile-actions">
                    <button
                      onClick={() => testVoiceProfile(profile.id, profile.name)}
                      className="action-button test-button"
                      title="音声をテスト"
                    >
                      ▶ テスト
                    </button>
                    
                    <button
                      onClick={() => deleteVoiceProfile(profile.id)}
                      className="action-button delete-button"
                      title="プロファイルを削除"
                    >
                      🗑 削除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="usage-info">
            <h4>💡 使用方法</h4>
            <p>
              作成した音声プロファイルは、動画生成画面の音声選択で「Voice Clone」カテゴリに表示されます。
              テストボタンで音質を確認してから、動画生成にお使いください。
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceCloneUpload;