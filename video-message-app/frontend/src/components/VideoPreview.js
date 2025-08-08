import React from 'react';

const VideoPreview = ({ videoUrl, onReset }) => {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = 'message-video.mp4';
    link.click();
  };

  return (
    <div className="video-preview-container">
      <h3>動画が完成しました！</h3>
      <div className="video-player">
        <video 
          src={videoUrl} 
          controls 
          width="100%" 
          style={{ maxWidth: '500px' }}
        >
          お使いのブラウザは動画再生に対応していません。
        </video>
      </div>
      <div className="video-actions">
        <button onClick={handleDownload} className="download-button">
          動画をダウンロード
        </button>
        <button onClick={onReset} className="reset-button">
          新しく生成
        </button>
      </div>
    </div>
  );
};

export default VideoPreview;