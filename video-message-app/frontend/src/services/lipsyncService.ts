/**
 * リップシンク動画生成 API（MuseTalk経由）
 * 音声合成にはQwen3-TTSを使用
 * エンドポイント: /api/lipsync/*
 */

export interface VideoGenerationRequest {
  audio_url: string;
  source_url: string;  // リップシンクには必須
}

export interface VideoGenerationResponse {
  id: string;
  status: string;
  result_url?: string;
  created_at: string;
}

export interface SourceImageUploadResponse {
  url: string;
}

class LipsyncService {
  private baseUrl = '/api/lipsync';

  /**
   * リップシンク動画を生成（MuseTalk経由）
   */
  async generateVideo(request: VideoGenerationRequest): Promise<VideoGenerationResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/generate-video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `動画生成に失敗しました: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('リップシンク動画生成エラー:', error);
      throw error;
    }
  }

  // プレゼンター機能は削除されました
  // リップシンク動画生成のみサポート

  /**
   * ソース画像をアップロード
   */
  async uploadSourceImage(file: File): Promise<SourceImageUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.baseUrl}/upload-source-image`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `画像アップロードに失敗しました: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('画像アップロードエラー:', error);
      throw error;
    }
  }

  /**
   * リップシンクサービスのヘルスチェック
   */
  async healthCheck(): Promise<{ status: string; primary_service?: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);

      if (!response.ok) {
        throw new Error(`ヘルスチェックに失敗しました: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('リップシンクヘルスチェックエラー:', error);
      return { status: 'error' };
    }
  }
}

export const lipsyncService = new LipsyncService();