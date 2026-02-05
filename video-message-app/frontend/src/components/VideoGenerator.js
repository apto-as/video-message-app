import React, { useState } from 'react';
import ImageUpload from './ImageUpload';
import TextInput from './TextInput';
import VideoPreview from './VideoPreview';
import ErrorMessage from './ErrorMessage';
import LoadingSpinner from './LoadingSpinner';
import BackgroundProcessor from './BackgroundProcessor';
import PersonDetector from './PersonDetector';
import VoiceVoxSelector from './VoiceVoxSelector';
import { generateVideoWithVoicevox, generateVideoWithClonedVoice } from '../services/api';
import './VideoGenerator.css';

const VideoGenerator = () => {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [text, setText] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [processedImageData, setProcessedImageData] = useState(null);
  const [processingInfo, setProcessingInfo] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [audioParams, setAudioParams] = useState({
    speed_scale: 1.0,
    pitch_scale: 0.0,
    intonation_scale: 1.0,
    volume_scale: 1.0,
    speed: 1.0,
    emotion: 'neutral',
    remove_background: false,
    enhance_quality: true,
    pause_duration: 0.0
  });

  const handleImageProcessed = (processedImage, info) => {
    setProcessedImageData(processedImage);
    setProcessingInfo(info);
  };

  const handleGenerate = async () => {
    if (!image || !text.trim()) {
      setError('画像とテキストを入力してください');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let result;

      // リップシンク動画生成（MuseTalk経由）
      // 常にアップロード画像を使用
      const imageToUse = processedImageData ?
        dataURLToFile(processedImageData, 'processed-image.jpg') :
        image;

      // 音声合成と動画生成を統合して実行
      if (selectedVoice && selectedVoice.provider === 'voicevox') {
        result = await generateVideoWithVoicevox(imageToUse, text, selectedVoice, audioParams);
      } else if (selectedVoice && selectedVoice.provider === 'voice-clone') {
        result = await generateVideoWithClonedVoice(imageToUse, text, selectedVoice, audioParams);
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
    setImagePreview(null);
    setText('');
    setVideoUrl('');
    setError('');
    setProcessedImageData(null);
    setProcessingInfo(null);
    setSelectedVoice(null);
    setAudioParams({
      speed_scale: 1.0,
      pitch_scale: 0.0,
      intonation_scale: 1.0,
      volume_scale: 1.0,
      speed: 1.0,
      emotion: 'neutral',
      remove_background: false,
      enhance_quality: true,
      pause_duration: 0.0
    });
  };

  // PersonDetectorからの処理済み画像を受け取る
  const handlePersonDetectorProcessed = (processedImage, info) => {
    setProcessedImageData(processedImage);
    setProcessingInfo(prev => ({
      ...prev,
      ...info
    }));
  };

  const canGenerate = () => {
    return text.trim() && !loading && image;
  };

  return (
    <div className="video-generator">
      <header className="app-header">
        <h1>動画メッセージ生成</h1>
        <p>写真とメッセージから、話す動画を作成します</p>
      </header>

      {error && <ErrorMessage message={error} onClose={() => setError('')} />}

      {loading ? (
        <LoadingSpinner />
      ) : videoUrl ? (
        <VideoPreview videoUrl={videoUrl} onReset={handleReset} />
      ) : (
        <div className="input-section">
          <ImageUpload
            onImageSelect={setImage}
            selectedImage={image}
            onPreviewChange={setImagePreview}
          />

          {/* Person Detector - 画像アップロード後に表示 */}
          {image && imagePreview && (
            <PersonDetector
              image={image}
              imagePreview={imagePreview}
              onProcessedImage={handlePersonDetectorProcessed}
              disabled={loading}
            />
          )}

          {image && (
            <BackgroundProcessor
              image={processedImageData ? dataURLToFile(processedImageData, 'extracted-image.png') : image}
              onImageProcessed={handleImageProcessed}
              disabled={loading}
            />
          )}

          {processingInfo && (
            <div className="processing-status">
              <h4>処理状況</h4>
              <ul>
                <li>背景削除: {processingInfo.background_removed ? 'OK' : 'NG'}</li>
                <li>背景合成: {processingInfo.background_composited ? 'OK' : 'NG'}</li>
                <li>画質向上: {processingInfo.quality_enhanced ? 'OK' : 'NG'}</li>
                {processingInfo.upper_body_cropped !== undefined && (
                  <li>上半身クロップ: {processingInfo.upper_body_cropped ? 'OK' : 'NG'}</li>
                )}
              </ul>
            </div>
          )}

          <TextInput value={text} onChange={setText} />

          <VoiceVoxSelector
            selectedVoice={selectedVoice}
            onVoiceSelect={setSelectedVoice}
            showCloneOption={true}
          />

          {selectedVoice && selectedVoice.provider === 'voicevox' && (
            <div className="voicevox-params">
              <h4>音声調整</h4>
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
                <div className="param-control">
                  <label>文末ポーズ: {audioParams.pause_duration.toFixed(1)}秒</label>
                  <input
                    type="range"
                    min="0.0"
                    max="3.0"
                    step="0.1"
                    value={audioParams.pause_duration}
                    onChange={(e) => setAudioParams({...audioParams, pause_duration: parseFloat(e.target.value)})}
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

          {selectedVoice && selectedVoice.provider === 'voice-clone' && (
            <div className="clone-voice-params">
              <h4>Voice Clone 設定</h4>
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
                <div className="param-control">
                  <label>文末ポーズ: {audioParams.pause_duration.toFixed(1)}秒</label>
                  <input
                    type="range"
                    min="0.0"
                    max="3.0"
                    step="0.1"
                    value={audioParams.pause_duration}
                    onChange={(e) => setAudioParams({...audioParams, pause_duration: parseFloat(e.target.value)})}
                    disabled={loading}
                  />
                </div>
              </div>
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={!canGenerate()}
            className={`generate-button ${canGenerate() ? 'active' : 'disabled'}`}
          >
            {loading ? '生成中...' : 'リップシンク動画を生成'}
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoGenerator;
