# EduPulse — Project Status

Status values: `not started`, `in progress`, `done`. "Done" means the milestone gate was run and
its output recorded in `REVIEW_PACKET.md`; it is not a claim of external verification.

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 Skeleton | done | see git log (M0) |
| M1 Data model + migrations | not started | — |
| M2 Auth + security | not started | — |
| M3 Core API | not started | — |
| M4 Frontend core | not started | — |
| M5 ML early-warning | not started | — |
| M6 ML in the UI | not started | — |
| M7 Hardening | not started | — |
| M8 Docs + release | not started | — |
| M9 Publish | not started | — |

## Resume point

Start of M1 (data model + migrations).

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

## Deviations and limitations

None yet.
