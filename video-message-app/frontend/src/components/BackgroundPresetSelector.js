import React, { useState, useEffect } from 'react';
import { getApiEndpoint } from '../config/api.config';

const BackgroundPresetSelector = ({ onSelect, selectedId, disabled = false }) => {
  const [backgrounds, setBackgrounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBackgrounds = async () => {
      try {
        const response = await fetch(getApiEndpoint('/presets/backgrounds'));
        if (!response.ok) throw new Error('Failed to fetch backgrounds');
        const data = await response.json();
        setBackgrounds(data.backgrounds || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchBackgrounds();
  }, []);

  const handleSelect = (bg) => {
    if (disabled) return;
    if (selectedId === bg.id) {
      onSelect(null); // deselect
    } else {
      onSelect(bg);
    }
  };

  if (loading) {
    return <div className="preset-loading">背景プリセットを読み込み中...</div>;
  }

  if (error) {
    return <div className="preset-error">背景の読み込みに失敗しました</div>;
  }

  if (backgrounds.length === 0) {
    return null;
  }

  return (
    <div className="background-preset-selector">
      <h4>背景を選択</h4>
      <p className="preset-hint">お祝い用の背景プリセットから選択できます</p>
      <div className="preset-grid">
        {backgrounds.map((bg) => (
          <div
            key={bg.id}
            className={`preset-item ${selectedId === bg.id ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
            onClick={() => handleSelect(bg)}
            title={bg.description}
          >
            <div className="preset-image-wrapper">
              <img
                src={getApiEndpoint(bg.thumbnail_url)}
                alt={bg.name}
                loading="lazy"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.parentElement.classList.add('no-image');
                }}
              />
              {selectedId === bg.id && (
                <div className="preset-check-overlay">&#10003;</div>
              )}
            </div>
            <span className="preset-name">{bg.name}</span>
          </div>
        ))}
      </div>

      <style>{`
        .background-preset-selector {
          margin: 10px 0;
        }
        .background-preset-selector h4 {
          margin: 0 0 5px 0;
          font-size: 15px;
          color: #333;
        }
        .preset-hint {
          margin: 0 0 12px 0;
          font-size: 13px;
          color: #888;
        }
        .preset-grid {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 10px;
        }
        .preset-item {
          cursor: pointer;
          border: 2px solid transparent;
          border-radius: 8px;
          overflow: hidden;
          transition: all 0.2s;
          text-align: center;
        }
        .preset-item:hover:not(.disabled) {
          border-color: #007bff;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 123, 255, 0.2);
        }
        .preset-item.selected {
          border-color: #007bff;
          box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.3);
        }
        .preset-item.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .preset-image-wrapper {
          position: relative;
          width: 100%;
          padding-top: 75%;
          background: #f0f0f0;
          overflow: hidden;
        }
        .preset-image-wrapper img {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .preset-image-wrapper.no-image {
          display: flex;
          align-items: center;
          justify-content: center;
          color: #aaa;
          font-size: 12px;
        }
        .preset-image-wrapper.no-image::after {
          content: 'No Image';
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
        }
        .preset-check-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 123, 255, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 32px;
          color: white;
          font-weight: bold;
        }
        .preset-name {
          display: block;
          padding: 6px 4px;
          font-size: 12px;
          color: #555;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .preset-loading, .preset-error {
          padding: 10px;
          text-align: center;
          color: #888;
          font-size: 14px;
        }
        @media (max-width: 600px) {
          .preset-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
          }
        }
      `}</style>
    </div>
  );
};

export default BackgroundPresetSelector;
