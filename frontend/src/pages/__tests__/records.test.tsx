import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AttendancePage from '@/pages/records/AttendancePage'
import GradesPage from '@/pages/records/GradesPage'
import { mockApi, renderWithProviders, TEACHER } from '@/test/utils'
import type { AttendanceSheet, GradeSheet } from '@/lib/types'

afterEach(() => vi.unstubAllGlobals())

const classes = { items: [{ id: 3, name: '10-C' }], total: 1, page: 1, page_size: 100 }
const years = [{ id: 1, name: '2025-2026', start_date: '2025-09-08', end_date: '2026-06-19', terms: [{ id: 1, number: 1, name: 'Term 1', start_date: '2025-09-08', end_date: '2025-12-19' }] }]
const sheet: AttendanceSheet = {
  class_id: 3,
  class_name: '10-C',
  date: '2025-10-06',
  records: [
    { student_id: 11, student_no: 'S11', first_name: 'Ana', last_name: 'Lopes', status: 'present', note: null },
    { student_id: 12, student_no: 'S12', first_name: 'Rui', last_name: 'Mota', status: null, note: null },
  ],
}

describe('AttendancePage', () => {
  it('asks for a class first', async () => {
    mockApi({ 'GET /api/v1/classes': classes, 'GET /api/v1/academic-years': years })
    renderWithProviders(<AttendancePage />, { route: '/attendance' })
    expect(await screen.findByText('Choose a class')).toBeInTheDocument()
  })

  it('marks students and saves only the changes', async () => {
    const { calls } = mockApi({
      'GET /api/v1/classes': classes,
      'GET /api/v1/academic-years': years,
      'GET /api/v1/classes/3/attendance': sheet,
      'PUT /api/v1/classes/3/attendance': (init: RequestInit | undefined) => {
        const body = JSON.parse(String(init?.body)) as { records: { student_id: number; status: string }[] }
        return {
          body: { ...sheet, records: sheet.records.map((r) => ({ ...r, status: body.records.find((x) => x.student_id === r.student_id)?.status ?? r.status })) },
        }
      },
    })
    renderWithProviders(<AttendancePage />, { route: '/attendance?class_id=3&date=2025-10-06' })
    const list = await screen.findByRole('list', { name: 'Attendance for 10-C' })
    expect(screen.getByText(/1 not marked/)).toBeInTheDocument()
    const save = screen.getByRole('button', { name: 'Save attendance' })
    expect(save).toBeDisabled()

    const rui = within(list).getByRole('group', { name: 'Attendance for Rui Mota' })
    await userEvent.click(within(rui).getByRole('radio', { name: 'Absent' }))
    expect(within(rui).getByRole('radio', { name: 'Absent' })).toBeChecked()
    await userEvent.click(save)
    expect(await screen.findByText('Attendance saved for 10-C')).toBeInTheDocument()
    const put = calls.find((c) => c.method === 'PUT')!
    expect(put.body).toEqual({ date: '2025-10-06', records: [{ student_id: 12, status: 'absent' }] })
  })

  it('marks every unmarked student present', async () => {
    mockApi({ 'GET /api/v1/classes': classes, 'GET /api/v1/academic-years': years, 'GET /api/v1/classes/3/attendance': sheet })
    renderWithProviders(<AttendancePage />, { route: '/attendance?class_id=3&date=2025-10-06' })
    await userEvent.click(await screen.findByRole('button', { name: 'Mark unmarked present' }))
    expect(screen.getByText(/0 not marked · 1 unsaved/)).toBeInTheDocument()
  })
})

const gradeSheet: GradeSheet = {
  assessment: {
    id: 9,
    assignment_id: 4,
    class_id: 3,
    subject_id: 1,
    subject_name: 'Mathematics',
    teacher_id: 7,
    term_id: 1,
    term_name: 'Term 1',
    title: 'Term 1 Quiz',
    kind: 'quiz',
    max_score: 20,
    weight: 1,
    assessed_on: '2025-10-01',
    graded_count: 0,
  },
  grades: [{ student_id: 11, student_no: 'S11', first_name: 'Ana', last_name: 'Lopes', score: null, comment: null }],
}
const gradeRoutes = {
  'GET /api/v1/classes': classes,
  'GET /api/v1/academic-years': years,
  'GET /api/v1/classes/3/assessments': [gradeSheet.assessment],
  'GET /api/v1/classes/3/assignments': [{ id: 4, class_id: 3, class_name: '10-C', subject_id: 1, subject_code: 'MAT', subject_name: 'Mathematics', teacher_id: 7, teacher_name: 'Tea Cher' }],
  'GET /api/v1/assessments/9/grades': gradeSheet,
}

describe('GradesPage', () => {
  it('validates scores against the maximum before saving', async () => {
    const { calls } = mockApi({
      ...gradeRoutes,
      'PUT /api/v1/assessments/9/grades': { ...gradeSheet, grades: [{ ...gradeSheet.grades[0]!, score: 15 }] },
    })
    renderWithProviders(<GradesPage />, { route: '/grades?class_id=3&assessment_id=9' })
    const input = await screen.findByLabelText(/Ana Lopes/)
    const save = screen.getByRole('button', { name: 'Save grades' })
    await userEvent.type(input, '25')
    expect(screen.getByText('Maximum is 20')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(save).toBeDisabled()

    await userEvent.clear(input)
    await userEvent.type(input, '15')
    await userEvent.click(save)
    expect(await screen.findByText('Grades saved')).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'PUT')!.body).toEqual({ grades: [{ student_id: 11, score: 15 }] })
  })

  it('is read-only for a teacher who does not teach the subject', async () => {
    mockApi(gradeRoutes, { ...TEACHER, teacher_id: 99 })
    renderWithProviders(<GradesPage />, { route: '/grades?class_id=3&assessment_id=9' })
    expect(await screen.findByLabelText(/Ana Lopes/)).toBeDisabled()
    expect(screen.getByText(/Read only/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'New assessment' })).not.toBeInTheDocument()
  })

  it('lets the subject teacher create assessments', async () => {
    mockApi(gradeRoutes, TEACHER)
    renderWithProviders(<GradesPage />, { route: '/grades?class_id=3' })
    await userEvent.click(await screen.findByRole('button', { name: 'New assessment' }))
    const dialog = screen.getByRole('dialog', { name: 'New assessment' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Create assessment' }))
    expect(await within(dialog).findByText('Title is required')).toBeInTheDocument()
    expect(within(dialog).getByText('Choose a term')).toBeInTheDocument()
  })
})
