import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { API_BASE, ApiError, api, refreshSession, setAccessToken, setSessionExpiredHandler } from './api'
import type { TokenResponse, User } from './types'

interface AuthState {
  user: User | null
  status: 'loading' | 'authenticated' | 'anonymous'
  /** Why the last session ended: a deliberate sign-out, or expiry/refusal by the server. */
  endedBy: 'logout' | 'expired' | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [endedBy, setEndedBy] = useState<AuthState['endedBy']>(null)

  const clear = useCallback((reason: 'logout' | 'expired' = 'expired') => {
    setEndedBy(reason)
    setAccessToken(null)
    setUser(null)
    setStatus('anonymous')
    queryClient.clear()
  }, [queryClient])

  // Restore the session from the refresh cookie on first load.
  useEffect(() => {
    let cancelled = false
    setSessionExpiredHandler(() => clear('expired'))
    refreshSession()
      .then(async (ok) => {
        if (!ok) throw new Error('no session')
        const me = await api.get<User>('/auth/me')
        if (!cancelled) {
          setUser(me)
          setStatus('authenticated')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('anonymous')
      })
    return () => {
      cancelled = true
      setSessionExpiredHandler(null)
    }
  }, [clear])

  const login = useCallback(async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password })
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      body: form,
      credentials: 'same-origin',
    })
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as {
        error?: { code: string; message: string }
      }
      throw new ApiError(
        response.status,
        body.error?.code ?? 'error',
        body.error?.message ?? 'Login failed',
      )
    }
    const tokens = (await response.json()) as TokenResponse
    setAccessToken(tokens.access_token)
    const me = await api.get<User>('/auth/me')
    setUser(me)
    setEndedBy(null)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      clear('logout')
    }
  }, [clear])

  const value = useMemo(() => ({ user, status, endedBy, login, logout }), [user, status, endedBy, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

/** The signed-in user. Only call below a route that requires authentication. */
export function useUser(): User {
  const { user } = useAuth()
  if (!user) throw new Error('useUser called without an authenticated user')
  return user
}
