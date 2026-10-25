import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StudentCreatePage } from '@/pages/students/StudentForm'
import StudentsListPage from '@/pages/students/StudentsListPage'
import { mockApi, renderWithProviders, TEACHER } from '@/test/utils'
import type { Page, Student } from '@/lib/types'

afterEach(() => vi.unstubAllGlobals())

const student: Student = {
  id: 5,
  student_no: 'ST250005',
  first_name: 'Ana',
  last_name: 'Lopes',
  date_of_birth: '2009-02-03',
  email: null,
  phone: null,
  guardian_name: null,
  guardian_phone: null,
  enrolled_on: '2023-09-01',
  status: 'active',
  prior_failures: 0,
  class_id: 1,
  class_name: '10-A',
  created_at: '',
  updated_at: '',
}
const page = (items: Student[]): Page<Student> => ({ items, total: items.length, page: 1, page_size: 20 })
const classes = { items: [{ id: 1, name: '10-A' }], total: 1, page: 1, page_size: 100 }

describe('StudentsListPage', () => {
  it('lists students with admin actions', async () => {
    mockApi({ 'GET /api/v1/students': page([student]), 'GET /api/v1/classes': classes })
    renderWithProviders(<StudentsListPage />)
    const table = await screen.findByRole('table')
    expect(within(table).getByRole('link', { name: 'Lopes, Ana' })).toHaveAttribute('href', '/students/5')
    expect(screen.getByRole('link', { name: 'Add student' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import CSV' })).toBeInTheDocument()
  })

  it('hides write actions from teachers', async () => {
    mockApi({ 'GET /api/v1/students': page([student]), 'GET /api/v1/classes': classes }, TEACHER)
    renderWithProviders(<StudentsListPage />)
    await screen.findByRole('table')
    expect(screen.queryByRole('link', { name: 'Add student' })).not.toBeInTheDocument()
    expect(screen.getByText('Students in your classes.')).toBeInTheDocument()
  })

  it('shows empty and error states', async () => {
    mockApi({ 'GET /api/v1/students': page([]), 'GET /api/v1/classes': classes })
    const { unmount } = renderWithProviders(<StudentsListPage />)
    expect(await screen.findByText('No students found')).toBeInTheDocument()
    unmount()

    mockApi({ 'GET /api/v1/students': { __status: 500, error: { code: 'error', message: 'Database unavailable' } }, 'GET /api/v1/classes': classes })
    renderWithProviders(<StudentsListPage />)
    expect(await screen.findByText('Database unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('passes search text to the API', async () => {
    const { calls } = mockApi({ 'GET /api/v1/students': page([student]), 'GET /api/v1/classes': classes })
    renderWithProviders(<StudentsListPage />)
    await userEvent.type(await screen.findByLabelText('Search'), 'lopes')
    await vi.waitFor(() => expect(calls.some((c) => c.path.startsWith('/api/v1/students?') && c.path.includes('q=lopes'))).toBe(true))
  })
})

describe('StudentCreatePage', () => {
  it('validates inline and maps a 409 onto the student number field', async () => {
    const { calls } = mockApi({
      'GET /api/v1/classes': classes,
      'POST /api/v1/students': {
        __status: 409,
        error: { code: 'conflict', message: "Student number 'ST-1' is already in use", details: { field: 'student_no' } },
      },
    })
    renderWithProviders(<StudentCreatePage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Create student' }))
    expect(await screen.findByText('First name is required')).toBeInTheDocument()
    expect(screen.getByText('Date of birth is required')).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/students')).toBe(false)

    await userEvent.type(screen.getByLabelText(/Student number/), 'ST-1')
    await userEvent.type(screen.getByLabelText(/First name/), 'Rui')
    await userEvent.type(screen.getByLabelText(/Last name/), 'Mota')
    await userEvent.type(screen.getByLabelText(/Date of birth/), '2009-05-06')
    await userEvent.selectOptions(screen.getByLabelText('Class'), '1')
    await userEvent.click(screen.getByRole('button', { name: 'Create student' }))

    const field = await screen.findByLabelText(/Student number/)
    await vi.waitFor(() => expect(field).toHaveAttribute('aria-invalid', 'true'))
    expect(screen.getByRole('alert')).toHaveTextContent('already in use')
    const post = calls.find((c) => c.method === 'POST' && c.path === '/api/v1/students')!
    expect(post.body).toMatchObject({ student_no: 'ST-1', first_name: 'Rui', class_id: 1, email: null, prior_failures: 0 })
  })

  it('rejects an enrolment date before the birth date', async () => {
    mockApi({ 'GET /api/v1/classes': classes })
    renderWithProviders(<StudentCreatePage />)
    await userEvent.type(await screen.findByLabelText(/Date of birth/), '2009-05-06')
    const enrolled = screen.getByLabelText(/Enrolled on/)
    await userEvent.clear(enrolled)
    await userEvent.type(enrolled, '2001-01-01')
    await userEvent.click(screen.getByRole('button', { name: 'Create student' }))
    expect(await screen.findByText('Enrolment cannot be before the date of birth')).toBeInTheDocument()
  })
})
