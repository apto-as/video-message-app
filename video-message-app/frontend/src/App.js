import React, { useState } from 'react';
import VideoGenerator from './components/VideoGenerator';
import VoiceCloneUpload from './components/VoiceCloneUpload';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('video'); // 'video', 'voice-clone'
  const [voiceListRefreshKey, setVoiceListRefreshKey] = useState(0);

  return (
    <div className="App">
      <nav className="app-navigation">
        <div className="nav-container">
          <div className="nav-brand">
            <h2>🎬 動画メッセージアプリ</h2>
          </div>
          <div className="nav-links">
            <button
              className={`nav-button ${currentPage === 'video' ? 'active' : ''}`}
              onClick={() => setCurrentPage('video')}
            >
              📹 動画生成
            </button>
            <button
              className={`nav-button ${currentPage === 'voice-clone' ? 'active' : ''}`}
              onClick={() => setCurrentPage('voice-clone')}
            >
              🎙️ 音声クローン
            </button>
          </div>
        </div>
      </nav>

      <main className="app-main">
        {currentPage === 'video' && <VideoGenerator key={voiceListRefreshKey} />}
        {currentPage === 'voice-clone' && (
          <VoiceCloneUpload 
            onUploadComplete={(profileId) => {
              console.log('音声クローン登録完了:', profileId);
              // 音声リストを更新
              setVoiceListRefreshKey(prev => prev + 1);
            }}
            onProfileUpdate={() => {
              // プロファイル削除時にも音声リストを更新
              setVoiceListRefreshKey(prev => prev + 1);
            }}
          />
        )}
      </main>

      <style>{`
        .app-navigation {
          background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
          color: white;
          padding: 0;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          position: sticky;
          top: 0;
          z-index: 1000;
        }

        .nav-container {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 20px;
        }

        .nav-brand h2 {
          margin: 0;
          font-size: 20px;
          font-weight: bold;
          background: linear-gradient(45deg, #fff, #e3f2fd);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .nav-links {
          display: flex;
          gap: 0;
          background-color: rgba(255, 255, 255, 0.1);
          border-radius: 25px;
          padding: 4px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .nav-button {
          background: none;
          border: none;
          color: white;
          padding: 10px 20px;
          border-radius: 21px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          white-space: nowrap;
          position: relative;
          text-align: center;
          min-width: 120px;
        }

        .nav-button:hover:not(.active) {
          background-color: rgba(255, 255, 255, 0.15);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .nav-button.active {
          background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
          color: #007bff;
          box-shadow: 0 4px 16px rgba(0,0,0,0.2);
          transform: translateY(-2px);
        }

        .nav-button.active::before {
          content: '';
          position: absolute;
          top: -2px;
          left: -2px;
          right: -2px;
          bottom: -2px;
          background: linear-gradient(135deg, #007bff, #0056b3);
          border-radius: 23px;
          z-index: -1;
        }

        .app-main {
          min-height: calc(100vh - 70px);
          padding: 20px;
          background-color: #f8f9fa;
          display: flex;
          justify-content: center;
          align-items: flex-start;
        }

        @media (max-width: 768px) {
          .nav-container {
            padding: 10px 15px;
            flex-direction: column;
            gap: 12px;
          }

          .nav-brand h2 {
            font-size: 18px;
          }

          .nav-links {
            order: 2;
          }

          .nav-button {
            min-width: 100px;
            padding: 8px 16px;
            font-size: 13px;
          }

          .app-main {
            padding: 15px;
            min-height: calc(100vh - 90px);
          }
        }

        @media (max-width: 480px) {
          .nav-container {
            padding: 8px 12px;
          }

          .nav-brand h2 {
            font-size: 16px;
          }

          .nav-links {
            flex-direction: column;
            width: 100%;
            max-width: 280px;
            gap: 4px;
            padding: 6px;
            border-radius: 12px;
          }

          .nav-button {
            width: 100%;
            min-width: auto;
            padding: 12px 16px;
            font-size: 14px;
            border-radius: 8px;
          }

          .nav-button.active::before {
            border-radius: 10px;
          }
        }
      `}</style>
    </div>
  );
}

export default App;
