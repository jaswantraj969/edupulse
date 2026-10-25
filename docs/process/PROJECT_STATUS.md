# EduPulse — Project Status

Status values: `not started`, `in progress`, `done`. "Done" means the milestone gate was run and
its output recorded in `REVIEW_PACKET.md`; it is not a claim of external verification.

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 Skeleton | done | see git log (M0) |
| M1 Data model + migrations | done | see git log (M1) |
| M2 Auth + security | not started | — |
| M3 Core API | not started | — |
| M4 Frontend core | not started | — |
| M5 ML early-warning | not started | — |
| M6 ML in the UI | not started | — |
| M7 Hardening | not started | — |
| M8 Docs + release | not started | — |
| M9 Publish | not started | — |

## Resume point

Start of M2 (auth + security).

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

## Deviations and limitations

None yet.
