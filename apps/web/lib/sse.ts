import { getApiBaseUrl } from './api';

export interface SseProgressEvent {
  stage?: string;
  percent?: number;
  message?: string;
  [key: string]: unknown;
}

export interface SseTokenEvent {
  text: string;
}

export interface SseCitationEvent {
  file: string;
  start_line: number;
  end_line: number;
  [key: string]: unknown;
}

export interface SseHandlers {
  onProgress?: (data: SseProgressEvent) => void;
  onToken?: (text: string) => void;
  onCitation?: (citation: SseCitationEvent) => void;
  onResult?: (result: unknown) => void;
  onError?: (error: { code?: string; message: string; details?: unknown }) => void;
  onDone?: () => void;
  onComment?: (comment: string) => void;
}

export interface SseOptions extends SseHandlers {
  method?: 'GET' | 'POST';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function streamSse(
  path: string,
  options: SseOptions = {}
): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${normalizedPath}`;

  const headers = new Headers(options.headers);
  headers.set('Accept', 'text/event-stream');
  if (options.body && typeof options.body === 'object' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    method: options.method || (options.body ? 'POST' : 'GET'),
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    let errorDetail = {
      code: 'sse_http_error',
      message: `SSE stream request failed with status ${response.status}`,
    };
    try {
      const json = await response.json();
      if (json?.error) {
        errorDetail = json.error;
      }
    } catch {
      // Body wasn't JSON
    }
    options.onError?.(errorDetail);
    throw new Error(errorDetail.message);
  }

  const body = response.body;
  if (!body) {
    throw new Error('Response body is not a ReadableStream');
  }

  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split SSE chunks by double newline (standard event separator)
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || ''; // Keep incomplete trailing chunk in buffer

      for (const part of parts) {
        if (!part.trim()) continue;

        let eventType = 'message';
        const dataLines: string[] = [];

        const lines = part.split(/\r?\n/);
        for (const line of lines) {
          // Lines starting with colon are comments (e.g. : ping)
          if (line.startsWith(':')) {
            options.onComment?.(line.slice(1).trim());
            continue;
          }

          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim());
          }
        }

        const dataStr = dataLines.join('\n');
        let parsedData: unknown = dataStr;
        if (dataStr) {
          try {
            parsedData = JSON.parse(dataStr);
          } catch {
            parsedData = dataStr;
          }
        }

        switch (eventType) {
          case 'progress':
            options.onProgress?.(parsedData as SseProgressEvent);
            break;
          case 'token':
            if (typeof parsedData === 'object' && parsedData !== null && 'text' in parsedData) {
              options.onToken?.((parsedData as { text: string }).text);
            } else if (typeof parsedData === 'string') {
              options.onToken?.(parsedData);
            }
            break;
          case 'citation':
            options.onCitation?.(parsedData as SseCitationEvent);
            break;
          case 'result':
            options.onResult?.(parsedData);
            break;
          case 'error':
            if (typeof parsedData === 'object' && parsedData !== null) {
              options.onError?.(
                parsedData as { code?: string; message: string; details?: unknown }
              );
            } else {
              options.onError?.({
                code: 'stream_error',
                message: String(parsedData),
              });
            }
            break;
          case 'done':
            options.onDone?.();
            break;
          default:
            // Fallback for message or custom events
            if (eventType === 'message' && dataStr === '[DONE]') {
              options.onDone?.();
            }
            break;
        }
      }
    }
  } catch (err: unknown) {
    if (options.signal?.aborted) {
      // Aborted by user, not an error
      return;
    }
    const message = err instanceof Error ? err.message : 'SSE stream error';
    options.onError?.({ code: 'stream_exception', message });
    throw err;
  } finally {
    reader.releaseLock();
  }
}
