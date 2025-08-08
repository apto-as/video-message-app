import React, { useState, useEffect } from 'react';
import './DIdSelector.css';

const DIdSelector = ({ onSelectionChange = () => {}, disabled = false }) => {
  // プレゼンター機能は削除され、常にカスタム画像を使用
  const useCustomImage = true;

  useEffect(() => {
    // 常にカスタム画像を使用することを親コンポーネントに通知
    onSelectionChange({
      use_custom_image: true
    });
  }, [onSelectionChange]);


  return (
    <div className="did-selector">
      <h4>🎭 D-ID リップシンク設定</h4>
      
      {/* リップシンク設定情報 */}
      <div className="lipsync-info">
        <h5>リップシンク生成設定</h5>
        <ul>
          <li>アバター: アップロード画像を使用</li>
          <li>リップシンク: 音声に合わせて自動生成</li>
          <li>動画形式: MP4 (H.264)</li>
        </ul>
        <div className="info-note">
          ℹ️ アップロードした画像と音声を基にリップシンク動画を生成します
        </div>
      </div>
    </div>
  );
};

export default DIdSelector;