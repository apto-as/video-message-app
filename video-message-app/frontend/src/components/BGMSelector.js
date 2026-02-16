import React, { useState, useEffect, useRef } from 'react';
import { getApiEndpoint } from '../config/api.config';

const BGMSelector = ({ onSelect, selectedId, disabled = false }) => {
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    const fetchTracks = async () => {
      try {
        const response = await fetch(getApiEndpoint('/presets/music'));
        if (!response.ok) throw new Error('Failed to fetch music');
        const data = await response.json();
        setTracks(data.tracks || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTracks();
  }, []);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleSelect = (track) => {
    if (disabled) return;
    if (selectedId === track.id) {
      onSelect(null);
    } else {
      onSelect(track);
    }
  };

  const handlePreview = (e, track) => {
    e.stopPropagation();
    if (disabled) return;

    if (playingId === track.id) {
      // Stop playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingId(null);
      return;
    }

    // Stop any existing playback
    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(getApiEndpoint(track.preview_url));
    audio.volume = 0.5;
    audio.onended = () => setPlayingId(null);
    audio.onerror = () => setPlayingId(null);
    audio.play().catch(() => setPlayingId(null));
    audioRef.current = audio;
    setPlayingId(track.id);
  };

  const formatDuration = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const moodLabels = {
    cheerful: '明るい',
    relaxed: 'リラックス',
    playful: '楽しい',
    gentle: '優しい',
  };

  if (loading) {
    return <div className="bgm-loading">BGMを読み込み中...</div>;
  }

  if (error) {
    return <div className="bgm-error">BGMの読み込みに失敗しました</div>;
  }

  if (tracks.length === 0) {
    return null;
  }

  return (
    <div className="bgm-selector">
      <h3>BGMを選択（オプション）</h3>
      <p className="bgm-hint">動画にバックグラウンドミュージックを追加できます</p>
      <div className="bgm-list">
        {tracks.map((track) => (
          <div
            key={track.id}
            className={`bgm-item ${selectedId === track.id ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
            onClick={() => handleSelect(track)}
          >
            <div className="bgm-info">
              <div className="bgm-title">{track.name}</div>
              <div className="bgm-details">
                <span className="bgm-artist">{track.artist}</span>
                <span className="bgm-mood">{moodLabels[track.mood] || track.mood}</span>
                <span className="bgm-duration">{formatDuration(track.duration_seconds)}</span>
              </div>
              <div className="bgm-description">{track.description}</div>
            </div>
            <div className="bgm-actions">
              <button
                className={`bgm-preview-btn ${playingId === track.id ? 'playing' : ''}`}
                onClick={(e) => handlePreview(e, track)}
                disabled={disabled}
                title={playingId === track.id ? '停止' : '試聴'}
              >
                {playingId === track.id ? '||' : '\u25B6'}
              </button>
              {selectedId === track.id && (
                <span className="bgm-selected-badge">&#10003;</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .bgm-selector {
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
          margin: 20px 0;
          background-color: #fdf9f3;
        }
        .bgm-selector h3 {
          margin: 0 0 5px 0;
          font-size: 16px;
          color: #333;
        }
        .bgm-hint {
          margin: 0 0 15px 0;
          font-size: 13px;
          color: #888;
        }
        .bgm-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .bgm-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border: 2px solid #e8e0d4;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          background: white;
        }
        .bgm-item:hover:not(.disabled) {
          border-color: #e8a838;
          background: #fffbf5;
        }
        .bgm-item.selected {
          border-color: #e8a838;
          background: #fff8ed;
          box-shadow: 0 0 0 2px rgba(232, 168, 56, 0.2);
        }
        .bgm-item.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .bgm-info {
          flex: 1;
          min-width: 0;
        }
        .bgm-title {
          font-weight: 600;
          font-size: 15px;
          color: #333;
          margin-bottom: 4px;
        }
        .bgm-details {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: #888;
          margin-bottom: 2px;
        }
        .bgm-mood {
          background: #f0e6d6;
          padding: 1px 8px;
          border-radius: 10px;
          color: #a07020;
        }
        .bgm-description {
          font-size: 13px;
          color: #666;
        }
        .bgm-actions {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-left: 12px;
        }
        .bgm-preview-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border: 2px solid #e8a838;
          background: white;
          color: #e8a838;
          font-size: 14px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }
        .bgm-preview-btn:hover:not(:disabled) {
          background: #e8a838;
          color: white;
        }
        .bgm-preview-btn.playing {
          background: #e8a838;
          color: white;
          animation: pulse 1s infinite;
        }
        .bgm-preview-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .bgm-selected-badge {
          color: #e8a838;
          font-size: 20px;
          font-weight: bold;
        }
        .bgm-loading, .bgm-error {
          padding: 10px;
          text-align: center;
          color: #888;
          font-size: 14px;
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
};

export default BGMSelector;
