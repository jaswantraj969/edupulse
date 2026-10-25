import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { login } from './helpers'

// Every main screen, checked with axe (WCAG 2.0/2.1/2.2 A and AA rules) in light and dark mode.
// The build fails on any "serious" or "critical" violation; others are reported.
const SCHOOL_DAY = '2025-10-07'

async function firstHref(page: Page, selector: string): Promise<string> {
  const link = page.locator(selector).first()
  await expect(link).toBeAttached()
  return (await link.getAttribute('href')) ?? '/'
}

async function pages(page: Page): Promise<[string, string][]> {
  await page.goto('/students?sort=student_no')
  const student = await firstHref(page, 'a[href^="/students/"]:not([href="/students/new"])')
  await page.goto('/classes')
  const klass = await firstHref(page, 'a[href^="/classes/"]')
  const classId = klass.split('/').pop()!
  await page.goto(`/grades?class_id=${classId}`)
  const assessment = page.getByLabel('Assessment')
  await expect(assessment.locator('option')).not.toHaveCount(1)
  const assessmentId = await assessment.locator('option').nth(1).getAttribute('value')
  return [
    ['dashboard', '/'],
    ['students', '/students'],
    ['student detail', student],
    ['student form', '/students/new'],
    ['teachers', '/teachers'],
    ['staff', '/staff'],
    ['classes', '/classes'],
    ['class detail', klass],
    ['attendance', `/attendance?class_id=${classId}&date=${SCHOOL_DAY}`],
    ['grades', `/grades?class_id=${classId}&assessment_id=${assessmentId}`],
    ['early warning', `/early-warning?class_id=${classId}`],
    ['student risk', student.replace('/students/', '/early-warning/students/')],
    ['audit log', '/audit'],
  ]
}

async function scan(page: Page, label: string, testInfo: { attach: (n: string, o: { body: string; contentType: string }) => Promise<void> }) {
  // Let lazy chunks, charts and data settle before scanning.
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: /Loading|Signing in/ })).toHaveCount(0)
  await expect(page.getByText(/^Loading/)).toHaveCount(0)
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
    .analyze()
  const blocking = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  const summary = results.violations.map((v) => `${v.impact}: ${v.id} (${v.nodes.length})`).join('; ') || 'none'
  console.log(`[axe] ${label}: ${results.passes.length} rules passed; violations: ${summary}`)
  await testInfo.attach(`axe-${label}`, { body: JSON.stringify(results.violations, null, 2), contentType: 'application/json' })
  expect(blocking.map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`)).toEqual([])
}

for (const theme of ['light', 'dark'] as const) {
  test(`no serious accessibility violations (${theme} mode)`, async ({ page }, testInfo) => {
    test.setTimeout(180_000)
    await page.addInitScript((t) => window.localStorage.setItem('edupulse-theme', t), theme)
    await page.goto('/login')
    await scan(page, `${theme} login`, testInfo)
    await login(page)
    for (const [label, url] of await pages(page)) {
      await page.goto(url)
      await scan(page, `${theme} ${label}`, testInfo)
    }
  })
}
