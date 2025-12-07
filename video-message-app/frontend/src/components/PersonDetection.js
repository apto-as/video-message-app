import React, { useState, useRef, useCallback, useEffect } from 'react';
import { detectPersons, extractSelectedPersons, getPersonDetectionHealth } from '../services/api';
import './PersonDetection.css';

/**
 * Person Detection Component
 * - 画像をアップロード
 * - 人物を検出してバウンディングボックスを表示
 * - 残したい人物を選択
 * - 選択した人物以外を背景と一緒に削除
 */
const PersonDetection = () => {
  // State
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [detectedPersons, setDetectedPersons] = useState([]);
  const [selectedPersonIds, setSelectedPersonIds] = useState(new Set());
  const [isDetecting, setIsDetecting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedImage, setExtractedImage] = useState(null);
  const [error, setError] = useState(null);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [confThreshold, setConfThreshold] = useState(0.5);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [transparentPaddingSize, setTransparentPaddingSize] = useState(300);
  const [addTransparentPadding, setAddTransparentPadding] = useState(true);

  const fileInputRef = useRef(null);
  const imageRef = useRef(null);

  // Check service health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await getPersonDetectionHealth();
        setServiceStatus(health);
      } catch (err) {
        setServiceStatus({ status: 'unavailable', error: err.message });
      }
    };
    checkHealth();
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback((e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('画像ファイルを選択してください');
      return;
    }

    setImageFile(file);
    setDetectedPersons([]);
    setSelectedPersonIds(new Set());
    setExtractedImage(null);
    setError(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target.result);
    };
    reader.readAsDataURL(file);
  }, []);

  // Handle image load to get dimensions
  const handleImageLoad = useCallback((e) => {
    setImageDimensions({
      width: e.target.naturalWidth,
      height: e.target.naturalHeight
    });
  }, []);

  // Handle drag and drop
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      if (fileInputRef.current) {
        fileInputRef.current.files = dataTransfer.files;
        handleFileSelect({ target: { files: dataTransfer.files } });
      }
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  // Detect persons in image
  const handleDetect = useCallback(async () => {
    if (!imageFile) {
      setError('画像を選択してください');
      return;
    }

    setIsDetecting(true);
    setError(null);
    setDetectedPersons([]);
    setSelectedPersonIds(new Set());

    try {
      const result = await detectPersons(imageFile, confThreshold);
      setDetectedPersons(result.persons || []);

      if (result.person_count === 0) {
        setError('画像内に人物が検出されませんでした');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDetecting(false);
    }
  }, [imageFile, confThreshold]);

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
    setExtractedImage(null);

    try {
      const result = await extractSelectedPersons(
        imageFile,
        Array.from(selectedPersonIds),
        confThreshold,
        20, // padding
        addTransparentPadding,
        transparentPaddingSize
      );

      setExtractedImage(result.processed_image);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsExtracting(false);
    }
  }, [imageFile, selectedPersonIds, confThreshold, addTransparentPadding, transparentPaddingSize]);

  // Download extracted image
  const handleDownload = useCallback(() => {
    if (!extractedImage) return;

    const link = document.createElement('a');
    link.href = extractedImage;
    link.download = 'extracted_persons.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [extractedImage]);

  // Reset all state
  const handleReset = useCallback(() => {
    setImageFile(null);
    setImagePreview(null);
    setDetectedPersons([]);
    setSelectedPersonIds(new Set());
    setExtractedImage(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

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

  return (
    <div className="person-detection-container">
      <div className="person-detection-header">
        <h2>人物検出・抽出</h2>
        <p className="description">
          画像から人物を検出し、選択した人物のみを残して背景を削除します
        </p>

        {/* Service Status */}
        {serviceStatus && (
          <div className={`service-status ${serviceStatus.status === 'healthy' ? 'healthy' : 'unhealthy'}`}>
            {serviceStatus.status === 'healthy' ? (
              <>
                <span className="status-dot"></span>
                GPU: {serviceStatus.model?.cuda_device || 'CPU'}
              </>
            ) : (
              <>
                <span className="status-dot error"></span>
                サービス利用不可
              </>
            )}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <span className="error-icon">!</span>
          {error}
        </div>
      )}

      <div className="person-detection-content">
        {/* Left Panel: Image Upload & Detection */}
        <div className="panel upload-panel">
          <h3>1. 画像をアップロード</h3>

          {/* Drop Zone */}
          <div
            className={`drop-zone ${imagePreview ? 'has-image' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />

            {imagePreview ? (
              <div className="image-preview-container">
                <img
                  ref={imageRef}
                  src={imagePreview}
                  alt="Preview"
                  className="preview-image"
                  onLoad={handleImageLoad}
                />

                {/* Bounding Boxes */}
                {detectedPersons.map((person) => (
                  <div
                    key={person.person_id}
                    className={`bbox ${selectedPersonIds.has(person.person_id) ? 'selected' : ''}`}
                    style={getBboxStyle(person.bbox)}
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePersonSelection(person.person_id);
                    }}
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
            ) : (
              <div className="drop-zone-placeholder">
                <div className="drop-icon">📷</div>
                <p>クリックまたはドラッグ&ドロップで画像を選択</p>
                <p className="file-hint">JPEG, PNG対応</p>
              </div>
            )}
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
              />
            </label>
          </div>

          {/* Transparent Padding Settings */}
          <div className="padding-control">
            <label className="padding-checkbox">
              <input
                type="checkbox"
                checked={addTransparentPadding}
                onChange={(e) => setAddTransparentPadding(e.target.checked)}
              />
              透明パディングを追加
            </label>
            {addTransparentPadding && (
              <label className="padding-slider">
                パディングサイズ: {transparentPaddingSize}px
                <input
                  type="range"
                  min="0"
                  max="500"
                  step="50"
                  value={transparentPaddingSize}
                  onChange={(e) => setTransparentPaddingSize(parseInt(e.target.value))}
                />
              </label>
            )}
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              className="btn btn-primary"
              onClick={handleDetect}
              disabled={!imageFile || isDetecting}
            >
              {isDetecting ? '検出中...' : '人物を検出'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleReset}
              disabled={!imageFile}
            >
              リセット
            </button>
          </div>

          {/* Detection Results */}
          {detectedPersons.length > 0 && (
            <div className="detection-results">
              <h4>検出結果: {detectedPersons.length}人</h4>
              <div className="selection-buttons">
                <button className="btn btn-small" onClick={selectAllPersons}>
                  全選択
                </button>
                <button className="btn btn-small" onClick={deselectAllPersons}>
                  全解除
                </button>
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
            </div>
          )}
        </div>

        {/* Right Panel: Extraction Result */}
        <div className="panel result-panel">
          <h3>2. 抽出結果</h3>

          {selectedPersonIds.size > 0 && (
            <div className="selection-info">
              <p>選択中: {selectedPersonIds.size}人</p>
              <button
                className="btn btn-primary"
                onClick={handleExtract}
                disabled={isExtracting}
              >
                {isExtracting ? '抽出中...' : '選択した人物を抽出'}
              </button>
            </div>
          )}

          {isExtracting && (
            <div className="extracting-indicator">
              <div className="spinner"></div>
              <p>背景を削除しています...</p>
            </div>
          )}

          {extractedImage && (
            <div className="extracted-result">
              <div className="extracted-image-container">
                <img
                  src={extractedImage}
                  alt="Extracted persons"
                  className="extracted-image"
                />
              </div>
              <button className="btn btn-success" onClick={handleDownload}>
                ダウンロード (PNG)
              </button>
            </div>
          )}

          {!extractedImage && !isExtracting && (
            <div className="result-placeholder">
              <p>画像をアップロードし、残したい人物を選択してください</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PersonDetection;
