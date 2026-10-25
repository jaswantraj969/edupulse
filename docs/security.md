# Security and operations

## Authentication and sessions

- Passwords hashed with **argon2id** (`argon2-cffi` defaults); policy 12–128 characters with
  upper-case, lower-case and a digit. Unknown e-mails are verified against a dummy hash so
  response times do not reveal which accounts exist.
- **Access tokens:** JWT (HS256), 15 minutes, kept in browser memory only. The user's role and
  account status are re-read from the database on every request.
- **Refresh tokens:** random 64-character strings stored only as SHA-256 hashes, rotated on every
  use, revocable (logout). Re-using a rotated token revokes all of that user's sessions. They are
  sent **only** as an `HttpOnly; Secure; SameSite=Strict` cookie scoped to `/api/v1/auth` — never
  in a response body — and `/refresh` and `/logout` read them only from that cookie.
  `Secure` is on by default; browsers honour Secure cookies on `http://localhost` and
  `http://127.0.0.1`, so local Docker use works. `EDUPULSE_COOKIE_SECURE=false` exists only for
  plain-HTTP testing on other hosts.
- **Where tokens live in the browser:** access token in JavaScript module memory (lost on reload,
  restored through the refresh cookie); refresh token only in the httpOnly cookie (not readable
  by JavaScript). `localStorage` holds only the light/dark theme choice; `sessionStorage`,
  IndexedDB and `document.cookie` are not used.
- **Startup checks:** the API refuses to start if `EDUPULSE_JWT_SECRET` is missing, shorter than
  32 bytes, or a placeholder (the `.env.example` value is empty; common placeholders such as
  `change-me` are rejected). The seed script refuses an empty or default
  `EDUPULSE_DEMO_PASSWORD` and one that fails the password policy.
- **Login rate limit:** 5 failures per minute per (client IP, e-mail) and 20 per client IP →
  HTTP 429 with `Retry-After`. State is per process (see limitations).
- **Client address behind the proxy (review T-R3).** In docker compose the browser talks to
  nginx (`web`), which proxies `/api/` to `api:8000`, so the API's TCP peer is nginx. The
  compose network has a fixed subnet and nginx a fixed address (`EDUPULSE_PROXY_IP`, default
  `172.30.57.10`, outside the dynamic `ip_range`). Uvicorn runs with `--proxy-headers
  --forwarded-allow-ips="$EDUPULSE_TRUSTED_PROXY"` set to that address only; the entrypoint
  refuses `*`. nginx overwrites `X-Forwarded-For` with its peer address. A client that reaches
  the published API port directly (127.0.0.1:8000) is keyed by its own address and its
  `X-Forwarded-For` is ignored. Before T-R3 uvicorn trusted the header from any address, so
  forging it gave every attempt a fresh per-client key (25 failed logins with forged headers,
  no 429). Tests: `backend/tests/test_proxy_headers.py`. Outside compose, set
  `EDUPULSE_TRUSTED_PROXY` to the address of your own reverse proxy (default `127.0.0.1`).
