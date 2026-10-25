// Lighthouse (default mobile preset) against the built app, including signed-in pages.
//
//   E2E_BASE_URL=http://127.0.0.1:8088 E2E_PASSWORD=... node scripts/lighthouse.mjs [out.json]
//
// Lighthouse launches Playwright's Chromium itself. For signed-in pages the script logs in
// through the API first and passes the refresh-token cookie with --extra-headers; the SPA then
// restores the session exactly as it does after a page reload.
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const LIGHTHOUSE = 'lighthouse@13.5.0'
const BASE = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8088'
const PASSWORD = process.env.E2E_PASSWORD
if (!PASSWORD) throw new Error('Set E2E_PASSWORD')
const work = mkdtempSync(join(tmpdir(), 'lh-out-'))

async function post(url, init, attempts = 3) {
  // Retry: Node may reuse a keep-alive socket that nginx has just closed (UND_ERR_SOCKET).
  for (let i = 1; ; i++) {
    try {
      return await fetch(url, init)
    } catch (error) {
      if (i >= attempts) throw error
    }
  }
}

async function refreshCookie() {
  const response = await post(`${BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Connection: 'close' },
    body: new URLSearchParams({ username: 'admin@edupulse.example', password: PASSWORD }),
  })
  if (!response.ok) throw new Error(`login failed: ${response.status}`)
  // The refresh token only arrives as a Set-Cookie header (never in the JSON body).
  const token = /edupulse_refresh=([^;]+)/.exec(response.headers.get('set-cookie') ?? '')?.[1]
  if (!token) throw new Error('login response had no refresh cookie')
  const { access_token: access } = await response.json()
  return { cookie: `edupulse_refresh=${token}`, access }
}

async function audit(name, path, signedIn) {
  const out = join(work, `${name}.json`)
  const args = [
    '-y',
    LIGHTHOUSE,
    `${BASE}${path}`,
    '--chrome-flags=--headless=new',
    '--only-categories=performance,accessibility,best-practices,seo',
    '--output=json',
    `--output-path=${out}`,
    ...(process.env.LH_VERBOSE ? [] : ['--quiet']),
  ]
  if (signedIn) {
    // A file avoids shell-quoting JSON on Windows.
    const headers = join(work, `${name}-headers.json`)
    writeFileSync(headers, JSON.stringify({ Cookie: (await refreshCookie()).cookie }))
    args.push(`--extra-headers=${headers}`)
  }
  const windows = process.platform === 'win32'
  // On Windows npx is a .cmd file run through the shell: quote arguments (URLs contain '&').
  execFileSync(windows ? 'npx.cmd' : 'npx', windows ? args.map((a) => `"${a}"`) : args, {
    stdio: 'inherit',
    shell: windows,
    env: { ...process.env, CHROME_PATH: chromium.executablePath() },
  })
  const report = JSON.parse(readFileSync(out, 'utf8'))
  if (signedIn && !report.finalDisplayedUrl.includes(path.split('?')[0])) {
    throw new Error(`${name}: ended on ${report.finalDisplayedUrl}, not signed in`)
  }
  const score = (key) => Math.round((report.categories[key]?.score ?? 0) * 100)
  const metric = (key) => report.audits[key]?.displayValue ?? '-'
  return {
    page: name,
    path,
    performance: score('performance'),
    accessibility: score('accessibility'),
    best_practices: score('best-practices'),
    seo: score('seo'),
    fcp: metric('first-contentful-paint'),
    lcp: metric('largest-contentful-paint'),
    tbt: metric('total-blocking-time'),
    cls: metric('cumulative-layout-shift'),
    lighthouse: report.lighthouseVersion,
    form_factor: report.configSettings.formFactor,
  }
}

const results = []
try {
  const { access } = await refreshCookie()
  const students = await (
    await fetch(`${BASE}/api/v1/students?sort=student_no&page_size=1`, { headers: { Authorization: `Bearer ${access}` } })
  ).json()
  const studentId = students.items[0].id

  // LH_PAGES=dashboard,students limits the run (e.g. for repeated before/after measurements).
  const only = process.env.LH_PAGES?.split(',')
  const wanted = (name) => !only || only.includes(name)
  if (wanted('login')) results.push(await audit('login', '/login', false))
  for (const [name, path] of [
    ['dashboard', '/'],
    ['students', '/students'],
    ['attendance', '/attendance?class_id=1&date=2025-10-07'],
    ['early-warning', '/early-warning?class_id=1'],
    ['student-risk', `/early-warning/students/${studentId}`],
  ]) {
    if (wanted(name)) results.push(await audit(name, path, true))
  }
} finally {
  rmSync(work, { recursive: true, force: true })
}

console.table(results.map(({ lighthouse: _l, form_factor: _f, ...row }) => row))
console.log(`Lighthouse ${results[0]?.lighthouse}, form factor: ${results[0]?.form_factor}`)
const output = process.argv[2]
if (output) writeFileSync(output, JSON.stringify(results, null, 2) + '\n')
const failing = results.filter((r) => r.performance < 90 || r.accessibility < 90)
if (failing.length) {
  console.error(`Below target (90): ${failing.map((r) => r.page).join(', ')}`)
  process.exitCode = 1
}
