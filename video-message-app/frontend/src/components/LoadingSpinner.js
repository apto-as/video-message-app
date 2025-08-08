import React from 'react';

const LoadingSpinner = ({ message = "動画を生成しています..." }) => {
  return (
    <div className="loading-container">
      <div className="spinner"></div>
      <p>{message}</p>
      <p className="loading-note">しばらくお待ちください（15-30秒程度）</p>
    </div>
  );
};

export default LoadingSpinner;