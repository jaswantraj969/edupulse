# Security and operations

## Authentication and sessions

- Passwords hashed with **argon2id** (`argon2-cffi` defaults); policy 12–128 characters with
  upper-case, lower-case and a digit. Unknown e-mails are verified against a dummy hash so
  response times do not reveal which accounts exist.
- **Access tokens:** JWT (HS256), 15 minutes, kept in browser memory only. The user's role and
  active flag are re-read from the database on every request.
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
- Registration is admin-only; there is no self sign-up.

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
