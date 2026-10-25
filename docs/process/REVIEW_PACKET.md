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

## M2 — Auth + security (2026-10-25)

Scope: OAuth2 password login with short-lived JWT access tokens (15 min), opaque refresh tokens stored as SHA-256 hashes and rotated on use (reuse revokes all sessions), httpOnly SameSite=Strict refresh cookie, logout, /me, admin-only register with password policy, login rate limit (per account and per client), role guards, teacher class scoping, CORS from config, consistent JSON errors. Tests cover every role boundary listed in the brief.

### Gate output (scripts/gate.sh)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
44 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 43 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
.....................................................................    [100%]

============================== warnings summary ===============================

.venv\Lib\site-packages\fastapi\testclient.py:1

  <repo>\backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

    from starlette.testclient import TestClient as TestClient  # noqa



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                     Stmts   Miss Branch BrPart  Cover   Missing

--------------------------------------------------------------------

app\api\routes\auth.py      75      0     18      1    99%   136->142

app\seed.py                206      3     62      2    98%   182-183, 452

app\services\auth.py        49      1     14      2    95%   41, 92->exit

--------------------------------------------------------------------

TOTAL                     1015      4    160      5    99%



26 files skipped due to complete coverage.

69 passed, 1 warning in 27.27s

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

1 passed in 0.07s

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
   Start at  16:37:25
   Duration  2.56s (environment 71%, setup 15%, tests 8%, import 2%, transform 2%, worker 1%)

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

✓ built in 246ms
[exit 0]

GATE RESULT: PASS
```

### Migration state on Postgres 16

```text
$ (cd backend && uv run alembic check)   # against Postgres 16
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
No new upgrade operations detected.
[exit 0]
$ (cd backend && uv run alembic current)
21ce113cdea7 (head)
```

### Live smoke test against docker compose (Postgres, seeded synthetic data)

```text
$ curl -s -X POST 127.0.0.1:8000/api/v1/auth/login -d "username=admin@edupulse.example&password=<demo password>" | python (print token_type, expires_in)
{'token_type': 'bearer', 'expires_in': 900}
$ curl -s 127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
{"id":1,"email":"admin@edupulse.example","full_name":"Demo Administrator","role":"admin","is_active":true,"teacher_id":null,"last_login_at":"2026-10-25T11:36:23.722297Z"}
$ curl -s "127.0.0.1:8000/api/v1/classes?page_size=3" -H "Authorization: Bearer <token>" | python (print total, class names)
15 ['10-A', '10-B', '10-C']
$ for i in 1..6: curl -s -o /dev/null -w "%{http_code} " -X POST .../auth/login -d "username=admin@edupulse.example&password=wrong"
401 401 401 401 401 429
```

Notes: the Postgres block filters Alembic's `Detected sequence`/`setting up autogenerate` INFO lines; the demo password and access token are replaced by placeholders in the smoke-test command lines. The rate-limit run shows five 401s then 429 because the API's default limit is 5 failures per minute per account.

## M3 — Core API (2026-10-25)

Scope: CRUD with search, filters, sorting and pagination for students, teachers, staff and classes; subjects and academic years; class rosters, enrolments and teaching assignments; bulk daily attendance per class; assessments and bulk grade entry (score <= max enforced); CSV import (validated, all-or-nothing, per-row errors, dry run) and formula-safe export for students/teachers/staff; dashboard aggregates; OpenAPI at /api/v1/docs. Tests include validation errors and 404/403/409 cases.

### Gate output (scripts/gate.sh)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
66 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 65 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 53%]

...............................................................          [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                            Stmts   Miss Branch BrPart  Cover   Missing

---------------------------------------------------------------------------

app\api\routes\assessments.py     130      1     42      2    98%   63, 177->176

app\api\routes\auth.py             75      0     18      1    99%   136->142

app\api\routes\catalog.py          42      0      4      1    98%   44->46

app\api\routes\classes.py         152      0     40      1    99%   163->167

app\api\routes\dashboard.py        55      0     20      3    96%   51->53, 73->75, 100->99

app\api\routes\staff.py            64      0      6      3    96%   67->69, 69->71, 71->73

app\api\routes\students.py        133      1     24      1    99%   89

app\core\errors.py                 40      1      0      0    98%   106

app\seed.py                       206      3     62      2    98%   182-183, 452

app\services\auth.py               49      1     14      2    95%   41, 92->exit

app\services\csv_io.py            115      1     42      3    97%   55->57, 57->59, 89

---------------------------------------------------------------------------

TOTAL                            2149      8    368     19    99%



32 files skipped due to complete coverage.

135 passed in 63.90s (0:01:03)

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

1 passed in 0.10s

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
   Start at  17:02:48
   Duration  2.17s (environment 73%, setup 11%, tests 10%, import 4%, transform 2%, worker 1%)

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

✓ built in 250ms
[exit 0]

GATE RESULT: PASS
```

### Live smoke test against docker compose (Postgres 16, seeded synthetic data)

```text
GET /dashboard -> 200 counts {'students': 400, 'teachers': 30, 'staff': 15, 'classes': 15} | weeks 37 | first week {'week_start': '2025-09-08', 'attendance_rate': 0.9405, 'records': 2000} | buckets {'0-10': 0, '10-20': 0, '20-30': 0, '30-40': 11, '40-50': 49, '50-60': 81, '60-70': 127, '70-80': 93, '80-90': 33, '90-100': 6}
GET /students?q=st2500&sort=student_no&order=desc&page_size=3 -> 200 total 99 [('ST250099', '11-D'), ('ST250098', '11-C'), ('ST250097', '11-B')]
GET /classes/{id}/attendance?date=2025-10-06 -> 200 class 10-A rows 27 statuses ['excused', 'present']
PUT /classes/{id}/attendance (same status, idempotent) -> 200
GET /classes/{id}/assessments -> 200 count 48 first Term 1 Quiz Mathematics graded 27
GET /assessments/{id}/grades -> 200 rows 27
GET /students/{id}/attendance -> 200 {'present': 176, 'absent': 3, 'late': 4, 'excused': 2, 'total': 185, 'attendance_rate': 0.973}
GET /students/export -> 200 lines 401 header student_no,first_name,last_name,date_of_birth,email,phone,guardian_name,guardian_phone,enrolled_on,status,prior_failures,class_name
teacher TCH001: GET /classes -> 200 own classes ['10-A', '10-E', '11-D', '11-E', '12-C']
teacher TCH001: GET /classes/{other} -> 403 | POST /students -> 403 | GET /staff -> 403
teacher TCH001: GET /dashboard -> 200 my_classes {'students': 134, 'teachers': 18, 'staff': 15, 'classes': 5}
```

The smoke test is a throw-away script (Python stdlib HTTP client) kept outside the repository; its printed output is pasted as produced.
