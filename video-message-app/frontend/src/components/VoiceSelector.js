import React, { useState, useEffect } from 'react';
import { getVoices, getCustomVoices } from '../services/api';

const VoiceSelector = ({ selectedVoice, onVoiceChange, disabled = false }) => {
    const [voices, setVoices] = useState({});
    const [customVoices, setCustomVoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadVoices();
    }, []);

    const loadVoices = async () => {
        try {
            setLoading(true);
            
            // システム音声を取得
            const systemResponse = await getVoices();
            let systemVoices = {};
            if (systemResponse.success) {
                systemVoices = systemResponse.voices;
            }
            
            // カスタム音声を取得
            let customVoicesList = [];
            try {
                const customResponse = await getCustomVoices();
                if (customResponse.success) {
                    // クローン完了したカスタム音声のみを表示
                    customVoicesList = customResponse.voices.filter(voice => 
                        voice.status === 'ready' && voice.did_voice_id
                    );
                }
            } catch (customErr) {
                console.warn('Custom voices loading failed:', customErr);
            }
            
            setVoices(systemVoices);
            setCustomVoices(customVoicesList);
            
            // デフォルト音声が設定されていない場合は設定
            if (!selectedVoice && systemResponse.default_voice) {
                onVoiceChange(systemResponse.default_voice);
            }
        } catch (err) {
            console.error('Voice loading error:', err);
            setError('音声一覧の読み込みに失敗しました');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="voice-selector">
                <label className="voice-label">🎤 音声を選択:</label>
                <div className="voice-loading">読み込み中...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="voice-selector">
                <label className="voice-label">🎤 音声を選択:</label>
                <div className="voice-error">{error}</div>
            </div>
        );
    }

    return (
        <div className="voice-selector">
            <label className="voice-label" htmlFor="voice-select">
                🎤 音声を選択:
            </label>
            <select
                id="voice-select"
                value={selectedVoice || ''}
                onChange={(e) => onVoiceChange(e.target.value)}
                disabled={disabled}
                className="voice-dropdown"
            >
                {/* システム音声 */}
                <optgroup label="🔊 システム音声">
                    {Object.entries(voices).map(([voiceId, voiceName]) => (
                        <option key={voiceId} value={voiceId}>
                            {voiceName}
                        </option>
                    ))}
                </optgroup>
                
                {/* カスタム音声 */}
                {customVoices.length > 0 && (
                    <optgroup label="🎤 カスタム音声">
                        {customVoices.map(voice => (
                            <option key={voice.did_voice_id} value={voice.did_voice_id}>
                                {voice.name} (マイ音声)
                            </option>
                        ))}
                    </optgroup>
                )}
            </select>
            
            {customVoices.length === 0 && (
                <div className="custom-voice-hint">
                    <p>💡 <a href="/voice-manager" target="_blank">カスタム音声管理</a>で自分の声を登録できます</p>
                </div>
            )}

            <style>{`
                .voice-selector {
                    margin: 15px 0;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: #f9f9f9;
                }

                .voice-label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: bold;
                    color: #333;
                    font-size: 14px;
                }

                .voice-dropdown {
                    width: 100%;
                    padding: 10px 12px;
                    border: 2px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                    background-color: white;
                    cursor: pointer;
                    transition: border-color 0.3s, box-shadow 0.3s;
                }

                .voice-dropdown:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
                }

                .voice-dropdown:disabled {
                    background-color: #f5f5f5;
                    cursor: not-allowed;
                    opacity: 0.6;
                }

                .voice-loading {
                    padding: 10px;
                    text-align: center;
                    color: #666;
                    font-style: italic;
                }

                .voice-error {
                    padding: 10px;
                    background-color: #ffe6e6;
                    border: 1px solid #ffcccc;
                    border-radius: 4px;
                    color: #cc0000;
                    font-size: 14px;
                }

                .voice-dropdown option {
                    padding: 8px;
                    font-size: 14px;
                }

                /* ホバー効果 */
                .voice-dropdown:hover:not(:disabled) {
                    border-color: #007bff;
                }

                /* カスタム音声ヒント */
                .custom-voice-hint {
                    margin-top: 10px;
                    padding: 8px 12px;
                    background-color: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    border-radius: 4px;
                    font-size: 12px;
                }

                .custom-voice-hint p {
                    margin: 0;
                    color: #0066cc;
                }

                .custom-voice-hint a {
                    color: #0066cc;
                    text-decoration: none;
                    font-weight: bold;
                }

                .custom-voice-hint a:hover {
                    text-decoration: underline;
                }

                /* オプショングループのスタイル */
                .voice-dropdown optgroup {
                    font-weight: bold;
                    font-size: 13px;
                    color: #555;
                }

                .voice-dropdown optgroup option {
                    font-weight: normal;
                    color: #333;
                }

                /* スタイルの統一感のための追加CSS */
                .voice-selector {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
            `}</style>
        </div>
    );
};

export default VoiceSelector;