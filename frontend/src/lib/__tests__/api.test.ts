import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, refreshSession, setAccessToken, setSessionExpiredHandler, toQuery } from '../api'

function respond(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  setAccessToken(null)
  setSessionExpiredHandler(null)
  vi.unstubAllGlobals()
})

describe('api client', () => {
  it('sends the bearer token and parses JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('abc')
    await expect(api.get('/things', { page: 2, q: '', sort: undefined })).resolves.toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/things?page=2')
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer abc')
  })

  it('refreshes once on 401 and retries the request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respond(401, { error: { code: 'unauthorized', message: 'expired' } }))
      .mockResolvedValueOnce(respond(200, { access_token: 'new', token_type: 'bearer', expires_in: 900 }))
      .mockResolvedValueOnce(respond(200, { id: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('old')
    await expect(api.get('/students/1')).resolves.toEqual({ id: 1 })
    expect(fetchMock.mock.calls[1]![0]).toBe('/api/v1/auth/refresh')
    const retried = fetchMock.mock.calls[2]![1] as RequestInit
    expect((retried.headers as Record<string, string>).Authorization).toBe('Bearer new')
  })

  it('reports an expired session when the refresh fails', async () => {
    const expired = vi.fn()
    setSessionExpiredHandler(expired)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(respond(401, { error: { code: 'unauthorized', message: 'expired' } }))
        .mockResolvedValueOnce(respond(401, { error: { code: 'unauthorized', message: 'bad refresh' } })),
    )
    await expect(api.get('/students')).rejects.toBeInstanceOf(ApiError)
    expect(expired).toHaveBeenCalledOnce()
  })

  it('consumes the body of a failed refresh so the request can complete', async () => {
    const failed = respond(401, { error: { code: 'unauthorized', message: 'no cookie' } })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(failed))
    await expect(refreshSession()).resolves.toBe(false)
    expect(failed.bodyUsed).toBe(true)
  })

  it('turns error bodies into ApiError with field errors', async () => {
    const details = [
      { field: 'email', message: 'bad email', type: 'value_error' },
      { field: 'email', message: 'second', type: 'x' },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respond(422, { error: { code: 'validation_error', message: 'Invalid', details } })),
    )
    const error = (await api.post('/students', {}).catch((e: unknown) => e)) as ApiError
    expect(error.status).toBe(422)
    expect(error.code).toBe('validation_error')
    expect(error.fieldErrors()).toEqual({ email: 'bad email' })
  })

  it('handles 204 and non-JSON errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(respond(204))
        .mockResolvedValueOnce(new Response('oops', { status: 500, statusText: 'Server Error' })),
    )
    await expect(api.delete('/students/1')).resolves.toBeUndefined()
    await expect(api.get('/x')).rejects.toMatchObject({ status: 500, message: 'Server Error' })
  })

  it('builds query strings without empty values', () => {
    expect(toQuery()).toBe('')
    expect(toQuery({ q: 'ana maria', page: 1, sort: '' })).toBe('?q=ana+maria&page=1')
  })
})
