import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AuditLogPage from '@/pages/risk/AuditLogPage'
import RiskListPage from '@/pages/risk/RiskListPage'
import StudentRiskPage from '@/pages/risk/StudentRiskPage'
import { mockApi, renderWithProviders, TEACHER } from '@/test/utils'
import type { ClassRisk, RiskModelInfo, StudentRisk } from '@/lib/types'

// Recharts is heavy to load in jsdom and is not what these tests check.
vi.mock('@/pages/risk/RiskTrendCharts', () => ({
  default: ({ title }: { title: string }) => <p>chart: {title}</p>,
}))

afterEach(() => vi.unstubAllGlobals())

const model: RiskModelInfo = {
  version: '1.0.0',
  model_type: 'logistic_regression',
  trained_at: '2026-10-25',
  prediction_moment: 'End of Term 1',
  thresholds: { high: 0.315, medium: 0.134 },
  evaluation: { average_precision: { estimate: 0.817, ci_low: 0.705, ci_high: 0.901 } },
  training_data: 'Trained on UCI data; must be re-validated.',
  disclaimer: 'Decision support only. Review with the student\'s context before acting; never use this score as an automatic sanction.',
  data_notice: 'Demo — synthetic data. Scores are illustrative and refer to no real student.',
}
const inputs = { g1: 7.2, failures: 1, assessments_term1: 4 }
const classRisk: ClassRisk = {
  class_id: 3,
  class_name: '10-C',
  as_of: '2025-12-19',
  model,
  students: [
    { student_id: 11, student_no: 'S11', first_name: 'Ana', last_name: 'Lopes', status: 'scored', probability: 0.72, band: 'high', top_factor: 'Term 1 average of 7.2/20 is below the typical 11/20; this raises the estimate.', inputs },
    { student_id: 12, student_no: 'S12', first_name: 'Rui', last_name: 'Mota', status: 'scored', probability: 0.05, band: 'low', top_factor: 'Term 1 average is above typical.', inputs: { ...inputs, g1: 15 } },
    { student_id: 13, student_no: 'S13', first_name: 'Eva', last_name: 'Neves', status: 'insufficient_data', probability: null, band: null, top_factor: null, inputs: { ...inputs, g1: null } },
  ],
}
const routes = {
  'GET /api/v1/classes': { items: [{ id: 3, name: '10-C' }], total: 1, page: 1, page_size: 100 },
  'GET /api/v1/risk/classes/3': classRisk,
  'GET /api/v1/risk/classes/3/export': 'student_no\nS11\n',
}

describe('RiskListPage', () => {
  it('shows the disclaimer, demo label and band text for each student', async () => {
    mockApi(routes, TEACHER)
    renderWithProviders(<RiskListPage />, { route: '/early-warning?class_id=3' })
    const note = await screen.findByRole('note')
    expect(note).toHaveTextContent("Decision support; review with the student's context.")
    expect(note).toHaveTextContent('Demo — synthetic data')
    const table = screen.getByRole('table')
    expect(within(table).getByText('High risk')).toBeInTheDocument()
    expect(within(table).getByText('Low risk')).toBeInTheDocument()
    expect(within(table).getByText('Not scored')).toBeInTheDocument()
    expect(within(table).getByText('No Term 1 grades yet')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Lopes, Ana' })).toHaveAttribute('href', '/early-warning/students/11')
    expect(screen.getByText(/1 high · 0 medium · 1 low · 1 not scored/)).toBeInTheDocument()
  })

  it('sorts through the API and exports', async () => {
    const { calls } = mockApi(routes)
    renderWithProviders(<RiskListPage />, { route: '/early-warning?class_id=3' })
    const table = await screen.findByRole('table')
    const nameHeader = within(table).getByRole('columnheader', { name: /student/i })
    await userEvent.click(within(nameHeader).getByRole('button'))
    await vi.waitFor(() => expect(calls.some((c) => c.path.includes('sort=name'))).toBe(true))
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() }))
    await userEvent.click(screen.getByRole('button', { name: 'Export CSV' }))
    expect(await screen.findByText('Export recorded in the audit log')).toBeInTheDocument()
    expect(calls.some((c) => c.path === '/api/v1/risk/classes/3/export')).toBe(true)
  })

  it('asks for a class first and surfaces errors', async () => {
    mockApi({ ...routes, 'GET /api/v1/risk/classes/3': { __status: 403, error: { code: 'forbidden', message: 'You do not teach this class' } } })
    const { unmount } = renderWithProviders(<RiskListPage />, { route: '/early-warning' })
    expect(await screen.findByText('Choose a class')).toBeInTheDocument()
    unmount()
    renderWithProviders(<RiskListPage />, { route: '/early-warning?class_id=3' })
    expect(await screen.findByText('You do not teach this class')).toBeInTheDocument()
  })
})

