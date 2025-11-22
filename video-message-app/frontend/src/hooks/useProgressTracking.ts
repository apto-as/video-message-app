/**
 * React Hook for Real-time Progress Tracking
 *
 * Supports both WebSocket and SSE (Server-Sent Events) with automatic fallback.
 *
 * Usage:
 * ```tsx
 * const { progress, isConnected, error } = useProgressTracking(taskId, {
 *   preferWebSocket: true,
 *   onComplete: (data) => console.log('Task completed', data),
 *   onError: (error) => console.error('Task failed', error)
 * });
 *
 * return (
 *   <div>
 *     <p>Progress: {progress.progress}%</p>
 *     <p>Stage: {progress.stage}</p>
 *     <p>Message: {progress.message}</p>
 *   </div>
 * );
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface ProgressEvent {
  task_id: string;
  event_type: 'stage_update' | 'progress_update' | 'error' | 'complete' | 'heartbeat';
  data: {
    stage: string;
    progress: number;
    message: string;
    metadata?: Record<string, any>;
    error?: string;
    video_url?: string;
    execution_time_ms?: number;
  };
  timestamp: string;
}

export interface ProgressState {
  stage: string;
  progress: number;
  message: string;
  metadata?: Record<string, any>;
  timestamp: string;
}

export interface UseProgressTrackingOptions {
  /**
   * Prefer WebSocket over SSE (default: true)
   */
  preferWebSocket?: boolean;

  /**
   * Callback when task completes successfully
   */
  onComplete?: (data: ProgressEvent['data']) => void;

  /**
   * Callback when task fails
   */
  onError?: (error: string) => void;

  /**
   * Callback for every progress update
   */
  onProgress?: (progress: ProgressState) => void;

  /**
   * Auto-reconnect on disconnect (default: true)
   */
  autoReconnect?: boolean;

  /**
   * Maximum reconnection attempts (default: 5)
   */
  maxReconnectAttempts?: number;

  /**
   * Base URL for API (default: from environment or localhost)
   */
  baseUrl?: string;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useProgressTracking(
  taskId: string | null,
  options: UseProgressTrackingOptions = {}
) {
  const {
    preferWebSocket = true,
    onComplete,
    onError,
    onProgress,
    autoReconnect = true,
    maxReconnectAttempts = 5,
    baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:55433'
  } = options;

  const [progress, setProgress] = useState<ProgressState>({
    stage: 'initialized',
    progress: 0,
    message: 'Initializing...',
    timestamp: new Date().toISOString()
  });

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionType, setConnectionType] = useState<'websocket' | 'sse' | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ============================================================================
  // WebSocket Connection
  // ============================================================================

  const connectWebSocket = useCallback(() => {
    if (!taskId) return;

    const wsUrl = `${baseUrl.replace('http://', 'ws://').replace('https://', 'wss://')}/api/ws/progress/${taskId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to task ${taskId}`);
        setIsConnected(true);
        setConnectionType('websocket');
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const progressEvent: ProgressEvent = JSON.parse(event.data);

          // Skip heartbeat events
          if (progressEvent.event_type === 'heartbeat') {
            return;
          }

          const newProgress: ProgressState = {
            stage: progressEvent.data.stage,
            progress: progressEvent.data.progress,
            message: progressEvent.data.message,
            metadata: progressEvent.data.metadata,
            timestamp: progressEvent.timestamp
          };

          setProgress(newProgress);
          onProgress?.(newProgress);

          // Handle completion
          if (progressEvent.event_type === 'complete') {
            onComplete?.(progressEvent.data);
          }

          // Handle errors
          if (progressEvent.event_type === 'error') {
            const errorMessage = progressEvent.data.error || progressEvent.data.message;
            setError(errorMessage);
            onError?.(errorMessage);
          }

        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WebSocket] Connection closed: code=${event.code}, reason=${event.reason}`);
        setIsConnected(false);

        // Attempt reconnection
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            if (preferWebSocket) {
              connectWebSocket();
            } else {
              connectSSE();
            }
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached, falling back to SSE');
          connectSSE();
        }
      };

    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err);
      setError('Failed to establish WebSocket connection');

      // Fallback to SSE
      if (preferWebSocket) {
        connectSSE();
      }
    }
  }, [taskId, baseUrl, autoReconnect, maxReconnectAttempts, preferWebSocket, onComplete, onError, onProgress]);

  // ============================================================================
  // SSE Connection
  // ============================================================================

  const connectSSE = useCallback(() => {
    if (!taskId) return;

    const sseUrl = `${baseUrl}/api/sse/progress/${taskId}`;

    try {
      const eventSource = new EventSource(sseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log(`[SSE] Connected to task ${taskId}`);
        setIsConnected(true);
        setConnectionType('sse');
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const progressEvent: ProgressEvent = JSON.parse(event.data);

          // Skip heartbeat events
          if (progressEvent.event_type === 'heartbeat') {
            return;
          }

          const newProgress: ProgressState = {
            stage: progressEvent.data.stage,
            progress: progressEvent.data.progress,
            message: progressEvent.data.message,
            metadata: progressEvent.data.metadata,
            timestamp: progressEvent.timestamp
          };

          setProgress(newProgress);
          onProgress?.(newProgress);

          // Handle completion
          if (progressEvent.event_type === 'complete') {
            onComplete?.(progressEvent.data);
            eventSource.close();
          }

          // Handle errors
          if (progressEvent.event_type === 'error') {
            const errorMessage = progressEvent.data.error || progressEvent.data.message;
            setError(errorMessage);
            onError?.(errorMessage);
            eventSource.close();
          }

        } catch (err) {
          console.error('[SSE] Failed to parse message:', err);
        }
      };

      eventSource.onerror = (event) => {
        console.error('[SSE] Error:', event);
        setIsConnected(false);

        // SSE auto-reconnects by default, but we track attempts
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[SSE] Reconnection attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached');
          eventSource.close();
        }
      };

    } catch (err) {
      console.error('[SSE] Failed to connect:', err);
      setError('Failed to establish SSE connection');
    }
  }, [taskId, baseUrl, autoReconnect, maxReconnectAttempts, onComplete, onError, onProgress]);

  // ============================================================================
  // Connection Management
  // ============================================================================

  useEffect(() => {
    if (!taskId) return;

    // Choose connection method
    if (preferWebSocket) {
      connectWebSocket();
    } else {
      connectSSE();
    }

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [taskId, preferWebSocket, connectWebSocket, connectSSE]);

  // ============================================================================
  // Manual Reconnection
  // ============================================================================

  const reconnect = useCallback(() => {
    // Close existing connections
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Reset reconnection attempts
    reconnectAttemptsRef.current = 0;

    // Reconnect
    if (preferWebSocket) {
      connectWebSocket();
    } else {
      connectSSE();
    }
  }, [preferWebSocket, connectWebSocket, connectSSE]);

  // ============================================================================
  // Return State and Controls
  // ============================================================================

  return {
    progress,
    isConnected,
    error,
    connectionType,
    reconnect
  };
}
