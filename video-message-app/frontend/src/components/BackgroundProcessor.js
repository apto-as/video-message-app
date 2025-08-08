import React, { useState } from 'react';

const BackgroundProcessor = ({ 
    onImageProcessed, 
    disabled = false,
    image = null 
}) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [backgroundImage, setBackgroundImage] = useState(null);
    const [removeBackground, setRemoveBackground] = useState(true);
    const [enhanceQuality, setEnhanceQuality] = useState(true);
    const [processedImageUrl, setProcessedImageUrl] = useState(null);

    const handleBackgroundImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert('背景画像ファイルのみアップロード可能です');
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                alert('ファイルサイズは5MB以下にしてください');
                return;
            }
            setBackgroundImage(file);
        }
    };

    const processImage = async () => {
        if (!image) {
            alert('まず、メイン画像をアップロードしてください');
            return;
        }

        // 背景削除も背景画像もない場合は処理をスキップ
        if (!removeBackground && !backgroundImage) {
            alert('背景削除または背景画像を選択してください');
            return;
        }

        setIsProcessing(true);
        setProcessedImageUrl(null);

        try {
            const formData = new FormData();
            formData.append('image', image);
            formData.append('remove_background', removeBackground);
            formData.append('enhance_quality', enhanceQuality);
            
            if (backgroundImage) {
                formData.append('background', backgroundImage);
            }

            const response = await fetch('http://localhost:55433/api/process-image', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '画像処理に失敗しました');
            }

            const result = await response.json();
            
            if (result.success) {
                if (result.processed_image) {
                    setProcessedImageUrl(result.processed_image);
                    if (onImageProcessed) {
                        onImageProcessed(result.processed_image, result.processing_info);
                    }
                } else {
                    // 処理が実行されなかった場合
                    alert('処理条件が満たされていません');
                }
            }

        } catch (error) {
            console.error('Image processing error:', error);
            
            // より詳細なエラーメッセージを提供
            let errorMessage = '画像処理エラーが発生しました。';
            
            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                errorMessage = '🚨 バックエンドサーバーに接続できません。\n\n' +
                              '対処法:\n' +
                              '1. サーバーが起動しているか確認してください\n' +
                              '2. http://localhost:55433/health で接続テストを行ってください\n' +
                              '3. ネットワーク接続を確認してください';
            } else if (error.message.includes('CORS')) {
                errorMessage = '🔒 CORS（Cross-Origin）エラーが発生しました。サーバー設定を確認してください。';
            } else if (error.message.includes('timeout')) {
                errorMessage = '⏱️ 処理がタイムアウトしました。画像サイズを小さくしてお試しください。';
            } else {
                errorMessage = `❌ 処理エラー: ${error.message}`;
            }
            
            alert(errorMessage);
        } finally {
            setIsProcessing(false);
        }
    };

    const clearProcessing = () => {
        setProcessedImageUrl(null);
        setBackgroundImage(null);
        if (onImageProcessed) {
            onImageProcessed(null, null);
        }
    };

    return (
        <div className="background-processor">
            <h3>🎨 背景処理設定</h3>
            
            <div className="processing-options">
                <label className="checkbox-label">
                    <input
                        type="checkbox"
                        checked={removeBackground}
                        onChange={(e) => setRemoveBackground(e.target.checked)}
                        disabled={disabled || isProcessing}
                    />
                    背景を削除する
                </label>

                <label className="checkbox-label">
                    <input
                        type="checkbox"
                        checked={enhanceQuality}
                        onChange={(e) => setEnhanceQuality(e.target.checked)}
                        disabled={disabled || isProcessing}
                    />
                    画質を向上させる
                </label>
            </div>

            {removeBackground && (
                <div className="background-upload">
                    <label className="file-label">
                        <span>🖼️ 背景画像を選択（オプション）:</span>
                        <input
                            type="file"
                            accept="image/*"
                            onChange={handleBackgroundImageChange}
                            disabled={disabled || isProcessing}
                            className="file-input"
                        />
                    </label>
                    {backgroundImage && (
                        <p className="file-info">
                            選択された背景: {backgroundImage.name}
                        </p>
                    )}
                </div>
            )}

            <div className="process-controls">
                <button
                    onClick={processImage}
                    disabled={disabled || isProcessing || !image || (!removeBackground && !backgroundImage)}
                    className="process-button"
                >
                    {isProcessing ? '🔄 処理中...' : 
                     backgroundImage ? '🎨 背景合成して処理' :
                     removeBackground ? '✂️ 背景削除して処理' : 
                     '✨ 画像を処理'}
                </button>

                {processedImageUrl && (
                    <button
                        onClick={clearProcessing}
                        disabled={disabled || isProcessing}
                        className="clear-button"
                    >
                        🗑️ 処理をクリア
                    </button>
                )}
            </div>

            {!removeBackground && !backgroundImage && (
                <div className="info-message">
                    💡 背景削除または背景画像を選択すると処理が実行されます
                </div>
            )}

            {processedImageUrl && (
                <div className="processed-preview">
                    <h4>✅ 処理済み画像</h4>
                    <img 
                        src={processedImageUrl} 
                        alt="処理済み画像" 
                        className="processed-image"
                        style={{ maxWidth: '300px', height: 'auto' }}
                    />
                </div>
            )}

            <style>{`
                .background-processor {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    background-color: #f9f9f9;
                }

                .processing-options {
                    margin: 15px 0;
                }

                .checkbox-label {
                    display: block;
                    margin: 10px 0;
                    cursor: pointer;
                }

                .checkbox-label input {
                    margin-right: 8px;
                }

                .background-upload {
                    margin: 15px 0;
                    padding: 15px;
                    border: 1px dashed #ccc;
                    border-radius: 6px;
                    background-color: #fff;
                }

                .file-label {
                    display: block;
                    cursor: pointer;
                }

                .file-input {
                    margin-top: 10px;
                    width: 100%;
                }

                .file-info {
                    margin-top: 10px;
                    color: #666;
                    font-size: 14px;
                }

                .process-controls {
                    margin: 20px 0;
                    display: flex;
                    gap: 10px;
                }

                .process-button, .clear-button {
                    padding: 12px 24px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    transition: background-color 0.3s;
                }

                .process-button {
                    background-color: #007bff;
                    color: white;
                }

                .process-button:hover:not(:disabled) {
                    background-color: #0056b3;
                }

                .process-button:disabled {
                    background-color: #ccc;
                    cursor: not-allowed;
                }

                .clear-button {
                    background-color: #dc3545;
                    color: white;
                }

                .clear-button:hover:not(:disabled) {
                    background-color: #a71e2a;
                }

                .processed-preview {
                    margin-top: 20px;
                    padding: 15px;
                    border: 1px solid #28a745;
                    border-radius: 6px;
                    background-color: #f8fff9;
                }

                .processed-image {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    margin-top: 10px;
                }

                .info-message {
                    margin: 15px 0;
                    padding: 10px;
                    background-color: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    border-radius: 4px;
                    color: #0066cc;
                    font-size: 14px;
                }
            `}</style>
        </div>
    );
};

export default BackgroundProcessor;