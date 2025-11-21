import React from 'react';
import './DIdErrorBoundary.css';

class DIdErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[DIdSelector Error]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="did-error-fallback">
          <div className="error-icon">⚠️</div>
          <h3>リップシンク設定の読み込みに失敗しました</h3>
          <p className="error-message">
            {this.state.error?.message || '不明なエラーが発生しました'}
          </p>
          <button
            className="reload-button"
            onClick={() => window.location.reload()}
          >
            ページを再読み込み
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default DIdErrorBoundary;