const studentRisk: StudentRisk = {
  student_id: 11,
  student_no: 'S11',
  first_name: 'Ana',
  last_name: 'Lopes',
  class_id: 3,
  class_name: '10-C',
  as_of: '2025-12-19',
  status: 'scored',
  probability: 0.72,
  band: 'high',
  inputs,
  model,
  factors: [
    { feature: 'g1', label: 'Term 1 average', value: 7.2, contribution: 2.1, direction: 'raises', text: 'Term 1 average of 7.2/20 is below the typical 11/20; this raises the estimate.' },
    { feature: 'failures', label: 'Previous failures', value: 0, contribution: -0.1, direction: 'lowers', text: 'No previous school-year failures; this lowers the estimate.' },
  ],
}
const studentRoutes = {
  'GET /api/v1/risk/students/11': studentRisk,
  'GET /api/v1/students/11/attendance': { student_id: 11, present: 2, absent: 1, late: 0, excused: 0, total: 3, attendance_rate: 0.67, by_month: [{ month: '2025-09', present: 2, absent: 1, late: 0, excused: 0 }] },
  'GET /api/v1/students/11/grades': [{ assessment_id: 1, title: 'Quiz', kind: 'quiz', subject_name: 'Maths', term_number: 1, assessed_on: '2025-10-01', score: 7, max_score: 20, percentage: 35 }],
}

describe('StudentRiskPage', () => {
  it('explains the estimate in plain language with a disclaimer', async () => {
    mockApi(studentRoutes)
    renderWithProviders(<StudentRiskPage />, { route: '/early-warning/students/11', path: '/early-warning/students/:id' })
    expect(await screen.findByRole('heading', { level: 1, name: 'Ana Lopes' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent("review with the student's context")
    expect(screen.getByText('High risk')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
    const factors = screen.getByRole('region', { name: 'What drives this estimate' })
    const items = within(factors).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('↑ Raises')
    expect(items[0]).toHaveTextContent('Term 1 average of 7.2/20')
    expect(items[1]).toHaveTextContent('↓ Lowers')
    expect(screen.getByRole('link', { name: 'Early warning' })).toHaveAttribute('href', '/early-warning?class_id=3')
    expect(await screen.findByText('chart: Attendance rate by month')).toBeInTheDocument()
    expect(await screen.findByText('chart: Average grade by month')).toBeInTheDocument()
  })

  it('shows when there is not enough data', async () => {
    mockApi({ ...studentRoutes, 'GET /api/v1/risk/students/11': { ...studentRisk, status: 'insufficient_data', probability: null, band: null, factors: [], inputs: null } })
    renderWithProviders(<StudentRiskPage />, { route: '/early-warning/students/11', path: '/early-warning/students/:id' })
    expect(await screen.findByText('Not enough data')).toBeInTheDocument()
    expect(screen.getByText('No factors available.')).toBeInTheDocument()
  })
})

describe('AuditLogPage', () => {
  it('lists entries newest first with readable actions', async () => {
    const { calls } = mockApi({
      'GET /api/v1/audit-logs': {
        items: [{ id: 2, created_at: '2026-10-25T10:00:00Z', user_id: 2, user_email: 't@edupulse.example', action: 'risk.export_class', target_type: 'class', target_id: 3, detail: '10-C', ip_address: '127.0.0.1' }],
        total: 1,
        page: 1,
        page_size: 25,
      },
    })
    renderWithProviders(<AuditLogPage />, { route: '/audit' })
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Exported class risk list')).toBeInTheDocument()
    expect(within(table).getByText('class 10-C')).toBeInTheDocument()
    expect(calls.find((c) => c.path.startsWith('/api/v1/audit-logs'))!.path).toContain('order=desc')
  })
})
