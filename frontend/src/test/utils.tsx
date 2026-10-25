import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { vi } from 'vitest'
import { AuthProvider, useAuth } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'
import { ToastProvider } from '@/lib/toast'
import type { User } from '@/lib/types'

export const ADMIN: User = {
  id: 1,
  email: 'admin@edupulse.example',
  full_name: 'Demo Administrator',
  role: 'admin',
  is_active: true,
  teacher_id: null,
  last_login_at: null,
}

export const TEACHER: User = { ...ADMIN, id: 2, email: 't@edupulse.example', full_name: 'Tea Cher', role: 'teacher', teacher_id: 7 }

type Handler = (init: RequestInit | undefined, url: URL) => { status?: number; body?: unknown }

/** Replace global fetch with a router keyed by "METHOD /path" (query string ignored). */
export function mockApi(routes: Record<string, Handler | unknown>, user: User | null = ADMIN) {
  const calls: { method: string; path: string; body: unknown }[] = []
  const all: Record<string, Handler | unknown> = {
    'POST /api/v1/auth/refresh': user ? { access_token: 'token', token_type: 'bearer', expires_in: 900, refresh_token: 'r' } : { __status: 401 },
    'GET /api/v1/auth/me': user,
    ...routes,
  }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const method = (init?.method ?? 'GET').toUpperCase()
    const key = `${method} ${url.pathname}`
    let body: unknown = init?.body
    if (typeof body === 'string') {
      try {
        body = JSON.parse(body)
      } catch {
        // form-encoded body: keep as string
      }
    }
    calls.push({ method, path: url.pathname + url.search, body })
    if (!(key in all)) return new Response(JSON.stringify({ error: { code: 'not_found', message: `No mock for ${key}` } }), { status: 404 })
    const entry = all[key]
    const result = typeof entry === 'function' ? (entry as Handler)(init, url) : { body: entry }
    const value = result.body as { __status?: number } | undefined
    const status = result.status ?? value?.__status ?? 200
    if (status === 204) return new Response(null, { status })
    return new Response(JSON.stringify(result.body ?? null), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, calls }
}

/** Mirrors the app's RequireAuth guard: protected pages only render for a signed-in user. */
function AuthGate({ children, requireAuth }: { children: ReactNode; requireAuth: boolean }) {
  const { status } = useAuth()
  if (status === 'loading') return <p>auth-loading</p>
  if (requireAuth && status === 'anonymous') return <p>signed out</p>
  return children
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '*', requireAuth = true }: { route?: string; path?: string; requireAuth?: boolean } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={[route]}>
            <AuthProvider>
              <AuthGate requireAuth={requireAuth}>
                <Routes>
                  <Route path={path} element={ui} />
                  <Route path="*" element={<p>other route</p>} />
                </Routes>
              </AuthGate>
            </AuthProvider>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}
