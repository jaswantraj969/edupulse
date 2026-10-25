import { expect, type Page } from '@playwright/test'

export const ADMIN_EMAIL = 'admin@edupulse.example'

export function demoPassword(): string {
  const password = process.env.E2E_PASSWORD
  if (!password) throw new Error('Set E2E_PASSWORD to the demo password used by the seed script')
  return password
}

export async function login(page: Page, email = ADMIN_EMAIL): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Password').fill(demoPassword())
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: /^Welcome/ })).toBeVisible()
}

/** Navigate with the visible main navigation (sidebar on desktop, bottom bar or "More" on mobile). */
export async function navigate(page: Page, label: string): Promise<void> {
  const link = page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: label, exact: true })
  if (await link.isVisible()) {
    await link.click()
  } else {
    await page.getByRole('button', { name: 'More' }).click()
    await page.getByRole('dialog', { name: 'More' }).getByRole('link', { name: label, exact: true }).click()
  }
  await expect(page.getByRole('heading', { level: 1, name: label })).toBeVisible()
}
