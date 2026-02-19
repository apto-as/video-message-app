import React, { useState } from 'react';

const VideoPreview = ({ videoUrl, onReset }) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const response = await fetch(videoUrl);
      const blob = await response.blob();
      const file = new File([blob], 'message-video.mp4', { type: 'video/mp4' });

      // iOS/mobile: use Web Share API (opens native share sheet → save to camera roll)
      if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: '動画メッセージ' });
        return;
      }

      // Desktop: blob download
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = 'message-video.mp4';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      // Share cancelled or failed — open video in new tab as last resort
      if (err.name !== 'AbortError') {
        window.open(videoUrl, '_blank');
      }
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="video-preview-container">
      <h3>動画が完成しました！</h3>
      <div className="video-player">
        <video
          src={videoUrl}
          controls
          playsInline
          width="100%"
          style={{ maxWidth: '500px' }}
        >
          お使いのブラウザは動画再生に対応していません。
        </video>
      </div>
      <div className="video-actions">
        <button onClick={handleDownload} className="download-button" disabled={downloading}>
          {downloading ? '保存中...' : '動画を保存・共有'}
        </button>
        <button onClick={onReset} className="reset-button">
          新しく生成
        </button>
      </div>
    </div>
  );
};

export default VideoPreview;