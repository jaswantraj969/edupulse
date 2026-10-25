# EduPulse

School management platform (students, teachers, staff, classes, attendance, grades) with an
explainable at-risk early-warning module for decision support.

> Work in progress. See `docs/process/IMPLEMENTATION_PLAN.md` and
> `docs/process/PROJECT_STATUS.md`.

## Quickstart

```bash
cp .env.example .env   # then fill in the secrets
docker compose up --build
```

- Web app: http://localhost:8088
- API docs: http://localhost:8000/api/v1/docs

## Repository layout

| Path | Contents |
|------|----------|
| `backend/` | FastAPI service |
| `frontend/` | React + TypeScript SPA |
| `ml/` | Early-warning model training and evaluation |
| `docs/` | Process records and documentation |
