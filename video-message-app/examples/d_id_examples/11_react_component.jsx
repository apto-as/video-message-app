/**
 * Example 11: React D-ID Video Generator Component
 * ==================================================
 *
 * Complete React component for D-ID video generation with:
 * - File upload (image + audio)
 * - Progress tracking
 * - Error handling
 * - Video preview
 *
 * Usage:
 *   import VideoGenerator from './11_react_component';
 *   <VideoGenerator apiBaseUrl="http://localhost:55433/api/d-id" />
 */

import React, { useState } from 'react';
import axios from 'axios';
import './VideoGenerator.css';

const VideoGenerator = ({ apiBaseUrl = 'http://localhost:55433/api/d-id' }) => {
  // State management
  const [imageFile, setImageFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  /**
   * Handle image file selection
   */
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file (JPEG, PNG)');
      return;
    }

    // Validate file size (max 10 MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image file too large (max 10 MB)');
      return;
    }

    setImageFile(file);
    setError(null);

    // Generate preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  /**
   * Handle audio file selection
   */
  const handleAudioChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/mp4', 'audio/m4a'];
    if (!allowedTypes.includes(file.type)) {
      setError('Please select an audio file (WAV, MP3, M4A)');
      return;
    }

    // Validate file size (max 30 MB)
    if (file.size > 30 * 1024 * 1024) {
      setError('Audio file too large (max 30 MB)');
      return;
    }

    setAudioFile(file);
    setError(null);
  };

  /**
   * Upload image to D-ID
   */
  const uploadImage = async () => {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await axios.post(
      `${apiBaseUrl}/upload-source-image`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percentCompleted * 0.3); // 0-30% for image upload
        }
      }
    );

    return response.data.url;
  };

  /**
   * Upload audio to D-ID
   */
  const uploadAudio = async () => {
    const formData = new FormData();
    formData.append('file', audioFile);

    const response = await axios.post(
      `${apiBaseUrl}/upload-audio`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(30 + percentCompleted * 0.2); // 30-50% for audio upload
        }
      }
    );

    return response.data.url;
  };

  /**
   * Generate video from uploaded files
   */
  const generateVideo = async (imageUrl, audioUrl) => {
    const response = await axios.post(
      `${apiBaseUrl}/generate-video`,
      {
        audio_url: audioUrl,
        source_url: imageUrl
      }
    );

    return response.data.id;
  };

  /**
   * Poll video generation status
   */
  const pollVideoStatus = async (talkId) => {
    const maxAttempts = 60;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const response = await axios.get(
        `${apiBaseUrl}/talk-status/${talkId}`
      );

      const videoStatus = response.data.status;
      const progressPercent = 50 + Math.min(attempt / maxAttempts * 50, 45);

      setStatus(`Generating video... (${videoStatus})`);
      setProgress(progressPercent);

      if (videoStatus === 'done') {
        setProgress(100);
        return response.data.result_url;
      } else if (videoStatus === 'error' || videoStatus === 'rejected') {
        throw new Error('Video generation failed: ' + response.data.error);
      }

      // Wait 5 seconds before next poll
      await new Promise(resolve => setTimeout(resolve, 5000));
    }

    throw new Error('Video generation timed out');
  };

  /**
   * Main video generation handler
   */
  const handleGenerateVideo = async () => {
    if (!imageFile || !audioFile) {
      setError('Please select both image and audio files');
      return;
    }

    setLoading(true);
    setError(null);
    setVideoUrl(null);
    setProgress(0);

    try {
      // Step 1: Upload image
      setStatus('Uploading image...');
      const imageUrl = await uploadImage();
      console.log('Image uploaded:', imageUrl);

      // Step 2: Upload audio
      setStatus('Uploading audio...');
      const audioUrl = await uploadAudio();
      console.log('Audio uploaded:', audioUrl);

      // Step 3: Generate video
      setStatus('Starting video generation...');
      setProgress(50);
      const talkId = await generateVideo(imageUrl, audioUrl);
      console.log('Video generation started:', talkId);

      // Step 4: Poll status
      const videoUrl = await pollVideoStatus(talkId);
      console.log('Video ready:', videoUrl);

      // Success
      setVideoUrl(videoUrl);
      setStatus('Video generation complete!');
      setProgress(100);

    } catch (err) {
      console.error('Video generation error:', err);
      setError(err.message || 'Video generation failed');
      setStatus('');
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Reset form
   */
  const handleReset = () => {
    setImageFile(null);
    setAudioFile(null);
    setImagePreview(null);
    setVideoUrl(null);
    setLoading(false);
    setStatus('');
    setProgress(0);
    setError(null);
  };

  return (
    <div className="video-generator">
      <h2>D-ID Video Generator</h2>

      {/* Error message */}
      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Upload section */}
      <div className="upload-section">
        <div className="upload-group">
          <label htmlFor="image-upload" className="upload-label">
            📷 Upload Image (Portrait)
          </label>
          <input
            id="image-upload"
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            disabled={loading}
            className="upload-input"
          />
          {imageFile && (
            <div className="file-info">
              ✅ {imageFile.name} ({(imageFile.size / 1024 / 1024).toFixed(2)} MB)
            </div>
          )}
        </div>

        <div className="upload-group">
          <label htmlFor="audio-upload" className="upload-label">
            🎤 Upload Audio (WAV, MP3, M4A)
          </label>
          <input
            id="audio-upload"
            type="file"
            accept="audio/*"
            onChange={handleAudioChange}
            disabled={loading}
            className="upload-input"
          />
          {audioFile && (
            <div className="file-info">
              ✅ {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
            </div>
          )}
        </div>
      </div>

      {/* Image preview */}
      {imagePreview && (
        <div className="image-preview">
          <h3>Image Preview</h3>
          <img src={imagePreview} alt="Preview" />
        </div>
      )}

      {/* Generate button */}
      <div className="action-section">
        <button
          onClick={handleGenerateVideo}
          disabled={loading || !imageFile || !audioFile}
          className="generate-button"
        >
          {loading ? 'Generating...' : '🎬 Generate Video'}
        </button>

        {videoUrl && (
          <button onClick={handleReset} className="reset-button">
            🔄 Generate Another Video
          </button>
        )}
      </div>

      {/* Progress indicator */}
      {loading && (
        <div className="progress-section">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="status-text">{status} ({progress.toFixed(0)}%)</div>
        </div>
      )}

      {/* Video player */}
      {videoUrl && (
        <div className="video-player">
          <h3>Generated Video</h3>
          <video controls width="640" height="480" key={videoUrl}>
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          <div className="video-actions">
            <a
              href={videoUrl}
              download="generated_video.mp4"
              className="download-button"
            >
              📥 Download Video
            </a>
            <button
              onClick={() => navigator.clipboard.writeText(videoUrl)}
              className="copy-button"
            >
              📋 Copy URL
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoGenerator;
