// Minimal API client. The access token lives in memory only; the refresh token is an httpOnly
// cookie the browser sends to /api/v1/auth/* (never readable from JavaScript).

import type { ListParams, TokenResponse } from './types'

export const API_BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Field-level messages from a 422 response, keyed by field name. */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {}
    if (Array.isArray(this.details)) {
      for (const d of this.details as { field?: string; message?: string }[]) {
        if (d.field && d.message && !(d.field in out)) out[d.field] = d.message
      }
    }
    return out
  }
}

let accessToken: string | null = null
let refreshing: Promise<boolean> | null = null
let onSessionExpired: (() => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { error?: { code: string; message: string; details?: unknown } }
    if (body.error) {
      return new ApiError(response.status, body.error.code, body.error.message, body.error.details)
    }
  } catch {
    // fall through to a generic error
  }
  return new ApiError(response.status, 'error', response.statusText || 'Request failed')
}

/** Exchange the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'same-origin' })
    .then(async (response) => {
      if (!response.ok) {
        setAccessToken(null)
        return false
      }
      const body = (await response.json()) as TokenResponse
      setAccessToken(body.access_token)
      return true
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

export function toQuery(params?: ListParams): string {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== null) search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

interface RequestOptions {
  method?: string
  body?: unknown
  form?: URLSearchParams | FormData
  raw?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {}
  let body: BodyInit | undefined
  if (options.form) {
    body = options.form
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body,
    credentials: 'same-origin',
  })

  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await refreshSession()) return request<T>(path, options, false)
    onSessionExpired?.()
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  if (options.raw) return (await response.text()) as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, params?: ListParams) => request<T>(`${path}${toQuery(params)}`),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
  text: (path: string) => request<string>(path, { raw: true }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<T>(path, { method: 'POST', form })
  },
}

/** Human-readable message for any thrown value. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}
