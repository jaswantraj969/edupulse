import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'
import { login } from './helpers'

// Documentation screenshots (synthetic demo data). Run with:
//   SCREENSHOTS=1 E2E_PASSWORD=... npx playwright test e2e/screenshots.spec.ts
test.skip(!process.env.SCREENSHOTS, 'set SCREENSHOTS=1 to regenerate docs/screenshots')

const OUT = fileURLToPath(new URL('../../docs/screenshots/', import.meta.url))
const SCHOOL_DAY = '2025-10-07'

async function settle(page: Page) {
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByText(/^Loading/)).toHaveCount(0)
  await page.mouse.move(0, 0)
  await page.waitForTimeout(600) // let charts finish drawing
}

async function shoot(page: Page, name: string, fullPage = false) {
  await settle(page)
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage, animations: 'disabled' })
}

async function scrollIntoView(page: Page, text: string) {
  await page.getByRole('heading', { name: text }).scrollIntoViewIfNeeded()
}

test('documentation screenshots', async ({ page }, testInfo) => {
  test.setTimeout(180_000)
  const prefix = testInfo.project.name.startsWith('mobile') ? 'mobile' : 'desktop'
  await page.addInitScript(() => window.localStorage.setItem('edupulse-theme', 'light'))

  await page.goto('/login')
  await shoot(page, `${prefix}-login`)
  await login(page)

  // Class 10-A and its highest-risk student, looked up through the UI.
  await page.goto('/classes?q=10-A')
  const classHref = await page.locator('a[href^="/classes/"]').first().getAttribute('href')
  const classId = classHref!.split('/').pop()!
  await page.goto(`/early-warning?class_id=${classId}`)
  await settle(page)
  const studentHref = await page.locator('a[href^="/early-warning/students/"]:visible').first().getAttribute('href')

  await page.goto('/')
  await shoot(page, `${prefix}-dashboard`, prefix === 'desktop')
  await page.goto('/students')
  await shoot(page, `${prefix}-students`)
  await page.goto(`/attendance?class_id=${classId}&date=${SCHOOL_DAY}`)
  await shoot(page, `${prefix}-attendance`)
  await page.goto(`/grades?class_id=${classId}`)
  const assessment = page.getByLabel('Assessment')
  await expect(assessment.locator('option')).not.toHaveCount(1)
  await assessment.selectOption({ index: 1 })
  await shoot(page, `${prefix}-grades`)
  await page.goto(`/early-warning?class_id=${classId}`)
  await shoot(page, `${prefix}-early-warning`, prefix === 'desktop')
  await page.goto(studentHref!)
  if (prefix === 'mobile') await scrollIntoView(page, 'What drives this estimate')
  await shoot(page, `${prefix}-student-risk`, prefix === 'desktop')

  // Dark mode examples.
  await page.evaluate(() => window.localStorage.setItem('edupulse-theme', 'dark'))
  await page.addInitScript(() => window.localStorage.setItem('edupulse-theme', 'dark'))
  await page.goto('/')
  await shoot(page, `${prefix}-dashboard-dark`)
  await page.goto(studentHref!)
  await shoot(page, `${prefix}-student-risk-dark`)
})
