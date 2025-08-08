/**
 * D-ID API サービス（動画生成機能のみ）
 * 音声クローニング機能は削除し、OpenVoice V2を使用
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

class DIdService {
  private baseUrl = '/api/d-id';

  /**
   * D-IDを使用して動画を生成
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
      console.error('D-ID動画生成エラー:', error);
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
   * D-IDサービスのヘルスチェック
   */
  async healthCheck(): Promise<{ status: string; api_key_configured: boolean }> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);

      if (!response.ok) {
        throw new Error(`ヘルスチェックに失敗しました: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('D-IDヘルスチェックエラー:', error);
      return { status: 'error', api_key_configured: false };
    }
  }
}

export const dIdService = new DIdService();