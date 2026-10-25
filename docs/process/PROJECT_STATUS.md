# EduPulse — Project Status

Status values: `not started`, `in progress`, `done`. "Done" means the milestone gate was run and
its output recorded in `REVIEW_PACKET.md`; it is not a claim of external verification.

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 Skeleton | done | see git log (M0) |
| M1 Data model + migrations | done | see git log (M1) |
| M2 Auth + security | done | see git log (M2) |
| M3 Core API | done | see git log (M3) |
| M4 Frontend core | not started | — |
| M5 ML early-warning | not started | — |
| M6 ML in the UI | not started | — |
| M7 Hardening | not started | — |
| M8 Docs + release | not started | — |
| M9 Publish | not started | — |

## Resume point

Start of M4 (frontend core).

## Decisions

| # | Milestone | Decision | Rationale |
|---|-----------|----------|-----------|
| D1 | M0 | Python projects managed with `uv` (lockfiles committed); Python 3.12 provided by uv because only 3.13 was installed locally. | Reproducible installs locally, in Docker and in CI. |
| D2 | M0 | Frontend scaffolded with `create-vite` (react-ts), then ESLint 9 replaces the template's oxlint. | ESLint gives `jsx-a11y` accessibility rules; ESLint 10 is not yet accepted by `eslint-plugin-jsx-a11y`'s peer range. |
| D3 | M0 | `@hookform/resolvers` pinned to v5 (Zod 4 support). | v6 has an unresolvable optional peer conflict (`effect`). |
| D4 | M0 | Tailwind CSS v4 through `@tailwindcss/vite`. | Current major; no PostCSS config needed. |
| D5 | M0 | `scikit-learn` pinned to the same exact version in `backend/` and `ml/`. | The backend loads the model persisted by `ml/`; pickled estimators are only safe across identical versions. |
| D6 | M0 | Web container is nginx serving the built SPA and reverse-proxying `/api` to the API. | Same-origin API in the packaged app, so the refresh cookie can be `SameSite=Strict`. |
| D7 | M0 | Compose publishes ports on 127.0.0.1 only and requires `POSTGRES_PASSWORD` and `EDUPULSE_JWT_SECRET` from `.env`. | No default secrets; nothing exposed beyond localhost. |
| D8 | M0 | Web port defaults to 8088; all host ports configurable via `.env`. | 8080 was occupied on the development machine. |
| D9 | M0 | `scripts/gate.sh` runs every gate check; `scripts/sanitize_output.py` masks local paths in its output. | Verbatim, commit-safe evidence for REVIEW_PACKET.md. |
| D10 | M1 | Local database URLs use `127.0.0.1`, not `localhost`. | On Windows `localhost` resolves to `::1` first; Docker binds IPv4 only and the IPv6 connect stalled. |
| D11 | M1 | Enums stored as VARCHAR + CHECK (`native_enum=False`); timestamps default to `CURRENT_TIMESTAMP`; Alembic `render_as_batch`. | One migration history that runs on Postgres and on SQLite in tests; a test asserts no drift between models and migrations. |
| D12 | M1 | Class ownership for teachers = homeroom teacher OR any teaching assignment in the class. | Matches how schools work and gives one rule for "teacher sees only own classes". |
| D13 | M1 | Attendance is daily (one record per student per day), not per lesson. | The brief asks for bulk marking per class per day; daily absences also map to the UCI `absences` feature. |
| D14 | M1 | Student sex/gender is not stored. | Data minimisation: the app never uses it, and the fairness check runs on the UCI data in `ml/`. |
| D15 | M1 | `students.prior_failures` (0–3) stored on the student profile. | Needed for the early-warning feature that mirrors UCI `failures`; schools hold this from prior years. |
| D16 | M1 | Seed uses Faker (fixed seed 20250901), `@edupulse.example` e-mails and fictional `+1-555-01xx` phones; hidden traits (never stored) drive consistent grades/attendance; demo password from `EDUPULSE_DEMO_PASSWORD`. | Synthetic, reproducible, clearly non-real demo data with realistic spread. |
| D17 | M1 | Grade upper bound (`score <= max_score`) enforced in the service layer. | A cross-table CHECK is not possible in portable SQL. |
| D18 | M2 | Access JWT (HS256, 15 min, claims sub/role/type/iat/nbf/exp/jti); the user's role and active flag are re-read from the database on every request. | Demotion or deactivation takes effect immediately; the token's role claim is informational only. |
| D19 | M2 | Refresh tokens are opaque random strings stored as SHA-256 hashes, rotated on every use; presenting a revoked token revokes all of that user's sessions. | Server-side revocation for logout and theft detection without storing usable secrets. |
| D20 | M2 | Refresh token returned in the JSON body (OAuth2-compatible) and set as an httpOnly, `SameSite=Strict` cookie scoped to `/api/v1/auth`; the SPA keeps the access token in memory only. | Browser clients never expose the refresh token to JavaScript; API clients can still use the body. |
| D21 | M2 | Login rate limit: in-memory sliding window, 5 failures/min per (client IP, e-mail) and 20/min per client IP; success resets the account counter. | Meets the brief without extra infrastructure. Limitation: per-process state (see Deviations). |
| D22 | M2 | Password policy: 12–128 characters with upper-case, lower-case and a digit. | NIST-style length emphasis with basic composition rules. |
| D23 | M2 | Error shape `{"error": {"code", "message", "details"}}` for every error, including validation errors (`details` lists field/message/type). | One format for the frontend and the M7 hardening work. |
| D24 | M2 | Unknown e-mail logins still run an argon2 verification against a dummy hash. | Prevents account enumeration through response timing. |
| D25 | M2 | A teacher requesting an existing class/student outside their scope gets 403; a non-existent id gets 404. | Matches the brief's 403/404 distinction; ids are not secret. |
| D26 | M3 | List endpoints share one contract: `page` (1-based), `page_size` (≤ 100), `sort` (allow-listed per resource), `order`, `q` (case-insensitive substring); response `{items, total, page, page_size}`. Unknown sort fields are 422. | Predictable for the UI; sorting is never driven by raw user input. |
| D27 | M3 | CSV import is all-or-nothing: every row is validated (schema, duplicates within the file and against the DB, unknown classes) and any error returns 422 with `details.errors = [{row, field, message}]`; `dry_run=true` validates only. Limits: 2 MiB, 5000 rows, UTF-8. | Partial imports are hard for staff to reconcile; line numbers match the spreadsheet. |
| D28 | M3 | CSV export prefixes cells starting with `= + - @ tab CR` with `'`; import strips that prefix again. | Prevents spreadsheet formula injection while keeping export → import round-trips lossless. |
| D29 | M3 | Students list/export joins the student's class in the *current* academic year (latest start date). | One active year at a time; history stays in enrolments. |
| D30 | M3 | Teachers can read the teacher directory; staff records are admin-only; student writes are admin-only. | Least privilege: teachers need colleagues' names, not HR data. |
| D31 | M3 | Assessments and grades can be changed only by admins or the teacher of that subject in that class; homeroom teachers can read them. | Prevents one teacher altering another's marks. |
| D32 | M3 | Deletes that would destroy linked data are refused with 409 (teacher with assignments, class with students, assignment with assessments, subject in use); deleting a student or assessment cascades. An `IntegrityError` handler maps any remaining constraint race to 409 without echoing DB details. | Explicit, recoverable errors instead of silent cascades. |
| D33 | M3 | Attendance dates must be inside the class's academic year and not in the future; weekends are allowed. | Some schools teach on Saturdays. |
| D34 | M3 | Starlette's TestClient now prefers `httpx2`; the dev dependency switched from `httpx` to `httpx2`. | Removes the deprecation warning instead of suppressing it. |

## Deviations and limitations

- Login rate-limit state is per API process; a multi-instance deployment would need a shared store (e.g. Redis). (M2)
- Academic years and terms are read-only through the API (created by the seed/migrations); a year-rollover workflow is out of scope. (M3)
