import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AccountRequestsPage from '@/pages/accounts/AccountRequestsPage'
import { PublicDemoBanner } from '@/lib/meta'
import { mockApi, renderWithProviders } from '@/test/utils'
import type { Meta } from '@/lib/types'

afterEach(() => vi.unstubAllGlobals())

const meta = (public_demo: boolean): Meta => ({ demo_mode: true, public_demo, demo_reset_hours: 6, demo_accounts: [] })
const request = { id: 21, email: 'ada@example.org', full_name: 'Ada Applicant', status: 'pending', signup_note: null, created_at: '2026-10-26T09:00:00Z' }

describe('public demo', () => {
  it('shows the banner only in public-demo mode', async () => {
    mockApi({ 'GET /api/v1/meta': meta(true) }, null)
    const { unmount } = renderWithProviders(<PublicDemoBanner />, { requireAuth: false })
    expect(await screen.findByRole('region', { name: 'Public demo notice' })).toHaveTextContent(
      'Public demo — synthetic data, reset every 6 hours',
    )
    unmount()

    const { calls } = mockApi({ 'GET /api/v1/meta': meta(false) }, null)
    renderWithProviders(<PublicDemoBanner />, { requireAuth: false })
    await vi.waitFor(() => expect(calls.some((c) => c.path === '/api/v1/meta')).toBe(true))
    expect(screen.queryByRole('region', { name: 'Public demo notice' })).toBeNull()
  })

  it('disables locked actions with a tooltip and description', async () => {
    mockApi({ 'GET /api/v1/meta': meta(true), 'GET /api/v1/account-requests': { items: [request], total: 1 } })
    renderWithProviders(
      <>
        <PublicDemoBanner />
        <AccountRequestsPage />
      </>,
    )
    await screen.findByRole('region', { name: 'Public demo notice' })
    for (const name of ['Approve Ada Applicant', 'Reject Ada Applicant']) {
      const [button] = await screen.findAllByRole('button', { name })
      await vi.waitFor(() => expect(button).toBeDisabled())
      expect(button).toHaveAttribute('title', 'Disabled in the public demo')
      expect(button).toHaveAccessibleDescription(/Disabled in the public demo/)
    }
  })

  it('leaves actions enabled when public demo is off', async () => {
    mockApi({ 'GET /api/v1/meta': meta(false), 'GET /api/v1/account-requests': { items: [request], total: 1 } })
    renderWithProviders(<AccountRequestsPage />)
    const [button] = await screen.findAllByRole('button', { name: 'Approve Ada Applicant' })
    expect(button).toBeEnabled()
    expect(button).not.toHaveAttribute('title')
  })
})
