export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const DEFAULT_API_BASE = 'http://localhost:8000/api/v1';

export function getApiBaseUrl(): string {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  return DEFAULT_API_BASE;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${normalizedPath}`;

  const headers = new Headers(options.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  // Set Content-Type: application/json if sending a JSON body
  if (
    options.body &&
    typeof options.body === 'string' &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error ? err.message : 'Network request failed';
    throw new ApiError(
      'network_error',
      `Backend is offline or unreachable: ${errorMsg}`,
      0
    );
  }

  if (!response.ok) {
    let errorData: { error?: ApiErrorDetail } | null = null;
    try {
      const text = await response.text();
      if (text) {
        errorData = JSON.parse(text);
      }
    } catch {
      // Body wasn't JSON
    }

    if (errorData?.error) {
      throw new ApiError(
        errorData.error.code || 'api_error',
        errorData.error.message || `Request failed with status ${response.status}`,
        response.status,
        errorData.error.details
      );
    }

    throw new ApiError(
      'http_error',
      `HTTP error ${response.status}: ${response.statusText}`,
      response.status
    );
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

export const api = {
  get: <T>(path: string, options?: RequestInit) =>
    apiFetch<T>(path, { ...options, method: 'GET' }),

  post: <T>(path: string, body?: unknown, options?: RequestInit) =>
    apiFetch<T>(path, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown, options?: RequestInit) =>
    apiFetch<T>(path, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string, options?: RequestInit) =>
    apiFetch<T>(path, { ...options, method: 'DELETE' }),
};
