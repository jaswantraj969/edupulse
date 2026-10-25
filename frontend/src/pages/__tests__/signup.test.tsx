import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from '@/components/AppShell'
import AccountRequestsPage from '@/pages/accounts/AccountRequestsPage'
import PendingPage from '@/pages/auth/PendingPage'
import SignupPage from '@/pages/auth/SignupPage'
import LoginPage from '@/pages/LoginPage'
import { ADMIN, mockApi, renderWithProviders, TEACHER } from '@/test/utils'
import type { AccountRequest, Meta, User } from '@/lib/types'

afterEach(() => vi.unstubAllGlobals())

const DEMO: Meta = {
  demo_mode: true,
  public_demo: false,
  demo_reset_hours: 6,
  demo_accounts: [
    { role: 'admin', label: 'Administrator', email: 'admin@edupulse.example', password: 'Demo-Password-77' },
    { role: 'teacher', label: 'Teacher (Ana Lopes)', email: 'ana@edupulse.example', password: 'Demo-Password-77' },
  ],
}
const renderLogin = () => renderWithProviders(<LoginPage />, { route: '/login', path: '/login', requireAuth: false })

describe('LoginPage demo accounts', () => {
  it('lists demo accounts in demo mode and fills the form', async () => {
    mockApi({ 'GET /api/v1/meta': DEMO }, null)
    renderLogin()
    const box = await screen.findByRole('region', { name: 'Demo accounts' })
    expect(within(box).getByText('admin@edupulse.example')).toBeInTheDocument()
    expect(within(box).getAllByText('Demo-Password-77')).toHaveLength(2)
    await userEvent.click(within(box).getByRole('button', { name: 'Use this account: Teacher (Ana Lopes)' }))
    expect(screen.getByLabelText(/E-mail/)).toHaveValue('ana@edupulse.example')
    expect(screen.getByLabelText(/Password/)).toHaveValue('Demo-Password-77')
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute('href', '/signup')
  })

  it('never shows demo accounts when demo mode is off', async () => {
    // Even if a response carried accounts, nothing is shown unless demo_mode is true.
    const { calls } = mockApi({ 'GET /api/v1/meta': { ...DEMO, demo_mode: false } }, null)
    renderLogin()
    expect(await screen.findByRole('link', { name: 'Create account' })).toBeInTheDocument()
    await vi.waitFor(() => expect(calls.some((c) => c.path === '/api/v1/meta')).toBe(true))
    expect(screen.queryByRole('region', { name: 'Demo accounts' })).toBeNull()
    expect(screen.queryByText('Demo-Password-77')).toBeNull()
  })
})

describe('SignupPage', () => {
  const renderSignup = () => renderWithProviders(<SignupPage />, { route: '/signup', path: '/signup', requireAuth: false })

  it('validates inline and shows the password rules', async () => {
    const { calls } = mockApi({}, null)
    renderSignup()
    await userEvent.click(await screen.findByRole('button', { name: 'Send request' }))
    expect(await screen.findByText('Enter your full name')).toBeInTheDocument()
    expect(screen.getByText('Enter your e-mail address')).toBeInTheDocument()
    expect(screen.getByText(/The password needs:/)).toBeInTheDocument()
    expect(calls.some((c) => c.path.includes('/auth/signup'))).toBe(false)

    const rules = screen.getByRole('list', { name: 'The password must have:' })
    expect(within(rules).getAllByText(/not met yet/)).toHaveLength(4)
    await userEvent.type(screen.getByLabelText(/^Password/), 'Abcdefghijk1')
    expect(within(rules).queryAllByText(/not met yet/)).toHaveLength(0)
    await userEvent.type(screen.getByLabelText(/Repeat password/), 'Different-1234')
    await userEvent.tab()
    expect(await screen.findByText('The passwords do not match')).toBeInTheDocument()
  })

  it('sends the request and shows the confirmation', async () => {
    const { calls } = mockApi({ 'POST /api/v1/auth/signup': { __status: 202, message: 'ok' } }, null)
    renderSignup()
    await userEvent.type(await screen.findByLabelText(/Full name/), 'Nora New')
    await userEvent.type(screen.getByLabelText(/E-mail/), 'nora@example.org')
    await userEvent.type(screen.getByLabelText(/^Password/), 'Applicant-Pass-42')
    await userEvent.type(screen.getByLabelText(/Repeat password/), 'Applicant-Pass-42')
    await userEvent.type(screen.getByLabelText(/Note for the administrator/), 'I teach biology in 10-A')
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    expect(await screen.findByText('Your request was sent; an administrator must approve it.')).toBeInTheDocument()
    const sent = calls.find((c) => c.path === '/api/v1/auth/signup')
    expect(sent?.body).toEqual({ full_name: 'Nora New', email: 'nora@example.org', password: 'Applicant-Pass-42', note: 'I teach biology in 10-A' })
  })

  it('explains the rate limit', async () => {
    mockApi({ 'POST /api/v1/auth/signup': { __status: 429, error: { code: 'rate_limited', message: 'Too many requests. Try again later.' } } }, null)
    renderSignup()
    await userEvent.type(await screen.findByLabelText(/Full name/), 'Nora New')
    await userEvent.type(screen.getByLabelText(/E-mail/), 'nora@example.org')
    await userEvent.type(screen.getByLabelText(/^Password/), 'Applicant-Pass-42')
    await userEvent.type(screen.getByLabelText(/Repeat password/), 'Applicant-Pass-42')
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests from this device')
  })
})

