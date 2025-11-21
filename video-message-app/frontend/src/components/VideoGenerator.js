import React, { useState, useEffect } from 'react';
import ImageUpload from './ImageUpload';
import TextInput from './TextInput';
import VideoPreview from './VideoPreview';
import ErrorMessage from './ErrorMessage';
import LoadingSpinner from './LoadingSpinner';
import BackgroundProcessor from './BackgroundProcessor';
import VoiceVoxSelector from './VoiceVoxSelector';
import DIdSelector from './DIdSelector';
import DIdErrorBoundary from './DIdErrorBoundary';
import { generateVideoWithVoicevox, generateVideoWithOpenVoice } from '../services/api';

const VideoGenerator = () => {
  const [image, setImage] = useState(null);
  const [text, setText] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [processedImageData, setProcessedImageData] = useState(null);
  const [processingInfo, setProcessingInfo] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [dIdSelection, setDIdSelection] = useState(null);
  const [audioParams, setAudioParams] = useState({
    speed_scale: 1.0,
    pitch_scale: 0.0,
    intonation_scale: 1.0,
    volume_scale: 1.0,
    speed: 1.0,
    emotion: 'neutral',
    remove_background: false,
    enhance_quality: true
  });

  // Timeout detection for DIdSelector initialization
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (!dIdSelection) {
        setError('⚠️ リップシンク設定の初期化に失敗しました。ページを再読み込みしてください。');
        console.error('[Security] DIdSelector initialization timeout');
      }
    }, 3000);

    return () => clearTimeout(timeout);
  }, [dIdSelection]);

  const handleImageProcessed = (processedImage, info) => {
    setProcessedImageData(processedImage);
    setProcessingInfo(info);
  };

  const handleGenerate = async () => {
    if (!image || !text.trim()) {
      setError('画像とテキストを入力してください');
      return;
    }

    // CRITICAL: DIdSelection validation
    if (!dIdSelection) {
      console.error('[Security] dIdSelection is null - DIdSelector may not have mounted');
      setError('リップシンク設定の初期化に失敗しました。ページを再読み込みしてください。');
      return;
    }

    if (!dIdSelection.use_custom_image) {
      console.error('[Security] use_custom_image is not true');
      setError('リップシンク設定が不正です。');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let result;

      // D-ID リップシンク動画生成（常にリップシンクモード）
      // 常にアップロード画像を使用（プレゼンター機能は削除）
      const imageToUse = processedImageData ?
        dataURLToFile(processedImageData, 'processed-image.jpg') :
        image;

      // 音声合成と動画生成を統合して実行
      if (selectedVoice && selectedVoice.provider === 'voicevox') {
        result = await generateVideoWithVoicevox(imageToUse, text, selectedVoice, audioParams);
      } else if (selectedVoice && selectedVoice.provider === 'openvoice') {
        result = await generateVideoWithOpenVoice(imageToUse, text, selectedVoice, audioParams);
      } else {
        throw new Error('音声を選択してください');
      }
      
      if (result.success) {
        setVideoUrl(result.video_url);
      } else {
        setError(result.error || '動画生成に失敗しました');
      }
    } catch (err) {
      setError(err.message || '動画生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // Data URLをFileオブジェクトに変換
  const dataURLToFile = (dataURL, fileName) => {
    const arr = dataURL.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], fileName, { type: mime });
  };

  const handleReset = () => {
    setImage(null);
    setText('');
    setVideoUrl('');
    setError('');
    setProcessedImageData(null);
    setProcessingInfo(null);
    setSelectedVoice(null);
    setDIdSelection(null);
    setAudioParams({
      speed_scale: 1.0,
      pitch_scale: 0.0,
      intonation_scale: 1.0,
      volume_scale: 1.0,
      speed: 1.0,
      emotion: 'neutral',
      remove_background: false,
      enhance_quality: true
    });
  };

  const canGenerate = () => {
    if (!text.trim() || loading) return false;

    // リップシンク動画の場合、常に画像とDIdSelectionが必要
    return dIdSelection && image;
  };

  return (
    <div className="video-generator">
      <header className="app-header">
        <h1>🎬 動画メッセージ生成</h1>
        <p>写真とメッセージから、話す動画を作成します</p>
      </header>
      
      {error && <ErrorMessage message={error} onClose={() => setError('')} />}
      
      {loading ? (
        <LoadingSpinner />
      ) : videoUrl ? (
        <VideoPreview videoUrl={videoUrl} onReset={handleReset} />
      ) : (
        <div className="input-section">
          <ImageUpload onImageSelect={setImage} selectedImage={image} />
          
          {image && (
            <BackgroundProcessor 
              image={image}
              onImageProcessed={handleImageProcessed}
              disabled={loading}
            />
          )}
          
          {processingInfo && (
            <div className="processing-status">
              <h4>📊 処理状況</h4>
              <ul>
                <li>背景削除: {processingInfo.background_removed ? '✅' : '❌'}</li>
                <li>背景合成: {processingInfo.background_composited ? '✅' : '❌'}</li>
                <li>画質向上: {processingInfo.quality_enhanced ? '✅' : '❌'}</li>
              </ul>
            </div>
          )}
          
          <TextInput value={text} onChange={setText} />

          <VoiceVoxSelector
            selectedVoice={selectedVoice}
            onVoiceSelect={setSelectedVoice}
            showCloneOption={true}
          />

          {/* D-ID設定（常に表示） */}
          <DIdErrorBoundary>
            <DIdSelector
              onSelectionChange={setDIdSelection}
              disabled={loading}
            />
          </DIdErrorBoundary>
          
          {selectedVoice && selectedVoice.provider === 'voicevox' && (
            <div className="voicevox-params">
              <h4>🎛️ 音声調整</h4>
              <div className="params-grid">
                <div className="param-control">
                  <label>話速: {audioParams.speed_scale.toFixed(1)}</label>
                  <input
                    type="range"
                    min="0.5"
                    max="2.0"
                    step="0.1"
                    value={audioParams.speed_scale}
                    onChange={(e) => setAudioParams({...audioParams, speed_scale: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
                <div className="param-control">
                  <label>音高: {audioParams.pitch_scale.toFixed(2)}</label>
                  <input
                    type="range"
                    min="-0.15"
                    max="0.15"
                    step="0.01"
                    value={audioParams.pitch_scale}
                    onChange={(e) => setAudioParams({...audioParams, pitch_scale: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
                <div className="param-control">
                  <label>抑揚: {audioParams.intonation_scale.toFixed(1)}</label>
                  <input
                    type="range"
                    min="0.0"
                    max="2.0"
                    step="0.1"
                    value={audioParams.intonation_scale}
                    onChange={(e) => setAudioParams({...audioParams, intonation_scale: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
                <div className="param-control">
                  <label>音量: {audioParams.volume_scale.toFixed(1)}</label>
                  <input
                    type="range"
                    min="0.0"
                    max="2.0"
                    step="0.1"
                    value={audioParams.volume_scale}
                    onChange={(e) => setAudioParams({...audioParams, volume_scale: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
                <div className="param-checkboxes">
                  <label>
                    <input
                      type="checkbox"
                      checked={audioParams.enhance_quality}
                      onChange={(e) => setAudioParams({...audioParams, enhance_quality: e.target.checked})}
                      disabled={loading}
                    />
                    画質向上
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={audioParams.remove_background}
                      onChange={(e) => setAudioParams({...audioParams, remove_background: e.target.checked})}
                      disabled={loading}
                    />
                    背景削除
                  </label>
                </div>
              </div>
            </div>
          )}
          
          {selectedVoice && selectedVoice.provider === 'openvoice' && (
            <div className="openvoice-params">
              <h4>🎙️ OpenVoice V2 設定</h4>
              <div className="params-grid">
                <div className="param-control">
                  <label>話速: {audioParams.speed.toFixed(1)}</label>
                  <input
                    type="range"
                    min="0.5"
                    max="2.0"
                    step="0.1"
                    value={audioParams.speed}
                    onChange={(e) => setAudioParams({...audioParams, speed: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
                <div className="param-control">
                  <label>感情設定</label>
                  <select
                    value={audioParams.emotion}
                    onChange={(e) => setAudioParams({...audioParams, emotion: e.target.value})}
                    disabled={loading}
                    style={{
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #dee2e6',
                      fontSize: '14px'
                    }}
                  >
                    <option value="neutral">中性</option>
                    <option value="happy">明るい</option>
                    <option value="sad">悲しい</option>
                    <option value="angry">怒り</option>
                    <option value="excited">興奮</option>
                  </select>
                </div>
                <div className="param-checkboxes">
                  <label>
                    <input
                      type="checkbox"
                      checked={audioParams.enhance_quality}
                      onChange={(e) => setAudioParams({...audioParams, enhance_quality: e.target.checked})}
                      disabled={loading}
                    />
                    画質向上
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={audioParams.remove_background}
                      onChange={(e) => setAudioParams({...audioParams, remove_background: e.target.checked})}
                      disabled={loading}
                    />
                    背景削除
                  </label>
                </div>
              </div>
            </div>
          )}
          
          <button
            onClick={handleGenerate}
            disabled={!canGenerate()}
            className={`generate-button ${canGenerate() ? 'active' : 'disabled'}`}
          >
            {loading ? '生成中...' : '🎬 リップシンク動画を生成'}
          </button>
        </div>
      )}
      
      <style>{`
        .processing-status {
          margin: 15px 0;
          padding: 15px;
          border: 1px solid #28a745;
          border-radius: 6px;
          background-color: #f8fff9;
        }
        
        .processing-status ul {
          margin: 10px 0 0 0;
          padding-left: 20px;
        }
        
        .processing-status li {
          margin: 5px 0;
        }
        
        .voicevox-params {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #007bff;
          border-radius: 8px;
          background-color: #f8f9fa;
        }
        
        .openvoice-params {
          margin: 20px 0;
          padding: 20px;
          border: 1px solid #28a745;
          border-radius: 8px;
          background-color: #f8fff9;
        }
        
        .voicevox-params h4 {
          margin: 0 0 15px 0;
          color: #007bff;
          font-size: 16px;
        }
        
        .openvoice-params h4 {
          margin: 0 0 15px 0;
          color: #28a745;
          font-size: 16px;
        }
        
        .params-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 15px;
          margin-bottom: 15px;
        }
        
        .param-control {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .param-control label {
          font-size: 14px;
          font-weight: 500;
          color: #495057;
        }
        
        .param-control input[type="range"] {
          width: 100%;
          height: 6px;
          border-radius: 3px;
          background: #dee2e6;
          outline: none;
          -webkit-appearance: none;
        }
        
        .param-control input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #007bff;
          cursor: pointer;
        }
        
        .param-control input[type="range"]::-moz-range-thumb {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #007bff;
          cursor: pointer;
          border: none;
        }
        
        .param-checkboxes {
          grid-column: 1 / -1;
          display: flex;
          gap: 20px;
          margin-top: 10px;
        }
        
        .param-checkboxes label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: #495057;
          cursor: pointer;
        }
        
        .param-checkboxes input[type="checkbox"] {
          width: 16px;
          height: 16px;
          accent-color: #007bff;
        }
        
        @media (max-width: 600px) {
          .params-grid {
            grid-template-columns: 1fr;
            gap: 12px;
          }
          
          .param-checkboxes {
            flex-direction: column;
            gap: 10px;
          }
        }
      `}</style>
    </div>
  );
};

export default VideoGenerator;