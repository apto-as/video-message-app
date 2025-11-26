import React, { useState, useCallback, useRef, useEffect } from 'react';
import { detectPersons, extractSelectedPersons } from '../services/api';

/**
 * PersonDetector Component
 * 画像から人物を検出し、選択した人物のみを抽出する
 * VideoGeneratorに統合されて使用される
 */
const PersonDetector = ({
  image,           // File object
  imagePreview,    // base64 preview
  onProcessedImage,  // callback with processed image data URL
  disabled = false
}) => {
  const [detectedPersons, setDetectedPersons] = useState([]);
  const [selectedPersonIds, setSelectedPersonIds] = useState(new Set());
  const [isDetecting, setIsDetecting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState(null);
  const [confThreshold, setConfThreshold] = useState(0.5);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [isExpanded, setIsExpanded] = useState(false);

  const imageRef = useRef(null);

  // Reset state when image changes
  useEffect(() => {
    setDetectedPersons([]);
    setSelectedPersonIds(new Set());
    setError(null);
  }, [image]);

  // Handle image load to get dimensions
  const handleImageLoad = useCallback((e) => {
    setImageDimensions({
      width: e.target.naturalWidth,
      height: e.target.naturalHeight
    });
  }, []);

  // Detect persons in image
  const handleDetect = useCallback(async () => {
    if (!image) {
      setError('画像を選択してください');
      return;
    }

    setIsDetecting(true);
    setError(null);
    setDetectedPersons([]);
    setSelectedPersonIds(new Set());

    try {
      const result = await detectPersons(image, confThreshold);
      setDetectedPersons(result.persons || []);

      if (result.person_count === 0) {
        setError('画像内に人物が検出されませんでした');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDetecting(false);
    }
  }, [image, confThreshold]);

  // Toggle person selection
  const togglePersonSelection = useCallback((personId) => {
    setSelectedPersonIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(personId)) {
        newSet.delete(personId);
      } else {
        newSet.add(personId);
      }
      return newSet;
    });
  }, []);

  // Select all persons
  const selectAllPersons = useCallback(() => {
    setSelectedPersonIds(new Set(detectedPersons.map((p) => p.person_id)));
  }, [detectedPersons]);

  // Deselect all persons
  const deselectAllPersons = useCallback(() => {
    setSelectedPersonIds(new Set());
  }, []);

  // Extract selected persons
  const handleExtract = useCallback(async () => {
    if (selectedPersonIds.size === 0) {
      setError('抽出する人物を選択してください');
      return;
    }

    setIsExtracting(true);
    setError(null);

    try {
      const result = await extractSelectedPersons(
        image,
        Array.from(selectedPersonIds),
        confThreshold,
        20 // padding
      );

      // Pass the processed image to parent
      // Note: rembg is used in backend to remove background during extraction
      if (onProcessedImage && result.processed_image) {
        onProcessedImage(result.processed_image, {
          person_detection: true,
          extracted_count: selectedPersonIds.size,
          total_detected: detectedPersons.length,
          background_removed: true,      // rembg removes background in extraction
          background_composited: false,  // no compositing in person extraction
          quality_enhanced: false        // no quality enhancement in extraction
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsExtracting(false);
    }
  }, [image, selectedPersonIds, confThreshold, onProcessedImage, detectedPersons.length]);

  // Calculate bbox position relative to displayed image
  const getBboxStyle = useCallback((bbox) => {
    if (!imageRef.current || !imageDimensions.width) return {};

    const displayedWidth = imageRef.current.clientWidth;
    const displayedHeight = imageRef.current.clientHeight;

    const scaleX = displayedWidth / imageDimensions.width;
    const scaleY = displayedHeight / imageDimensions.height;

    return {
      left: `${bbox.x1 * scaleX}px`,
      top: `${bbox.y1 * scaleY}px`,
      width: `${(bbox.x2 - bbox.x1) * scaleX}px`,
      height: `${(bbox.y2 - bbox.y1) * scaleY}px`,
    };
  }, [imageDimensions]);

  if (!image || !imagePreview) return null;

  return (
    <div className="person-detector">
      <div
        className="person-detector-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h4>
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
          人物検出・抽出 (オプション)
        </h4>
        <p className="hint">複数人の写真から特定の人物のみを抽出できます</p>
      </div>

      {isExpanded && (
        <div className="person-detector-content">
          {/* Error Display */}
          {error && (
            <div className="detector-error">
              <span className="error-icon">!</span>
              {error}
              <button className="close-btn" onClick={() => setError(null)}>×</button>
            </div>
          )}

          {/* Image Preview with Bounding Boxes */}
          <div className="detection-preview">
            <div className="preview-container">
              <img
                ref={imageRef}
                src={imagePreview}
                alt="Detection Preview"
                className="preview-image"
                onLoad={handleImageLoad}
              />

              {/* Bounding Boxes */}
              {detectedPersons.map((person) => (
                <div
                  key={person.person_id}
                  className={`bbox ${selectedPersonIds.has(person.person_id) ? 'selected' : ''}`}
                  style={getBboxStyle(person.bbox)}
                  onClick={() => togglePersonSelection(person.person_id)}
                >
                  <span className="bbox-label">
                    #{person.person_id + 1} ({Math.round(person.confidence * 100)}%)
                  </span>
                  <span className="bbox-select-indicator">
                    {selectedPersonIds.has(person.person_id) ? '✓' : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Confidence Threshold */}
          <div className="threshold-control">
            <label>
              検出感度: {Math.round(confThreshold * 100)}%
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={confThreshold}
                onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                disabled={disabled || isDetecting || isExtracting}
              />
            </label>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              className="btn btn-detect"
              onClick={handleDetect}
              disabled={disabled || isDetecting || isExtracting}
            >
              {isDetecting ? '検出中...' : '人物を検出'}
            </button>
          </div>

          {/* Detection Results */}
          {detectedPersons.length > 0 && (
            <div className="detection-results">
              <h5>検出結果: {detectedPersons.length}人</h5>
              <div className="selection-buttons">
                <button className="btn-small" onClick={selectAllPersons}>全選択</button>
                <button className="btn-small" onClick={deselectAllPersons}>全解除</button>
              </div>
              <ul className="person-list">
                {detectedPersons.map((person) => (
                  <li
                    key={person.person_id}
                    className={selectedPersonIds.has(person.person_id) ? 'selected' : ''}
                    onClick={() => togglePersonSelection(person.person_id)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPersonIds.has(person.person_id)}
                      onChange={() => togglePersonSelection(person.person_id)}
                    />
                    <span>人物 #{person.person_id + 1}</span>
                    <span className="confidence">
                      {Math.round(person.confidence * 100)}%
                    </span>
                  </li>
                ))}
              </ul>

              {selectedPersonIds.size > 0 && (
                <button
                  className="btn btn-extract"
                  onClick={handleExtract}
                  disabled={disabled || isExtracting}
                >
                  {isExtracting ? '抽出中...' : `選択した${selectedPersonIds.size}人を抽出`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <style>{`
        .person-detector {
          margin: 15px 0;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          background: #fafafa;
          overflow: hidden;
        }

        .person-detector-header {
          padding: 12px 16px;
          cursor: pointer;
          background: linear-gradient(to right, #f8f9fa, #fff);
          border-bottom: 1px solid #e0e0e0;
        }

        .person-detector-header:hover {
          background: linear-gradient(to right, #f0f1f2, #f8f9fa);
        }

        .person-detector-header h4 {
          margin: 0;
          font-size: 14px;
          color: #333;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .toggle-icon {
          font-size: 10px;
          color: #666;
        }

        .hint {
          margin: 4px 0 0 18px;
          font-size: 12px;
          color: #888;
        }

        .person-detector-content {
          padding: 16px;
        }

        .detector-error {
          background: #ffebee;
          color: #c62828;
          padding: 10px 12px;
          border-radius: 6px;
          margin-bottom: 12px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
        }

        .error-icon {
          width: 18px;
          height: 18px;
          background: #c62828;
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 12px;
          flex-shrink: 0;
        }

        .close-btn {
          margin-left: auto;
          background: none;
          border: none;
          font-size: 18px;
          cursor: pointer;
          color: #c62828;
        }

        .detection-preview {
          margin-bottom: 12px;
        }

        .preview-container {
          position: relative;
          display: inline-block;
          max-width: 100%;
        }

        .preview-image {
          max-width: 100%;
          max-height: 300px;
          object-fit: contain;
          border-radius: 6px;
          display: block;
        }

        .bbox {
          position: absolute;
          border: 2px solid #ff9800;
          background: rgba(255, 152, 0, 0.1);
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .bbox:hover {
          border-color: #f57c00;
          background: rgba(255, 152, 0, 0.2);
        }

        .bbox.selected {
          border-color: #4caf50;
          background: rgba(76, 175, 80, 0.2);
        }

        .bbox-label {
          position: absolute;
          top: -20px;
          left: 0;
          background: #ff9800;
          color: white;
          padding: 1px 6px;
          font-size: 10px;
          border-radius: 3px 3px 0 0;
          white-space: nowrap;
        }

        .bbox.selected .bbox-label {
          background: #4caf50;
        }

        .bbox-select-indicator {
          position: absolute;
          top: 2px;
          right: 2px;
          width: 18px;
          height: 18px;
          background: white;
          border: 2px solid #4caf50;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          color: #4caf50;
          font-weight: bold;
        }

        .threshold-control {
          margin: 12px 0;
        }

        .threshold-control label {
          display: flex;
          flex-direction: column;
          gap: 6px;
          color: #666;
          font-size: 13px;
        }

        .threshold-control input[type="range"] {
          width: 100%;
          cursor: pointer;
        }

        .action-buttons {
          display: flex;
          gap: 8px;
          margin: 12px 0;
        }

        .btn {
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .btn-detect {
          background: linear-gradient(135deg, #007bff, #0056b3);
          color: white;
        }

        .btn-detect:hover:not(:disabled) {
          background: linear-gradient(135deg, #0056b3, #004085);
        }

        .btn-extract {
          background: linear-gradient(135deg, #4caf50, #388e3c);
          color: white;
          width: 100%;
          margin-top: 12px;
        }

        .btn-extract:hover:not(:disabled) {
          background: linear-gradient(135deg, #388e3c, #2e7d32);
        }

        .detection-results {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #e0e0e0;
        }

        .detection-results h5 {
          color: #333;
          margin: 0 0 10px 0;
          font-size: 13px;
        }

        .selection-buttons {
          display: flex;
          gap: 6px;
          margin-bottom: 10px;
        }

        .btn-small {
          padding: 4px 10px;
          font-size: 11px;
          background: #f0f0f0;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .btn-small:hover {
          background: #e0e0e0;
        }

        .person-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .person-list li {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 6px;
          cursor: pointer;
          transition: background 0.2s ease;
          font-size: 13px;
        }

        .person-list li:hover {
          background: #f5f5f5;
        }

        .person-list li.selected {
          background: #e8f5e9;
        }

        .person-list li input[type="checkbox"] {
          width: 16px;
          height: 16px;
          cursor: pointer;
        }

        .person-list li .confidence {
          margin-left: auto;
          color: #888;
          font-size: 12px;
        }

        @media (max-width: 600px) {
          .person-detector-content {
            padding: 12px;
          }

          .preview-image {
            max-height: 200px;
          }
        }
      `}</style>
    </div>
  );
};

export default PersonDetector;
