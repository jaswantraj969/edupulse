import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from '@/components/AppShell'
import { mockApi, renderWithProviders, TEACHER } from '@/test/utils'

afterEach(() => {
  vi.unstubAllGlobals()
  document.documentElement.classList.remove('dark')
})

describe('AppShell', () => {
  it('shows staff navigation to admins only', async () => {
    mockApi({})
    const { unmount } = renderWithProviders(<AppShell />)
    const [sidebar] = await screen.findAllByRole('navigation', { name: 'Main' })
    expect(within(sidebar!).getByRole('link', { name: 'Staff' })).toBeInTheDocument()
    unmount()

    mockApi({}, TEACHER)
    renderWithProviders(<AppShell />)
    const [teacherNav] = await screen.findAllByRole('navigation', { name: 'Main' })
    expect(within(teacherNav!).queryByRole('link', { name: 'Staff' })).not.toBeInTheDocument()
    expect(within(teacherNav!).getByRole('link', { name: 'Grades' })).toBeInTheDocument()
  })

  it('has a skip link and toggles dark mode', async () => {
    mockApi({})
    renderWithProviders(<AppShell />)
    expect(await screen.findByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main')
    const [toggle] = screen.getAllByRole('button', { name: 'Switch to dark mode' })
    await userEvent.click(toggle!)
    expect(document.documentElement).toHaveClass('dark')
    expect(screen.getAllByRole('button', { name: 'Switch to light mode' }).length).toBeGreaterThan(0)
  })

  it('opens the mobile "More" menu as a dialog', async () => {
    mockApi({})
    renderWithProviders(<AppShell />)
    await userEvent.click(await screen.findByRole('button', { name: 'More' }))
    const dialog = screen.getByRole('dialog', { name: 'More' })
    expect(within(dialog).getByRole('link', { name: 'Classes' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('signs out', async () => {
    const { calls } = mockApi({ 'POST /api/v1/auth/logout': { __status: 204 } })
    renderWithProviders(<AppShell />)
    const [signOut] = await screen.findAllByRole('button', { name: 'Sign out' })
    await userEvent.click(signOut!)
    expect(await screen.findByText('signed out')).toBeInTheDocument()
    expect(calls.some((c) => c.path === '/api/v1/auth/logout')).toBe(true)
  })
})
