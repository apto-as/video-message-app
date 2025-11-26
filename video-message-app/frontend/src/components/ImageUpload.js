import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

const ImageUpload = ({ onImageSelect, selectedImage, onPreviewChange }) => {
  const [preview, setPreview] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      onImageSelect(file);

      // プレビュー作成
      const reader = new FileReader();
      reader.onload = () => {
        setPreview(reader.result);
        // 親コンポーネントにプレビューURLを通知
        if (onPreviewChange) {
          onPreviewChange(reader.result);
        }
      };
      reader.readAsDataURL(file);
    }
  }, [onImageSelect, onPreviewChange]);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: 5 * 1024 * 1024, // 5MB
    multiple: false
  });

  return (
    <div className="image-upload-container">
      <div {...getRootProps()} className={`image-upload ${isDragActive ? 'drag-active' : ''}`}>
        <input {...getInputProps()} />
        {preview ? (
          <div className="image-preview">
            <img src={preview} alt="プレビュー" />
            <p>別の画像を選択する場合はクリックまたはドロップしてください</p>
          </div>
        ) : (
          <div className="upload-placeholder">
            {isDragActive ? (
              <p>ここに画像をドロップしてください</p>
            ) : (
              <div>
                <p>画像をドラッグ&ドロップ、またはクリックして選択</p>
                <p className="upload-note">JPG, PNG形式、5MB以下</p>
              </div>
            )}
          </div>
        )}
      </div>
      {fileRejections.length > 0 && (
        <div className="error-message">
          {fileRejections[0].errors[0].message}
        </div>
      )}
    </div>
  );
};

export default ImageUpload;