- **Self sign-up requires administrator approval.** `POST /api/v1/auth/signup` creates an
  account with status `pending` and **no role**. Why approval rather than open registration:
  every account in EduPulse sees personal data about children (attendance, grades, risk
  estimates), and a teacher's access is defined by which teacher profile the account is linked
  to. Only an administrator can know that the person really is that teacher, so a sign-up can
  never grant access by itself.
  - A pending account can sign in, and `/auth/me` reports its status, but every data route
    (students, classes, attendance, grades, risk scores, exports, dashboard, admin pages)
    answers `403 account_pending`. The check sits in the shared `CurrentUser` dependency, so new
    routes inherit it. The UI shows only a *Waiting for approval* page.
  - An administrator approves (as `admin`, or as `teacher` linked to an existing teacher profile
    that has no account yet — the account then sees exactly that teacher's classes) or rejects
    (optional reason). Both are written to the audit log. Rejected and disabled accounts cannot
    sign in; they get the same error as a wrong password, and rejection revokes their sessions.
  - **No account discovery:** the sign-up response is identical whether or not the e-mail
    already has an account, and an existing account is never changed; the password is hashed
    either way so response times match. Validation errors only describe the submitted input.
  - **Rate limit:** 5 sign-up requests per client per hour (every request counts) → HTTP 429
    with `Retry-After`; same per-process caveat as the login limit.
  - Admins can still create accounts directly (`POST /api/v1/auth/register`).
- **Demo accounts on the login page.** The public `GET /api/v1/meta` endpoint returns the demo
  administrator and one demo teacher **with the demo password** only when `EDUPULSE_DEMO_MODE`
  is true and `EDUPULSE_DEMO_PASSWORD` is set for the API; otherwise `demo_accounts` is always
  empty (tested both ways). This is deliberate for a demo of synthetic data — anyone who can
  open the login page can then sign in as the demo administrator — so a real installation must
  run with demo mode off and no demo password.

## Public demo mode and deployment

- **`EDUPULSE_PUBLIC_DEMO=true`** (off by default) is for an installation anyone may use.
  - Deleting students, teachers, staff or classes, CSV import, approving or rejecting accounts,
    and creating administrator accounts return `403 disabled_in_public_demo` for every user,
    admins included.
  - The app disables those buttons (tooltip and accessible description) and shows "Public demo —
    synthetic data, reset every 6 hours" on every page.
  - No endpoint changes an existing account's password (a test checks the OpenAPI schema), so
    the demo passwords cannot be changed.
  - The `demo-reset` job puts the database back to exactly the synthetic seed every
    `EDUPULSE_DEMO_RESET_HOURS` (default 6). It deletes everything first, including sign-up
    accounts, audit entries and sessions, and re-seeds in one transaction. A test checks that a
    reset leaves exactly the seeded data.
- **Deployment (`deploy/`).**
  - Caddy is the only service with published ports (80/443): automatic HTTPS, HTTP → HTTPS
    redirect, HSTS.
  - `/api/*` goes straight from Caddy to the API, and uvicorn trusts `X-Forwarded-For` only from
    Caddy's fixed address (`172.31.58.10`). The database and API are not published, so Docker's
    port publishing cannot bypass the host firewall for them.
  - Daily `pg_dump` backups; restart policies; CPU/memory limits; rotated logs.
  - `deploy/make_env.sh` generates the secrets; no secret is stored in the repository.
  - `deploy/smoke_test.sh` checks a deployed URL (health, login page, redirect, security headers,
    blocked actions) without changing data.

## Authorisation

Roles `admin` and `teacher`. A teacher can see a class if they are its homeroom teacher or teach
a subject in it, and a student if the student is enrolled in such a class. Writes to people,
classes and subjects are admin-only; grades can be changed only by the subject's teacher (or an
admin). Every role boundary has API tests (`backend/tests/test_roles.py`, `test_students.py`,
`test_assessments.py`, `test_risk.py`, `test_audit.py`).

## Data handling

- All database access goes through the SQLAlchemy ORM / expression language; no SQL is built
  from strings.
- CSV exports neutralise spreadsheet formulas (`= + - @` prefixes); imports are validated row by
  row and are all-or-nothing, limited to 2 MiB / 5,000 rows, UTF-8.
- Student sex/gender is not stored (data minimisation). Demo data is synthetic.
- Early-warning scores: teachers only for their own classes; every view and export is written
  to an append-only audit log (`/audit` page, admin only).

## HTTP hardening

| Layer | Measures |
|---|---|
| API (FastAPI) | `X-Request-ID` on every response (caller id accepted only if `[A-Za-z0-9._-]{1,64}`); JSON errors `{error: {code, message, details, request_id}}`, no stack traces or database messages; `Content-Security-Policy: default-src 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store`; HSTS when `EDUPULSE_HSTS=true`; CORS limited to `EDUPULSE_CORS_ORIGINS` |
| Web (nginx) | Strict CSP (`script-src 'self'`, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`), the same frame/sniff/referrer/permissions headers, `server_tokens off`, immutable caching for hashed assets, `no-cache` for `index.html`, gzip |
| Containers | API runs as an unprivileged user; ports bound to `127.0.0.1`; no default secrets (`POSTGRES_PASSWORD`, `EDUPULSE_JWT_SECRET` required) |
| Model file | joblib (pickle) loaded only after its SHA-256 matches `model_meta.json` |

## Observability

- Structured JSON logs on stdout (one access line per request with `request_id`, method, path,
  status, duration, client IP, and `user_id` once authenticated). Unhandled errors are logged
  with stack traces server-side only.
- `GET /api/v1/health` — liveness (process up).
- `GET /api/v1/ready` — readiness: database `SELECT 1` and model load; HTTP 503 otherwise. Used
  by the Docker Compose health check; the web container starts after the API is ready.

## Checks run for every release

| Check | How |
|---|---|
| Dependency audit | `scripts/audit_deps.sh` (pip-audit on both Python lock files, `npm audit`); CI job `dependency-audit` |
| Accessibility | `frontend/e2e/a11y.spec.ts`: axe on 14 screens × light/dark × 375/1440 px; fails on serious/critical |
| Lighthouse (mobile) | `frontend/scripts/lighthouse.mjs` against the Docker build; target ≥ 90 performance and accessibility |
| Static analysis | ruff (incl. bandit `S` rules), mypy `--strict`, ESLint (incl. `jsx-a11y`), TypeScript strict |

Results are recorded in `docs/process/REVIEW_PACKET.md` (M7).

## Known limitations

- The login rate limiter is in-process memory; several API replicas need a shared store.
- No HTTPS termination is included (local Docker Compose). Behind TLS set `EDUPULSE_HSTS=true`
  and enable the commented HSTS line in `frontend/security-headers.conf`.
- No account self-service (password reset, MFA) — out of scope for this version.
