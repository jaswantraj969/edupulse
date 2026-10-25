import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import LoginPage from '@/pages/LoginPage'
import { ADMIN, mockApi, renderWithProviders } from '@/test/utils'

afterEach(() => vi.unstubAllGlobals())

const renderLogin = () => renderWithProviders(<LoginPage />, { route: '/login', path: '/login', requireAuth: false })

async function submit(email: string, password: string) {
  await userEvent.type(await screen.findByLabelText(/E-mail/), email)
  await userEvent.type(screen.getByLabelText(/Password/), password)
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('LoginPage', () => {
  it('validates inline before calling the API', async () => {
    const { calls } = mockApi({}, null)
    renderLogin()
    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter your e-mail address')).toBeInTheDocument()
    expect(screen.getByText('Enter your password')).toBeInTheDocument()
    expect(screen.getByLabelText(/E-mail/)).toHaveAttribute('aria-invalid', 'true')
    await userEvent.type(screen.getByLabelText(/E-mail/), 'not-an-email')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter a valid e-mail address')).toBeInTheDocument()
    expect(calls.some((c) => c.path.includes('/auth/login'))).toBe(false)
  })

  it('shows the server error for bad credentials', async () => {
    mockApi(
      {
        'POST /api/v1/auth/login': {
          __status: 401,
          error: { code: 'invalid_credentials', message: 'Incorrect e-mail or password' },
        },
      },
      null,
    )
    renderLogin()
    await submit('admin@edupulse.example', 'wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect e-mail or password')
  })

  it('explains rate limiting', async () => {
    mockApi({ 'POST /api/v1/auth/login': { __status: 429, error: { code: 'rate_limited', message: 'Too many' } } }, null)
    renderLogin()
    await submit('admin@edupulse.example', 'x')
    expect(await screen.findByRole('alert')).toHaveTextContent('wait a minute')
  })

  it('signs in and leaves the login page', async () => {
    let loggedIn = false
    mockApi(
      {
        'POST /api/v1/auth/login': () => {
          loggedIn = true
          return { body: { access_token: 't', token_type: 'bearer', expires_in: 900, refresh_token: 'r' } }
        },
        'GET /api/v1/auth/me': () => (loggedIn ? { body: ADMIN } : { status: 401, body: null }),
      },
      null,
    )
    renderLogin()
    await submit('admin@edupulse.example', 'Correct-Horse-9')
    expect(await screen.findByText('other route')).toBeInTheDocument()
  })
})
