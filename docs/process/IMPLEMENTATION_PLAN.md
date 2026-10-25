# EduPulse — Implementation Plan

EduPulse is a school management platform (students, teachers, staff, classes, attendance,
grades) with an explainable at-risk early-warning module. This plan is the source of truth for
scope and order of work. Progress is tracked in `PROJECT_STATUS.md`; evidence for every gate is
in `REVIEW_PACKET.md`.

## Repository layout

```
backend/   FastAPI service (Python 3.12, SQLAlchemy 2, Alembic, Pydantic v2)
frontend/  React + TypeScript + Vite single-page app
ml/        Dataset fetch, training, evaluation and model export (scikit-learn)
docs/      Process records, model card, case study, screenshots
```

## Milestones

| ID | Name | Scope (summary) |
|----|------|-----------------|
| M0 | Skeleton | Monorepo, tooling (ruff, mypy, pytest, eslint, vitest), CI, Docker Compose, process records, README stub |
| M1 | Data model + migrations | Users, students, teachers, staff, classes, subjects, teaching assignments, enrolments, attendance, assessments, grades; constraints and indexes; Alembic; synthetic seed |
| M2 | Auth + security | Register (admin only), login, refresh, logout, me, role guards, password policy, login rate limit, CORS from config; role-boundary tests |
| M3 | Core API | CRUD + search/filter/sort/pagination; bulk attendance; grade entry; CSV import/export with per-row errors; OpenAPI; 404/403/409/422 tests |
| M4 | Frontend core | Login, responsive shell, dashboard, list/detail/edit pages, forms, toasts, confirm dialogs; Vitest + Playwright (375 px and 1440 px) |
| M5 | ML early-warning | UCI Student Performance; leakage control; holdout + repeated CV; baselines; AP; OOF threshold; bootstrap CIs; fairness by sex; model card; app feature mapping and scoring |
| M6 | ML in the UI | Class risk list, student risk panel, plain-language factors, trends, disclaimer, teacher scoping, audit log |
| M7 | Hardening | Structured logs, request IDs, JSON errors, health/readiness, security headers, pip-audit/npm audit, axe, Lighthouse |
| M8 | Docs + release | README, architecture diagram, screenshots, case study, LICENSE, NOTICE |
| M9 | Publish | Privacy scan of history, private GitHub repo, CI green, v1.0.0 release, stop |

## Gate (applies before each next milestone)

1. Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest --cov` (≥ 85 % on new modules).
2. Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`; Playwright from M4.
3. Update `PROJECT_STATUS.md`, append verbatim output to `REVIEW_PACKET.md`, commit `M<n>: <summary>`.
4. No test is deleted, skipped or weakened to pass a gate.

## Key design choices (details and rationale in PROJECT_STATUS.md → Decisions)

- Dependency management: `uv` for Python projects (`backend/`, `ml/`), `npm` for the frontend.
- Postgres 16 in Docker for development and runtime; SQLite in-memory only inside the test suite.
- Authorisation model: a teacher "owns" a class if they are its homeroom teacher or teach any
  subject in it. All teacher-scoped queries filter through that relation.
- The ML model only uses features that EduPulse itself records and that are known at the
  prediction moment: first-period grade and prior failures (whole-year absences were removed in
  review T-R2). Protected and socioeconomic attributes are never model inputs.