describe('PendingPage', () => {
  const PENDING: User = { ...ADMIN, id: 9, email: 'nora@example.org', full_name: 'Nora New', role: null, status: 'pending' }

  it('shows only the waiting message and a sign-out button', async () => {
    const { calls } = mockApi({ 'POST /api/v1/auth/logout': { __status: 204 } }, PENDING)
    renderWithProviders(<PendingPage />)
    expect(await screen.findByRole('heading', { name: 'Waiting for approval' })).toBeInTheDocument()
    expect(screen.getByText('nora@example.org')).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).toBeNull()
    expect(screen.getAllByRole('button')).toHaveLength(1)
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    await vi.waitFor(() => expect(calls.some((c) => c.path === '/api/v1/auth/logout')).toBe(true))
  })
})

describe('AccountRequestsPage', () => {
  const request: AccountRequest = {
    id: 21,
    email: 'nora@example.org',
    full_name: 'Nora New',
    status: 'pending',
    signup_note: 'I teach biology in 10-A',
    created_at: '2026-10-26T09:00:00Z',
  }
  const routes = {
    'GET /api/v1/account-requests': { items: [request], total: 1 },
    'GET /api/v1/account-requests/count': { pending: 1 },
    'GET /api/v1/account-requests/unlinked-teachers': [{ id: 7, employee_no: 'T0007', full_name: 'Nora New', email: 'nora.new@edupulse.example' }],
    'POST /api/v1/account-requests/21/approve': { ...request, status: 'active' },
    'POST /api/v1/account-requests/21/reject': { ...request, status: 'rejected' },
  }

  it('approves as a teacher linked to a profile', async () => {
    const { calls } = mockApi(routes)
    renderWithProviders(<AccountRequestsPage />)
    expect((await screen.findAllByText('I teach biology in 10-A')).length).toBeGreaterThan(0)
    await userEvent.click(screen.getAllByRole('button', { name: 'Approve Nora New' })[0]!)
    const dialog = screen.getByRole('dialog', { name: 'Approve Nora New' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Approve' }))
    expect(await within(dialog).findByText('Choose the teacher profile for this account')).toBeInTheDocument()
    expect(calls.some((c) => c.path.endsWith('/approve'))).toBe(false)
    await userEvent.selectOptions(await within(dialog).findByLabelText(/Teacher profile/), '7')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Approve' }))
    await vi.waitFor(() => expect(calls.find((c) => c.path.endsWith('/approve'))?.body).toEqual({ role: 'teacher', teacher_id: 7 }))
    expect(await screen.findByText('Nora New approved')).toBeInTheDocument()
  })

  it('approves an administrator without a teacher profile', async () => {
    const { calls } = mockApi(routes)
    renderWithProviders(<AccountRequestsPage />)
    await userEvent.click((await screen.findAllByRole('button', { name: 'Approve Nora New' }))[0]!)
    const dialog = screen.getByRole('dialog', { name: 'Approve Nora New' })
    await userEvent.selectOptions(within(dialog).getByLabelText(/Role/), 'admin')
    expect(within(dialog).queryByLabelText(/Teacher profile/)).toBeNull()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Approve' }))
    await vi.waitFor(() => expect(calls.find((c) => c.path.endsWith('/approve'))?.body).toEqual({ role: 'admin', teacher_id: null }))
  })

  it('rejects with a reason', async () => {
    const { calls } = mockApi(routes)
    renderWithProviders(<AccountRequestsPage />)
    await userEvent.click((await screen.findAllByRole('button', { name: 'Reject Nora New' }))[0]!)
    const dialog = screen.getByRole('dialog', { name: 'Reject Nora New' })
    await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Not on our staff list')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Reject request' }))
    await vi.waitFor(() => expect(calls.find((c) => c.path.endsWith('/reject'))?.body).toEqual({ reason: 'Not on our staff list' }))
    expect(await screen.findByText('Request from Nora New rejected')).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    mockApi({ ...routes, 'GET /api/v1/account-requests': { items: [], total: 0 } })
    renderWithProviders(<AccountRequestsPage />)
    expect(await screen.findByText('No pending requests')).toBeInTheDocument()
  })
})

describe('AppShell account-request badge', () => {
  it('shows the pending count to administrators only', async () => {
    mockApi({ 'GET /api/v1/account-requests/count': { pending: 3 } })
    const { unmount } = renderWithProviders(<AppShell />)
    const [sidebar] = await screen.findAllByRole('navigation', { name: 'Main' })
    const link = within(sidebar!).getByRole('link', { name: 'Account requests' })
    await vi.waitFor(() => expect(link).toHaveAccessibleDescription('3 pending'))
    unmount()

    const { calls } = mockApi({}, TEACHER)
    renderWithProviders(<AppShell />)
    const [teacherNav] = await screen.findAllByRole('navigation', { name: 'Main' })
    expect(within(teacherNav!).queryByRole('link', { name: 'Account requests' })).toBeNull()
    expect(calls.some((c) => c.path.includes('/account-requests'))).toBe(false)
  })
})
