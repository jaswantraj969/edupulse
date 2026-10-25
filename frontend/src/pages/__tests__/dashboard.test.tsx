import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import { mockApi, renderWithProviders } from '@/test/utils'
import type { DashboardSummary } from '@/lib/types'

vi.mock('@/pages/dashboard/DashboardCharts', () => ({
  AttendanceTrendChart: () => <p>attendance chart</p>,
  GradeDistributionChart: () => <p>grade chart</p>,
}))

const summary: DashboardSummary = {
  scope: 'school',
  counts: { students: 400, teachers: 30, staff: 15, classes: 15 },
  attendance_trend: [{ week_start: '2025-09-08', attendance_rate: 0.95, records: 100 }],
  grade_distribution: [{ label: '60-70', students: 10 }],
  demo_mode: true,
}

describe('DashboardPage', () => {
  it('labels synthetic demo data', async () => {
    mockApi({ 'GET /api/v1/dashboard': summary })
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByRole('note')).toHaveTextContent('Demo — synthetic data')
    expect(screen.getByText('400')).toBeInTheDocument()
  })

  it('shows no demo label for real data', async () => {
    mockApi({ 'GET /api/v1/dashboard': { ...summary, demo_mode: false } })
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('400')).toBeInTheDocument()
    expect(screen.queryByRole('note')).toBeNull()
  })
})
