import { expect, test } from '@playwright/test'
import { login, navigate, signOut } from './helpers'

test('teacher reviews early-warning scores; the views are audited', async ({ page }) => {
  let teacherEmail = ''

  await test.step('admin looks up a demo teacher account', async () => {
    await login(page)
    await page.goto('/teachers?q=TCH001')
    // The e-mail column is in the desktop table, which is hidden (but present) at 375 px.
    const row = page.locator('table tbody tr').first()
    await expect(row).toHaveCount(1)
    teacherEmail = ((await row.locator('td').nth(3).textContent()) ?? '').trim()
    expect(teacherEmail).toMatch(/@edupulse\.example$/)
    await signOut(page)
  })

  await test.step('teacher sees only their classes and a labelled, explained risk list', async () => {
    await login(page, teacherEmail)
    await navigate(page, 'Early warning')
    const picker = page.getByLabel('Class')
    await expect(picker).toBeEnabled() // classes loaded
    await expect(picker.locator('option')).not.toHaveCount(1)
    const options = (await picker.locator('option').allTextContents()).slice(1)
    expect(options.length).toBeGreaterThan(0)
    expect(options.length).toBeLessThan(15) // not every class in the school
    await picker.selectOption({ index: 1 })

    const note = page.getByRole('note')
    await expect(note).toContainText("Decision support; review with the student's context.")
    await expect(note).toContainText('Demo — synthetic data')
    await expect(page.getByText(/As of .* high · .* medium · .* low/)).toBeVisible()
  })

  await test.step('teacher opens a student panel with plain-language factors', async () => {
    const studentLink = page.locator('a[href^="/early-warning/students/"]:visible').first()
    await studentLink.click()
    await expect(page.getByRole('heading', { level: 2, name: 'Estimate by subject' })).toBeVisible()
    await expect(page.getByRole('note')).toContainText("review with the student's context")
    const bySubject = page.getByRole('region', { name: 'Estimate by subject' })
    await expect(bySubject.getByRole('heading', { level: 3 }).first()).toBeVisible()
    // Every scored subject lists exactly its two factors: Term 1 subject average and previous failures.
    const factorLists = bySubject.getByRole('list', { name: /^What drives the .+ estimate$/ })
    expect(await factorLists.count()).toBeGreaterThan(1)
    for (const list of await factorLists.all()) await expect(list.getByRole('listitem')).toHaveCount(2)
    const factors = factorLists.first().getByRole('listitem')
    await expect(factors.first()).toContainText(/Term 1 .+ average of/)
    await expect(bySubject.getByText(/absence/i)).toHaveCount(0)
    await expect(factors.first()).toContainText(/Raises|Lowers/)
    const estimate = page.getByRole('region', { name: 'Estimate', exact: true })
    await expect(estimate.getByText(/(High|Medium|Low) risk/)).toBeVisible()
    await expect(estimate).toContainText('Highest-risk subject:')
    await expect(page.getByRole('region', { name: 'Attendance and grade trend' })).toBeVisible()
    await signOut(page)
  })

  await test.step('admin finds the views in the audit log', async () => {
    await login(page)
    await navigate(page, 'Audit log')
    await page.getByLabel('Search').fill(teacherEmail)
    await expect(page.getByText('Viewed student risk panel').first()).toBeAttached()
    await expect(page.getByText('Viewed class risk list').first()).toBeAttached()
  })
})
