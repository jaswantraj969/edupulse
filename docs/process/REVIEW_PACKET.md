# EduPulse — Review Packet

One entry per milestone gate, newest last. Command output is pasted verbatim from
`scripts/gate.sh` (local absolute paths are masked as `<home>`/`<repo>` and colour codes are
stripped by the script; nothing else is edited).

## M0 — Skeleton (2026-10-25)

Scope: monorepo layout, uv/npm tooling, CI workflow, Docker Compose (db, api, web), process
records, README stub.

### Gate output (`scripts/gate.sh`)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
10 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 10 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
......                                                                   [100%]

============================== warnings summary ===============================

.venv\Lib\site-packages\fastapi\testclient.py:1

  <repo>\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

    from starlette.testclient import TestClient as TestClient  # noqa



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name    Stmts   Miss Branch BrPart  Cover   Missing

---------------------------------------------------

TOTAL      58      0      6      0   100%



7 files skipped due to complete coverage.

6 passed, 1 warning in 1.44s

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
3 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 3 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
.                                                                        [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                      Stmts   Miss Branch BrPart  Cover

-----------------------------------------------------------

edupulse_ml\__init__.py       1      0      0      0   100%

-----------------------------------------------------------

TOTAL                         1      0      0      0   100%

1 passed in 0.05s

[exit 0]

$ (cd frontend && npm run lint)

> edupulse-web@0.1.0 lint
> eslint . --max-warnings=0

[exit 0]

$ (cd frontend && npm run typecheck)

> edupulse-web@0.1.0 typecheck
> tsc -b --noEmit

[exit 0]

$ (cd frontend && npm test)

> edupulse-web@0.1.0 test
> vitest run


 RUN  v5.0.5 <repo>/frontend


 Test Files  1 passed (1)
      Tests  1 passed (1)
   Start at  16:01:16
   Duration  1.26s (environment 66%, tests 13%, setup 12%, transform 4%, import 4%, worker 2%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.53 kB │ gzip:  0.32 kB
dist/assets/index-BmbyWbE2.css    6.50 kB │ gzip:  1.94 kB
dist/assets/index-Cz-iWIdB.js   219.63 kB │ gzip: 68.63 kB

✓ built in 165ms
[exit 0]

GATE RESULT: PASS
```

### Docker Compose smoke check

```text
$ docker compose ps --format "{{.Name}} {{.Status}}"
edupulse-api-1 Up 33 seconds
edupulse-db-1 Up About a minute (healthy)
edupulse-web-1 Up 33 seconds
$ curl -s localhost:8088/api/v1/health
{"status":"ok"}
```

Note: host port 8080 was already in use on the development machine, so the web port defaults to
8088; all host ports are configurable (`EDUPULSE_WEB_PORT`, `EDUPULSE_API_PORT`,
`EDUPULSE_DB_PORT`).

## M1 — Data model + migrations (2026-10-25)

Scope: 13 tables with constraints and indexes, initial Alembic migration (portable across Postgres and SQLite), deterministic synthetic seed (400 students, 30 teachers, 15 staff, one academic year), tests for constraints, migrations and seed.

### Gate output (scripts/gate.sh)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
28 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 27 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
............................                                             [100%]

============================== warnings summary ===============================

.venv\Lib\site-packages\fastapi\testclient.py:1

  <repo>\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

    from starlette.testclient import TestClient as TestClient  # noqa



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name          Stmts   Miss Branch BrPart  Cover   Missing

---------------------------------------------------------

app\seed.py     206      3     62      2    98%   182-183, 452

---------------------------------------------------------

TOTAL           532      3     78      2    99%



16 files skipped due to complete coverage.

28 passed, 1 warning in 20.42s

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
3 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 3 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
.                                                                        [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                      Stmts   Miss Branch BrPart  Cover

-----------------------------------------------------------

edupulse_ml\__init__.py       1      0      0      0   100%

-----------------------------------------------------------

TOTAL                         1      0      0      0   100%

1 passed in 0.12s

[exit 0]

$ (cd frontend && npm run lint)

> edupulse-web@0.1.0 lint
> eslint . --max-warnings=0

[exit 0]

$ (cd frontend && npm run typecheck)

> edupulse-web@0.1.0 typecheck
> tsc -b --noEmit

[exit 0]

$ (cd frontend && npm test)

> edupulse-web@0.1.0 test
> vitest run


 RUN  v5.0.5 <repo>/frontend


 Test Files  1 passed (1)
      Tests  1 passed (1)
   Start at  16:28:17
   Duration  2.85s (environment 74%, setup 14%, tests 5%, transform 3%, import 3%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.53 kB │ gzip:  0.32 kB
dist/assets/index-BmbyWbE2.css    6.50 kB │ gzip:  1.94 kB
dist/assets/index-Cz-iWIdB.js   219.63 kB │ gzip: 68.63 kB

✓ built in 352ms
[exit 0]

GATE RESULT: PASS
```

### Migrations and seed against Postgres 16

```text
$ (cd backend && uv run alembic downgrade base)   # against Postgres 16 (docker compose db)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 7d8725238af7 -> , initial schema
[exit 0]

$ (cd backend && uv run alembic upgrade head)   # against Postgres 16 (docker compose db)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 7d8725238af7, initial schema
[exit 0]

$ (cd backend && uv run alembic check)   # against Postgres 16 (docker compose db)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
No new upgrade operations detected.
[exit 0]

$ (cd backend && uv run python -m app.seed)   # against Postgres 16 (docker compose db)
Seeded SYNTHETIC demo data (not real people):
  teachers                    30
  staff                       15
  students                   400
  users                       31
  subjects                     8
  academic_years               1
  terms                        3
  classes                     15
  teaching_assignments       120
  enrolments                 400
  attendance_records       74000
  assessments                720
  grades                   19200
Demo logins: admin@edupulse.example (admin), any teacher e-mail @ edupulse.example (teacher)
[exit 0]
```

Note: in the Postgres block, Alembic's INFO lines `Detected sequence named ... assuming SERIAL and omitting` and `setting up autogenerate plugin ...` were filtered with `grep -v` for length; all other lines are verbatim.
