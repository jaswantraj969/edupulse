import { expect, test, type APIRequestContext } from '@playwright/test'
import { ADMIN_EMAIL, demoPassword, login, navigate, signOut } from './helpers'

const PASSWORD = 'Applicant-Pass-42'

/** Admin-side setup through the API: a teacher profile without an account, and one class for
 * which that teacher is the homeroom teacher. */
async function teacherWithClass(request: APIRequestContext, stamp: string) {
  const tokens = await request.post('/api/v1/auth/login', { form: { username: ADMIN_EMAIL, password: demoPassword() } })
  expect(tokens.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await tokens.json()).access_token}` }
  const teacher = await request.post('/api/v1/teachers', {
    headers,
    data: {
      employee_no: `E2E-${stamp}`,
      first_name: 'Nora',
      last_name: `Signup${stamp}`,
      email: `nora.${stamp}@edupulse.example`,
      hire_date: '2026-09-01',
    },
  })
  expect(teacher.ok(), await teacher.text()).toBeTruthy()
  const teacherId = (await teacher.json()).id as number
  const [year] = (await (await request.get('/api/v1/academic-years', { headers })).json()) as { id: number }[]
  const created = await request.post('/api/v1/classes', {
    headers,
    data: { academic_year_id: year!.id, grade_level: 13, section: `S${stamp.slice(-4)}`, homeroom_teacher_id: teacherId },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const klass = (await created.json()) as { id: number; name: string }
  return { teacherId, fullName: `Nora Signup${stamp}`, klass }
}

test('sign up → pending page → admin approves as teacher → teacher sees only their classes', async ({ page, request }, testInfo) => {
  test.setTimeout(120_000)
  const stamp = `${Date.now() % 1_000_000}${testInfo.project.name.startsWith('mobile') ? '1' : '2'}`
  const email = `applicant.${stamp}@example.org`
  const name = `Ada Applicant ${stamp}`
  const { teacherId, fullName, klass } = await teacherWithClass(request, stamp)

  await test.step('a visitor requests an account', async () => {
    await page.goto('/login')
    await page.getByRole('link', { name: 'Create account' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Request an account' })).toBeVisible()
    await page.getByLabel('Full name').fill(name)
    await page.getByLabel('E-mail').fill(email)
    await page.getByLabel(/^Password/).fill(PASSWORD)
    await page.getByLabel('Repeat password').fill(PASSWORD)
    await page.getByLabel(/Note for the administrator/).fill(`I teach in ${klass.name}`)
    await page.getByRole('button', { name: 'Send request' }).click()
    await expect(page.getByText('Your request was sent; an administrator must approve it.')).toBeVisible()
  })

  await test.step('the new account can sign in but only sees the waiting page', async () => {
    await page.getByRole('link', { name: 'Back to sign in' }).click()
    await page.getByLabel('E-mail').fill(email)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Waiting for approval' })).toBeVisible()
    await page.goto('/students')
    await expect(page.getByRole('heading', { level: 1, name: 'Waiting for approval' })).toBeVisible()
    await expect(page.getByRole('navigation')).toHaveCount(0)
    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in to your school account' })).toBeVisible()
  })

  await test.step('an administrator approves the request as a teacher', async () => {
    await login(page)
    await navigate(page, 'Account requests')
    await page.getByRole('button', { name: `Approve ${name}` }).click()
    const dialog = page.getByRole('dialog', { name: `Approve ${name}` })
    await expect(dialog.getByLabel('Role')).toHaveValue('teacher')
    await dialog.getByLabel('Teacher profile').selectOption(String(teacherId))
    await expect(dialog.getByLabel('Teacher profile')).toContainText(fullName)
    await dialog.getByRole('button', { name: 'Approve' }).click()
    await expect(page.getByText(`${name} approved`)).toBeVisible()
    await expect(page.getByRole('button', { name: `Approve ${name}` })).toHaveCount(0)
    await signOut(page)
  })

  await test.step('the approved teacher sees only their own class', async () => {
    await page.getByLabel('E-mail').fill(email)
    await page.getByLabel('Password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: /^Welcome/ })).toBeVisible()
    await navigate(page, 'Classes')
    const classLinks = page.locator('a[href^="/classes/"]:visible')
    await expect(classLinks).toHaveCount(1)
    await expect(classLinks).toHaveAttribute('href', `/classes/${klass.id}`)
    await expect(page.getByRole('link', { name: 'Staff', exact: true })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Account requests', exact: true })).toHaveCount(0)
  })
})
