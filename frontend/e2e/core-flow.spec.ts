import { expect, test } from '@playwright/test'
import { login, navigate } from './helpers'

// A school day inside the seeded (synthetic) 2025-2026 academic year.
const SCHOOL_DAY = '2025-10-07'
const CLASS_NAME = '10-A'

test('login → add student → mark attendance → enter grade', async ({ page }, testInfo) => {
  const stamp = `${testInfo.project.name.replace(/\W/g, '')}${Date.now().toString(36)}`.slice(-14)
  const firstName = 'Eva'
  const lastName = `E2e${stamp}`
  const fullName = `${firstName} ${lastName}`

  await test.step('log in as the demo administrator', async () => {
    await login(page)
  })

  await test.step('add a student to class 10-A', async () => {
    await navigate(page, 'Students')
    await page.getByRole('link', { name: 'Add student' }).click()
    await expect(page.getByRole('heading', { name: 'Add student' })).toBeVisible()

    // Inline validation fires before anything is sent.
    await page.getByRole('button', { name: 'Create student' }).click()
    await expect(page.getByText('First name is required')).toBeVisible()

    await page.getByLabel('Student number').fill(`E2E-${stamp}`)
    await page.getByLabel('First name').fill(firstName)
    await page.getByLabel('Last name').fill(lastName)
    await page.getByLabel('Date of birth').fill('2010-04-12')
    await page.getByLabel('Class', { exact: true }).selectOption({ label: CLASS_NAME })
    await page.getByRole('button', { name: 'Create student' }).click()

    await expect(page.getByRole('heading', { level: 1, name: fullName })).toBeVisible()
    await expect(page.getByText(`${fullName} was added`)).toBeVisible()
  })

  await test.step('mark the student absent', async () => {
    await navigate(page, 'Attendance')
    await page.getByLabel('Class').selectOption({ label: CLASS_NAME })
    await page.getByLabel('Date').fill(SCHOOL_DAY)
    const row = page.getByRole('group', { name: `Attendance for ${fullName}` })
    await expect(row).toBeVisible()
    await row.getByText('Absent', { exact: true }).click()
    await expect(row.getByRole('radio', { name: 'Absent' })).toBeChecked()
    await page.getByRole('button', { name: 'Save attendance' }).click()
    await expect(page.getByText(`Attendance saved for ${CLASS_NAME}`)).toBeVisible()
  })

  await test.step('enter a grade', async () => {
    await navigate(page, 'Grades')
    await page.getByLabel('Class').selectOption({ label: CLASS_NAME })
    const assessment = page.getByLabel('Assessment')
    await expect(assessment.locator('option')).not.toHaveCount(1)
    await assessment.selectOption({ index: 1 })
    const score = page.getByLabel(new RegExp(fullName))
    await score.fill('99')
    await expect(page.getByText(/Maximum is/)).toBeVisible()
    await score.fill('15')
    await page.getByRole('button', { name: 'Save grades' }).click()
    await expect(page.getByText('Grades saved')).toBeVisible()
  })

  await test.step('records appear on the student page, then clean up', async () => {
    await navigate(page, 'Students')
    await page.getByLabel('Search').fill(lastName)
    await page.getByRole('link', { name: new RegExp(lastName) }).first().click()
    await expect(page.getByRole('heading', { level: 1, name: fullName })).toBeVisible()
    const attendance = page.getByRole('region', { name: 'Attendance' })
    const absent = attendance.locator('div').filter({ has: page.getByRole('term').filter({ hasText: /^Absent$/ }) })
    await expect(absent.getByRole('definition')).toHaveText('1')
    await expect(page.getByRole('region', { name: 'Grades' }).getByText('15/')).toBeVisible()

    await page.getByRole('button', { name: 'Delete' }).click()
    const dialog = page.getByRole('dialog', { name: 'Delete student?' })
    await dialog.getByRole('button', { name: 'Delete student' }).click()
    await expect(page.getByRole('heading', { level: 1, name: 'Students' })).toBeVisible()
    await expect(page.getByText('Student deleted')).toBeVisible()
  })
})
