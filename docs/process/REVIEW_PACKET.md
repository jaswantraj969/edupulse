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

## M4 — Frontend core (2026-10-25)

Scope: React SPA: login, responsive shell (sidebar on md+, bottom bar + 'More' dialog on mobile, skip link), dashboard (counts, weekly attendance trend, grade distribution; charts lazy-loaded with tooltips and data-table view), students list/detail/create/edit, teachers and staff CRUD dialogs, classes list/detail, bulk attendance marking, grade entry, CSV import (validate then import, per-row errors) and export, toasts, confirm dialogs, loading/empty/error states, light/dark/system theme. 32 Vitest component tests; Playwright flow login -> add student -> mark attendance -> enter grade (-> verify -> delete) at 375 px and 1440 px.

### Gate output (scripts/gate.sh --e2e; Playwright via vite preview against the docker compose API)

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

135 passed in 63.35s (0:01:03)

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

1 passed in 0.15s

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


 Test Files  7 passed (7)
      Tests  32 passed (32)
   Start at  17:24:55
   Duration  7.07s (environment 55%, tests 23%, setup 10%, import 8%, transform 2%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 772 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-oVxrD7Xk.css              34.49 kB │ gzip:   7.12 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-DErLqo5V.js              0.51 kB │ gzip:   0.26 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/format-Dn2OGqmF.js               0.60 kB │ gzip:   0.41 kB
dist/assets/ClassPicker-JJgPkOF6.js          0.66 kB │ gzip:   0.41 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-DjHIYDUz.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-Dcg8T4n5.js            1.98 kB │ gzip:   1.02 kB
dist/assets/ListToolbar-C8S9lQit.js          2.04 kB │ gzip:   0.93 kB
dist/assets/useMutation-BfMDPYYX.js          2.32 kB │ gzip:   0.97 kB
dist/assets/DashboardPage-MzBcWvN9.js        2.75 kB │ gzip:   1.15 kB
dist/assets/ClassesPage-DZ0S6l_J.js          2.79 kB │ gzip:   1.32 kB
dist/assets/StudentsListPage-BYPDPOac.js     3.20 kB │ gzip:   1.46 kB
dist/assets/ClassDetailPage-HDLkNKWX.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-CfhHOVuz.js            4.62 kB │ gzip:   1.96 kB
dist/assets/TeachersPage-_9RLvR8y.js         4.81 kB │ gzip:   2.00 kB
dist/assets/AttendancePage-CAN4yRpo.js       4.91 kB │ gzip:   2.00 kB
dist/assets/StudentDetailPage-BerDnpus.js    4.93 kB │ gzip:   1.85 kB
dist/assets/StudentForm-C8LMOPcC.js          5.97 kB │ gzip:   2.22 kB
dist/assets/DataTable-Bx_Kfqh5.js            6.12 kB │ gzip:   2.23 kB
dist/assets/GradesPage-D1yQpdJz.js           7.00 kB │ gzip:   2.70 kB
dist/assets/useQuery-Ca7SktmN.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/index-CGLlYuoW.js              351.69 kB │ gzip: 110.59 kB
dist/assets/DashboardCharts-DrLWL0Pd.js    376.83 kB │ gzip: 108.06 kB

✓ built in 572ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 2 tests using 1 worker

(node:16460) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 1 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (4.9s)
(node:19156) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 2 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.7s)

  2 passed (15.8s)
[exit 0]

GATE RESULT: PASS
```

### Playwright against the packaged app (docker compose: nginx web + api + Postgres)

```text
$ (cd frontend && E2E_BASE_URL=http://127.0.0.1:8088 npx playwright test --reporter=list)   # against docker compose (nginx + api + postgres)

Running 2 tests using 1 worker

  ok 1 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.4s)
  ok 2 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.7s)

  2 passed (13.6s)
[exit 0]
```

Bug found by the e2e run and fixed before this gate: saving attendance or grades did not invalidate the per-student queries, so a student page opened earlier showed stale 'No attendance recorded'. The first e2e run failed at that assertion; the fix is in AttendancePage/GradesPage (invalidate ['students']).

## M5 — ML early-warning module (2026-10-25)

Scope: UCI Student Performance fetched by script with SHA-256 verification and recorded provenance (ml/data/SOURCE.md, CC BY 4.0); prediction moment = end of first period (G2/G3 never inputs); student-grouped stratified 20 % holdout created once; 3x5 grouped CV on identical folds for dummy / logistic regression / gradient boosting; AP primary; threshold from out-of-fold predictions; single test scoring with 2000 cluster-bootstrap CIs; sex and socioeconomic proxies excluded, subgroup recall/precision by sex reported; ablations; generated run record; model card; backend scoring service computing the same features from EduPulse attendance and grades with SHA-256-verified model loading, plain-language explanations, demo labelling and teacher scoping; CI job that re-downloads the data and reproduces the run.

### Gate output (scripts/gate.sh --e2e)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
70 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 69 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 48%]

........................................................................ [ 96%]

......                                                                   [100%]

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

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2422     10    406     21    99%



34 files skipped due to complete coverage.

150 passed in 73.92s (0:01:13)

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
16 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 14 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
...................                                                      [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       21      0      0      0   100%

edupulse_ml\report.py         34      0     14      1    98%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         135      1     22      2    98%

------------------------------------------------------------

TOTAL                        355     30     84      5    91%

19 passed in 55.39s

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


 Test Files  7 passed (7)
      Tests  32 passed (32)
   Start at  17:44:53
   Duration  6.78s (environment 49%, tests 27%, setup 13%, import 8%, transform 1%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 772 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-oVxrD7Xk.css              34.49 kB │ gzip:   7.12 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-DErLqo5V.js              0.51 kB │ gzip:   0.26 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/format-Dn2OGqmF.js               0.60 kB │ gzip:   0.41 kB
dist/assets/ClassPicker-JJgPkOF6.js          0.66 kB │ gzip:   0.41 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-DjHIYDUz.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-Dcg8T4n5.js            1.98 kB │ gzip:   1.02 kB
dist/assets/ListToolbar-C8S9lQit.js          2.04 kB │ gzip:   0.93 kB
dist/assets/useMutation-BfMDPYYX.js          2.32 kB │ gzip:   0.97 kB
dist/assets/DashboardPage-MzBcWvN9.js        2.75 kB │ gzip:   1.15 kB
dist/assets/ClassesPage-DZ0S6l_J.js          2.79 kB │ gzip:   1.32 kB
dist/assets/StudentsListPage-BYPDPOac.js     3.20 kB │ gzip:   1.46 kB
dist/assets/ClassDetailPage-HDLkNKWX.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-CfhHOVuz.js            4.62 kB │ gzip:   1.96 kB
dist/assets/TeachersPage-_9RLvR8y.js         4.81 kB │ gzip:   2.00 kB
dist/assets/AttendancePage-CAN4yRpo.js       4.91 kB │ gzip:   2.00 kB
dist/assets/StudentDetailPage-BerDnpus.js    4.93 kB │ gzip:   1.85 kB
dist/assets/StudentForm-C8LMOPcC.js          5.97 kB │ gzip:   2.22 kB
dist/assets/DataTable-Bx_Kfqh5.js            6.12 kB │ gzip:   2.23 kB
dist/assets/GradesPage-D1yQpdJz.js           7.00 kB │ gzip:   2.70 kB
dist/assets/useQuery-Ca7SktmN.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/index-CGLlYuoW.js              351.69 kB │ gzip: 110.59 kB
dist/assets/DashboardCharts-DrLWL0Pd.js    376.83 kB │ gzip: 108.06 kB

✓ built in 745ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 2 tests using 1 worker

(node:20088) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 1 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.3s)
(node:20952) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 2 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.8s)

  2 passed (16.3s)
[exit 0]

GATE RESULT: PASS
```

### Reproduction check and scoring of the synthetic demo students

```text
$ (cd ml && uv run python -m edupulse_ml.reproduce)
reproduced

[exit 0]

$ python risk_dist.py   # throw-away script: scores every synthetic student via GET /api/v1/risk/classes/{id} on the docker compose API
as_of 2025-12-19 | model 1.0.0 logistic_regression | notice: Demo — synthetic data. Scores are illustrative and refer to no real student.

bands {'high': 46, 'medium': 34, 'low': 322} of 402

g1 (0-20): min 6.1 median 13.0 max 19.4

absences projected: median 4.9 p90 19.7 max 71.5

probability: median 0.009 p90 0.379 max 0.980
```

ML results (copied from ml/reports/run_record.md): chosen model logistic regression; CV AP 0.803 ± 0.057 (dummy 0.220 ± 0.002, gradient boosting 0.800 ± 0.036); test AP 0.817 [0.705, 0.901], ROC AUC 0.936 [0.900, 0.966]; at threshold 0.315 precision 0.627 [0.500, 0.740], recall 0.804 [0.674, 0.915]; recall gap F-M +0.083 (test), +0.056 (out-of-fold). The demo population count of 402 includes two students left behind by the first (failed) M4 e2e run; the database is reseeded before screenshots in M8.

## M6 — ML in the UI (2026-10-25)

Scope: Early-warning list per class (sortable by estimate or name; band always written out; main factor in plain language; CSV export), per-student panel (band, estimate, all factors with raises/lowers, Term 1 inputs, monthly attendance and grade trend charts with the prediction moment marked, data tables), a visible disclaimer ('Decision support; review with the student's context.') plus 'Demo — synthetic data' label on every early-warning screen, model details with test metrics and CIs; teachers limited to their classes (API-enforced); append-only audit log of risk views and exports (migration 3) with an admin audit page.

### Gate output (scripts/gate.sh --e2e)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
74 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 73 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 46%]

........................................................................ [ 93%]

..........                                                               [100%]

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

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2510     10    416     21    99%



37 files skipped due to complete coverage.

154 passed in 77.75s (0:01:17)

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
16 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 14 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
...................                                                      [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       21      0      0      0   100%

edupulse_ml\report.py         34      0     14      1    98%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         135      1     22      2    98%

------------------------------------------------------------

TOTAL                        355     30     84      5    91%

19 passed in 55.54s

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

Not implemented: navigation to another Document

 Test Files  8 passed (8)
      Tests  38 passed (38)
   Start at  18:11:57
   Duration  6.87s (environment 56%, tests 26%, setup 8%, import 8%, transform 1%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 778 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-Cr2T3bYc.css              35.91 kB │ gzip:   7.31 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-CfSZjk6g.js              0.51 kB │ gzip:   0.26 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/ClassPicker-B_luxRtQ.js          0.66 kB │ gzip:   0.41 kB
dist/assets/format-DqLuBCE3.js               0.66 kB │ gzip:   0.44 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-Dj_64n7V.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-B_wAODlH.js            1.98 kB │ gzip:   1.03 kB
dist/assets/AuditLogPage-BbUk_y-m.js         2.04 kB │ gzip:   1.04 kB
dist/assets/ListToolbar-CtPURdpS.js          2.06 kB │ gzip:   0.94 kB
dist/assets/useMutation-CZxuoCOv.js          2.32 kB │ gzip:   0.97 kB
dist/assets/RiskParts-DwQUUoR7.js            2.59 kB │ gzip:   0.97 kB
dist/assets/DashboardPage-D0vfn653.js        2.78 kB │ gzip:   1.17 kB
dist/assets/ClassesPage-BJC_Fa8O.js          2.79 kB │ gzip:   1.32 kB
dist/assets/CsvImportDialog-BnBqVPNn.js      3.01 kB │ gzip:   1.30 kB
dist/assets/DataTable-BuCZYttU.js            3.21 kB │ gzip:   1.23 kB
dist/assets/StudentsListPage-BaYnn6QQ.js     3.24 kB │ gzip:   1.48 kB
dist/assets/RiskListPage-CspD18p9.js         3.56 kB │ gzip:   1.71 kB
dist/assets/ClassDetailPage-NcPhG7rx.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-C9CF96nE.js            4.67 kB │ gzip:   1.97 kB
dist/assets/TeachersPage-FPT-LxEn.js         4.86 kB │ gzip:   2.02 kB
dist/assets/AttendancePage-Byy9aoaQ.js       4.91 kB │ gzip:   1.99 kB
dist/assets/StudentDetailPage-QjW5IuRG.js    5.06 kB │ gzip:   1.88 kB
dist/assets/StudentRiskPage-C2ElX3eg.js      5.96 kB │ gzip:   2.21 kB
dist/assets/StudentForm-Btifld6U.js          5.97 kB │ gzip:   2.22 kB
dist/assets/RiskTrendCharts-KxmhbVaV.js      6.41 kB │ gzip:   2.66 kB
dist/assets/GradesPage-DyzZ1qLf.js           7.00 kB │ gzip:   2.69 kB
dist/assets/useQuery-CkpnmNeg.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/DashboardCharts-CynyNJ3T.js     24.03 kB │ gzip:   8.04 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/index-CO5BGTUK.js              352.72 kB │ gzip: 110.89 kB
dist/assets/chartTheme-BRzSplXI.js         354.34 kB │ gzip: 103.23 kB

✓ built in 644ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 4 tests using 1 worker

(node:17488) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 1 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.4s)
  ok 2 [mobile-375] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (7.7s)
(node:9588) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
  ok 3 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (6.0s)
  ok 4 [desktop-1440] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (6.9s)

  4 passed (31.4s)
[exit 0]

GATE RESULT: PASS
```

### Migration state on Postgres 16

```text
$ (cd backend && uv run alembic current && uv run alembic check)   # Postgres 16
0d96e7cbb08f (head)
No new upgrade operations detected.
```

Fixed during this milestone: (1) list sorting tie-breaker now follows the sort direction (audit 'newest first' was unstable for equal timestamps); (2) after a deliberate sign-out the next user was redirected to the previous user's last page — the auth guard now keeps 'return to' state only when a session expired; (3) an e2e race (reading class options before they loaded) was fixed in the test by waiting for the options. The e2e suite was then run three times in a row: 4 passed each time.

## M7 — Hardening (2026-10-25)

Scope: Structured JSON logs with request ids (X-Request-ID echoed, sanitised) and user ids; consistent JSON errors incl. request_id, generic 500s without internals; /health (liveness) and /ready (DB + model) probes wired into Docker health checks; security headers on API and nginx (CSP, frame, sniff, referrer, permissions, COOP, no-store; HSTS when Secure cookies); dependency audits; axe on 14 screens x light/dark x 375/1440 px; Lighthouse mobile on the Docker build.

### Gate output (scripts/gate.sh --e2e; includes 56 axe scans)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
77 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 76 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 43%]

........................................................................ [ 86%]

......................                                                   [100%]

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

app\core\logging.py                35      1     10      1    96%   28

app\seed.py                       206      3     62      2    98%   182-183, 452

app\services\auth.py               49      1     14      2    95%   41, 92->exit

app\services\csv_io.py            115      1     42      3    97%   55->57, 57->59, 89

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2647     10    442     22    99%



39 files skipped due to complete coverage.

166 passed in 100.31s (0:01:40)

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
16 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 14 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
...................                                                      [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       21      0      0      0   100%

edupulse_ml\report.py         34      0     14      1    98%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         135      1     22      2    98%

------------------------------------------------------------

TOTAL                        355     30     84      5    91%

19 passed in 72.93s (0:01:12)

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

Not implemented: navigation to another Document

 Test Files  8 passed (8)
      Tests  39 passed (39)
   Start at  19:59:19
   Duration  6.97s (environment 51%, tests 30%, import 8%, setup 8%, transform 1%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 780 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-r9nMhY3h.css              38.25 kB │ gzip:   7.81 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-D8vtpeqI.js              0.51 kB │ gzip:   0.27 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/DeferredRender-CGSRHVuI.js       0.61 kB │ gzip:   0.38 kB
dist/assets/ClassPicker-CnXwr14W.js          0.66 kB │ gzip:   0.41 kB
dist/assets/format-DqLuBCE3.js               0.66 kB │ gzip:   0.44 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-DUfLLxzb.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-CGeTjuvy.js            1.98 kB │ gzip:   1.02 kB
dist/assets/AuditLogPage-E76Bxo7n.js         2.04 kB │ gzip:   1.04 kB
dist/assets/ListToolbar-CwzkzizX.js          2.06 kB │ gzip:   0.94 kB
dist/assets/useMutation-CPh81u1u.js          2.32 kB │ gzip:   0.97 kB
dist/assets/RiskParts-BdheHJRv.js            2.59 kB │ gzip:   0.97 kB
dist/assets/ClassesPage-D43GoEgN.js          2.79 kB │ gzip:   1.32 kB
dist/assets/DashboardPage-iZphQuxR.js        2.99 kB │ gzip:   1.24 kB
dist/assets/CsvImportDialog-CustKNbb.js      3.07 kB │ gzip:   1.32 kB
dist/assets/DataTable-iyqIzl6l.js            3.21 kB │ gzip:   1.23 kB
dist/assets/StudentsListPage-URdAojF8.js     3.24 kB │ gzip:   1.48 kB
dist/assets/RiskListPage-DlkQftTd.js         3.56 kB │ gzip:   1.71 kB
dist/assets/ClassDetailPage-BdDe4LZ9.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-ClizUYX2.js            4.67 kB │ gzip:   1.97 kB
dist/assets/TeachersPage-CGJQmGEl.js         4.86 kB │ gzip:   2.02 kB
dist/assets/AttendancePage-C6co3xBa.js       4.91 kB │ gzip:   1.99 kB
dist/assets/StudentDetailPage-CC5Lte0Q.js    5.14 kB │ gzip:   1.91 kB
dist/assets/StudentForm-C9gakEZh.js          5.97 kB │ gzip:   2.22 kB
dist/assets/StudentRiskPage-BycqRfBw.js      6.14 kB │ gzip:   2.26 kB
dist/assets/RiskTrendCharts-oHxtjvnt.js      6.55 kB │ gzip:   2.75 kB
dist/assets/GradesPage-BhRi_vq4.js           7.00 kB │ gzip:   2.69 kB
dist/assets/useQuery-B86WbdLh.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/DashboardCharts-BKet6WYV.js     24.30 kB │ gzip:   8.17 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/useElementWidth-MynoTyFU.js    347.70 kB │ gzip: 101.49 kB
dist/assets/index-DOKzYCNu.js              352.85 kB │ gzip: 110.93 kB

✓ built in 639ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 8 tests using 1 worker

(node:16460) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 32 rules passed; violations: none
[axe] light students: 38 rules passed; violations: none
[axe] light student detail: 42 rules passed; violations: none
[axe] light student form: 35 rules passed; violations: none
[axe] light teachers: 39 rules passed; violations: none
[axe] light staff: 39 rules passed; violations: none
[axe] light classes: 36 rules passed; violations: none
[axe] light class detail: 34 rules passed; violations: none
[axe] light attendance: 36 rules passed; violations: none
[axe] light grades: 36 rules passed; violations: none
[axe] light early warning: 42 rules passed; violations: none
[axe] light student risk: 39 rules passed; violations: none
[axe] light audit log: 38 rules passed; violations: none
  ok 1 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (36.1s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 32 rules passed; violations: none
[axe] dark students: 38 rules passed; violations: none
[axe] dark student detail: 42 rules passed; violations: none
[axe] dark student form: 35 rules passed; violations: none
[axe] dark teachers: 39 rules passed; violations: none
[axe] dark staff: 39 rules passed; violations: none
[axe] dark classes: 36 rules passed; violations: none
[axe] dark class detail: 34 rules passed; violations: none
[axe] dark attendance: 36 rules passed; violations: none
[axe] dark grades: 36 rules passed; violations: none
[axe] dark early warning: 42 rules passed; violations: none
[axe] dark student risk: 39 rules passed; violations: none
[axe] dark audit log: 38 rules passed; violations: none
  ok 2 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (35.8s)
  ok 3 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.2s)
  ok 4 [mobile-375] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (7.5s)
(node:7740) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 30 rules passed; violations: none
[axe] light students: 37 rules passed; violations: none
[axe] light student detail: 40 rules passed; violations: none
[axe] light student form: 33 rules passed; violations: none
[axe] light teachers: 38 rules passed; violations: none
[axe] light staff: 38 rules passed; violations: none
[axe] light classes: 34 rules passed; violations: none
[axe] light class detail: 32 rules passed; violations: none
[axe] light attendance: 34 rules passed; violations: none
[axe] light grades: 34 rules passed; violations: none
[axe] light early warning: 41 rules passed; violations: none
[axe] light student risk: 38 rules passed; violations: none
[axe] light audit log: 37 rules passed; violations: none
  ok 5 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (34.9s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 30 rules passed; violations: none
[axe] dark students: 37 rules passed; violations: none
[axe] dark student detail: 40 rules passed; violations: none
[axe] dark student form: 33 rules passed; violations: none
[axe] dark teachers: 38 rules passed; violations: none
[axe] dark staff: 38 rules passed; violations: none
[axe] dark classes: 34 rules passed; violations: none
[axe] dark class detail: 32 rules passed; violations: none
[axe] dark attendance: 34 rules passed; violations: none
[axe] dark grades: 34 rules passed; violations: none
[axe] dark early warning: 41 rules passed; violations: none
[axe] dark student risk: 38 rules passed; violations: none
[axe] dark audit log: 37 rules passed; violations: none
  ok 6 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (35.0s)
  ok 7 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.9s)
  ok 8 [desktop-1440] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (6.8s)

  8 passed (2.9m)
[exit 0]

GATE RESULT: PASS
```

### Dependency audit

```text
$ (cd backend && uv export --frozen --format requirements-txt --all-groups --no-emit-project -o <tmp>/req-backend.txt) && (cd backend && uv run pip-audit -r <tmp>/req-backend.txt --strict --progress-spinner off)
No known vulnerabilities found

[exit 0]

$ (cd ml && uv export --frozen --format requirements-txt --all-groups --no-emit-project -o <tmp>/req-ml.txt) && (cd backend && uv run pip-audit -r <tmp>/req-ml.txt --strict --progress-spinner off)
No known vulnerabilities found

[exit 0]

$ (cd frontend && npm audit)
found 0 vulnerabilities
[exit 0]
$ (cd frontend && npm audit --omit=dev)
found 0 vulnerabilities
[exit 0]
```

### Headers, readiness and structured logs on the Docker build

```text
$ curl -sI http://127.0.0.1:8088/students ; curl -sI <asset> ; curl -si http://127.0.0.1:8088/api/v1/ready   (after the nginx header refactor)
HTTP/1.1 200 OK
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
Cache-Control: no-cache

HTTP/1.1 200 OK
X-Frame-Options: DENY
Cache-Control: public, max-age=31536000, immutable
Content-Encoding: gzip

HTTP/1.1 200 OK
x-frame-options: DENY
content-security-policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'
cache-control: no-store
x-request-id: d7c6767d25bb85d5355465d566a0a5e3
{"status":"ready","checks":{"database":"ok","model":"ok (v1.0.0)"}}

$ docker compose ps
edupulse-api-1 Up 2 hours (healthy)
edupulse-db-1 Up 4 hours (healthy)
edupulse-web-1 Up 22 minutes

$ docker compose logs api --tail 1
{"ts": "2026-10-25T15:03:05.443+00:00", "level": "INFO", "logger": "edupulse.access", "message": "request", "request_id": "d7c6767d25bb85d5355465d566a0a5e3", "method": "GET", "path": "/api/v1/ready", "status": 200, "duration_ms": 6.8, "client": "172.18.0.1"}
```

### Lighthouse (mobile preset, simulated throttling) on the Docker build

```text
$ (cd frontend && E2E_BASE_URL=http://127.0.0.1:8088 E2E_PASSWORD=<demo password> node scripts/lighthouse.mjs)   # built app via docker compose, freshly seeded
┌─────────┬─────────────────┬──────────────────────────────────────────┬─────────────┬───────────────┬────────────────┬─────┬─────────┬─────────┬──────────┬─────┐
│ (index) │ page            │ path                                     │ performance │ accessibility │ best_practices │ seo │ fcp     │ lcp     │ tbt      │ cls │
├─────────┼─────────────────┼──────────────────────────────────────────┼─────────────┼───────────────┼────────────────┼─────┼─────────┼─────────┼──────────┼─────┤
│ 0       │ 'login'         │ '/login'                                 │ 95          │ 100           │ 92             │ 91  │ '2.1 s' │ '2.5 s' │ '90 ms'  │ '0' │
│ 1       │ 'dashboard'     │ '/'                                      │ 82          │ 100           │ 100            │ 91  │ '1.9 s' │ '2.2 s' │ '620 ms' │ '0' │
│ 2       │ 'students'      │ '/students'                              │ 92          │ 100           │ 100            │ 91  │ '2.0 s' │ '2.4 s' │ '230 ms' │ '0' │
│ 3       │ 'attendance'    │ '/attendance?class_id=1&date=2025-10-07' │ 96          │ 100           │ 96             │ 91  │ '2.0 s' │ '2.4 s' │ '100 ms' │ '0' │
│ 4       │ 'early-warning' │ '/early-warning?class_id=1'              │ 96          │ 100           │ 96             │ 91  │ '2.0 s' │ '2.4 s' │ '90 ms'  │ '0' │
│ 5       │ 'student-risk'  │ '/early-warning/students/429'            │ 96          │ 100           │ 100            │ 91  │ '1.9 s' │ '2.4 s' │ '70 ms'  │ '0' │
└─────────┴─────────────────┴──────────────────────────────────────────┴─────────────┴───────────────┴────────────────┴─────┴─────────┴─────────┴──────────┴─────┘
Lighthouse 13.5.0, form factor: mobile
Below target (90): dashboard
[exit 1]
```

Lighthouse: accessibility 100 on all six pages; performance 92-96 on login, students, attendance, early-warning list and student panel; the dashboard scores 82 (TBT ~620 ms), below the 90 target. Profiling (Chromium, 4x CPU throttling) attributes the difference to Recharts rendering the above-the-fold chart (~0.7 s self time in the Recharts chunk plus React work it triggers through useSyncExternalStore, which React cannot time-slice). Mitigations kept: charts lazy-loaded, rendered only near the viewport inside a transition, animations off, explicit tick intervals, measured width instead of ResponsiveContainer (student panel rose from 81 to 96). A bare chart without tooltip/grid still scored 78-86, so the remaining gap is the library's baseline cost; recorded as a deviation. Real issues found and fixed in this milestone: (1) the API client never consumed the body of a failed refresh / retried 401, leaving requests open (network never idle, Lighthouse load timeouts) — fixed and covered by a unit test; (2) Recharts' focusable SVG inside aria-hidden; (3) dark-mode primary button contrast; (4) 'Late' chip contrast; (5) keyboard-inaccessible scroll regions; (6) duplicate CSP / Cache-Control headers from nginx. An earlier ad-hoc Lighthouse helper was invalid because Git Bash rewrote '/' arguments into Windows paths; those numbers were discarded and all reported figures come from scripts/lighthouse.mjs.

## M8 — Docs + release (2026-10-25)

Scope: README (purpose, screenshots, Mermaid architecture diagram, Docker quickstart, demo logins marked demo-only, API docs links, ML summary with numbers from the run record, limitations), docs/case_study.md, 18 Playwright screenshots (desktop 1440 px and mobile 375 px, light and dark) in docs/screenshots/ generated from the freshly reseeded synthetic database, MIT LICENSE (Jaswant Raj, 2026), NOTICE.md with CC BY 4.0 dataset attribution.

### Gate output (scripts/gate.sh --e2e)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
77 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 76 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 43%]

........................................................................ [ 86%]

......................                                                   [100%]

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

app\core\logging.py                35      1     10      1    96%   28

app\seed.py                       206      3     62      2    98%   182-183, 452

app\services\auth.py               49      1     14      2    95%   41, 92->exit

app\services\csv_io.py            115      1     42      3    97%   55->57, 57->59, 89

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2647     10    442     22    99%



39 files skipped due to complete coverage.

166 passed in 91.19s (0:01:31)

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
16 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 14 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
...................                                                      [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       21      0      0      0   100%

edupulse_ml\report.py         34      0     14      1    98%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         135      1     22      2    98%

------------------------------------------------------------

TOTAL                        355     30     84      5    91%

19 passed in 67.65s (0:01:07)

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

Not implemented: navigation to another Document

 Test Files  8 passed (8)
      Tests  39 passed (39)
   Start at  20:09:45
   Duration  6.80s (environment 54%, tests 25%, import 9%, setup 9%, transform 2%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 780 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-r9nMhY3h.css              38.25 kB │ gzip:   7.81 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-D8vtpeqI.js              0.51 kB │ gzip:   0.27 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/DeferredRender-CGSRHVuI.js       0.61 kB │ gzip:   0.38 kB
dist/assets/ClassPicker-CnXwr14W.js          0.66 kB │ gzip:   0.41 kB
dist/assets/format-DqLuBCE3.js               0.66 kB │ gzip:   0.44 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-DUfLLxzb.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-CGeTjuvy.js            1.98 kB │ gzip:   1.02 kB
dist/assets/AuditLogPage-E76Bxo7n.js         2.04 kB │ gzip:   1.04 kB
dist/assets/ListToolbar-CwzkzizX.js          2.06 kB │ gzip:   0.94 kB
dist/assets/useMutation-CPh81u1u.js          2.32 kB │ gzip:   0.97 kB
dist/assets/RiskParts-BdheHJRv.js            2.59 kB │ gzip:   0.97 kB
dist/assets/ClassesPage-D43GoEgN.js          2.79 kB │ gzip:   1.32 kB
dist/assets/DashboardPage-iZphQuxR.js        2.99 kB │ gzip:   1.24 kB
dist/assets/CsvImportDialog-CustKNbb.js      3.07 kB │ gzip:   1.32 kB
dist/assets/DataTable-iyqIzl6l.js            3.21 kB │ gzip:   1.23 kB
dist/assets/StudentsListPage-URdAojF8.js     3.24 kB │ gzip:   1.48 kB
dist/assets/RiskListPage-DlkQftTd.js         3.56 kB │ gzip:   1.71 kB
dist/assets/ClassDetailPage-BdDe4LZ9.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-ClizUYX2.js            4.67 kB │ gzip:   1.97 kB
dist/assets/TeachersPage-CGJQmGEl.js         4.86 kB │ gzip:   2.02 kB
dist/assets/AttendancePage-C6co3xBa.js       4.91 kB │ gzip:   1.99 kB
dist/assets/StudentDetailPage-CC5Lte0Q.js    5.14 kB │ gzip:   1.91 kB
dist/assets/StudentForm-C9gakEZh.js          5.97 kB │ gzip:   2.22 kB
dist/assets/StudentRiskPage-BycqRfBw.js      6.14 kB │ gzip:   2.26 kB
dist/assets/RiskTrendCharts-oHxtjvnt.js      6.55 kB │ gzip:   2.75 kB
dist/assets/GradesPage-BhRi_vq4.js           7.00 kB │ gzip:   2.69 kB
dist/assets/useQuery-B86WbdLh.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/DashboardCharts-BKet6WYV.js     24.30 kB │ gzip:   8.17 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/useElementWidth-MynoTyFU.js    347.70 kB │ gzip: 101.49 kB
dist/assets/index-DOKzYCNu.js              352.85 kB │ gzip: 110.93 kB

✓ built in 708ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 10 tests using 1 worker

(node:13828) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 32 rules passed; violations: none
[axe] light students: 38 rules passed; violations: none
[axe] light student detail: 42 rules passed; violations: none
[axe] light student form: 35 rules passed; violations: none
[axe] light teachers: 39 rules passed; violations: none
[axe] light staff: 39 rules passed; violations: none
[axe] light classes: 36 rules passed; violations: none
[axe] light class detail: 34 rules passed; violations: none
[axe] light attendance: 36 rules passed; violations: none
[axe] light grades: 36 rules passed; violations: none
[axe] light early warning: 42 rules passed; violations: none
[axe] light student risk: 39 rules passed; violations: none
[axe] light audit log: 38 rules passed; violations: none
  ok  1 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (35.5s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 32 rules passed; violations: none
[axe] dark students: 38 rules passed; violations: none
[axe] dark student detail: 42 rules passed; violations: none
[axe] dark student form: 35 rules passed; violations: none
[axe] dark teachers: 39 rules passed; violations: none
[axe] dark staff: 39 rules passed; violations: none
[axe] dark classes: 36 rules passed; violations: none
[axe] dark class detail: 34 rules passed; violations: none
[axe] dark attendance: 36 rules passed; violations: none
[axe] dark grades: 36 rules passed; violations: none
[axe] dark early warning: 42 rules passed; violations: none
[axe] dark student risk: 39 rules passed; violations: none
[axe] dark audit log: 38 rules passed; violations: none
  ok  2 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (34.2s)
  ok  3 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.0s)
  ok  4 [mobile-375] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (7.2s)
  -   5 [mobile-375] › e2e\screenshots.spec.ts:28:1 › documentation screenshots
(node:20312) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 30 rules passed; violations: none
[axe] light students: 37 rules passed; violations: none
[axe] light student detail: 40 rules passed; violations: none
[axe] light student form: 33 rules passed; violations: none
[axe] light teachers: 38 rules passed; violations: none
[axe] light staff: 38 rules passed; violations: none
[axe] light classes: 34 rules passed; violations: none
[axe] light class detail: 32 rules passed; violations: none
[axe] light attendance: 34 rules passed; violations: none
[axe] light grades: 34 rules passed; violations: none
[axe] light early warning: 41 rules passed; violations: none
[axe] light student risk: 38 rules passed; violations: none
[axe] light audit log: 37 rules passed; violations: none
  ok  6 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (33.5s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 30 rules passed; violations: none
[axe] dark students: 37 rules passed; violations: none
[axe] dark student detail: 40 rules passed; violations: none
[axe] dark student form: 33 rules passed; violations: none
[axe] dark teachers: 38 rules passed; violations: none
[axe] dark staff: 38 rules passed; violations: none
[axe] dark classes: 34 rules passed; violations: none
[axe] dark class detail: 32 rules passed; violations: none
[axe] dark attendance: 34 rules passed; violations: none
[axe] dark grades: 34 rules passed; violations: none
[axe] dark early warning: 41 rules passed; violations: none
[axe] dark student risk: 38 rules passed; violations: none
[axe] dark audit log: 37 rules passed; violations: none
  ok  7 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (33.5s)
  ok  8 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.6s)
  ok  9 [desktop-1440] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (7.2s)
  -  10 [desktop-1440] › e2e\screenshots.spec.ts:28:1 › documentation screenshots

  2 skipped
  8 passed (2.8m)
[exit 0]

GATE RESULT: PASS
```

### Screenshots (SCREENSHOTS=1 E2E_BASE_URL=http://127.0.0.1:8088 npx playwright test e2e/screenshots.spec.ts)

```text
desktop-attendance.png 89580 bytes
desktop-dashboard-dark.png 62710 bytes
desktop-dashboard.png 62320 bytes
desktop-early-warning.png 273055 bytes
desktop-grades.png 70377 bytes
desktop-login.png 19124 bytes
desktop-student-risk-dark.png 107369 bytes
desktop-student-risk.png 110961 bytes
desktop-students.png 100634 bytes
mobile-attendance.png 36800 bytes
mobile-dashboard-dark.png 34758 bytes
mobile-dashboard.png 34831 bytes
mobile-early-warning.png 38578 bytes
mobile-grades.png 35381 bytes
mobile-login.png 14945 bytes
mobile-student-risk-dark.png 43708 bytes
mobile-student-risk.png 42916 bytes
mobile-students.png 29638 bytes
```

The '2 skipped' Playwright entries are e2e/screenshots.spec.ts, a documentation generator that only runs with SCREENSHOTS=1 (it asserts nothing about behaviour); no test was skipped or weakened. All screenshot files are below 300 KB (privacy scan threshold 1 MB).

## M9 — Publish (2026-10-25)

Scope: History privacy scan (scanner self-tested on planted findings first), private GitHub repository jaswantraj969/edupulse, CI to green, final gate, v1.0.0 tag and release, final report. Not made public.

### Privacy scan of the full git history

```text
$ python scripts/privacy_scan.py --term <local username> --term <personal e-mail> --term <personal e-mail local part> --term <local folder name>
commits scanned: 10
file versions scanned: 294
runtime terms checked: 4 (values not printed)
RESULT: no findings
[exit 0]

$ python scripts/privacy_scan.py --term <POSTGRES_PASSWORD> --term <EDUPULSE_JWT_SECRET> --term <EDUPULSE_DEMO_PASSWORD>   # values from the local .env
commits scanned: 10
file versions scanned: 294
runtime terms checked: 3 (values not printed)
RESULT: no findings
[exit 0]

$ git ls-files | grep -iE "(^|/)\.env$"
[exit 1 — 1 means no match]

$ git config --local user.email
214715227+jaswantraj969@users.noreply.github.com
```

### GitHub CI

```text
$ gh run view 40205988018 --json conclusion,jobs   # first CI run (commit 6818def)
failure 6818def
  backend: success
  dependency-audit: failure
  ml: failure
  frontend: success
  backend-postgres: success
  e2e: success

$ gh run view 40206393249 --json conclusion,jobs   # after fixes (commit c1a824a)
success https://github.com/jaswantraj969/edupulse/actions/runs/40206393249 c1a824a
  backend: success
  dependency-audit: success
  ml: success
  frontend: success
  backend-postgres: success
  e2e: success

$ gh repo view jaswantraj969/edupulse --json visibility
PRIVATE
```

### Final local gate on the release code (commit c1a824a)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
77 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 76 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 43%]

........................................................................ [ 86%]

......................                                                   [100%]

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

app\core\logging.py                35      1     10      1    96%   28

app\seed.py                       206      3     62      2    98%   182-183, 452

app\services\auth.py               49      1     14      2    95%   41, 92->exit

app\services\csv_io.py            115      1     42      3    97%   55->57, 57->59, 89

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2647     10    442     22    99%



39 files skipped due to complete coverage.

166 passed in 51.09s

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
16 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 14 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
...................                                                      [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       21      0      0      0   100%

edupulse_ml\report.py         34      0     14      1    98%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         135      1     22      2    98%

------------------------------------------------------------

TOTAL                        355     30     84      5    91%

19 passed in 35.64s

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

Not implemented: navigation to another Document

 Test Files  8 passed (8)
      Tests  39 passed (39)
   Start at  20:36:32
   Duration  7.90s (environment 59%, tests 20%, setup 10%, import 8%, transform 1%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 780 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-r9nMhY3h.css              38.25 kB │ gzip:   7.81 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-D8vtpeqI.js              0.51 kB │ gzip:   0.27 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/DeferredRender-CGSRHVuI.js       0.61 kB │ gzip:   0.38 kB
dist/assets/ClassPicker-CnXwr14W.js          0.66 kB │ gzip:   0.41 kB
dist/assets/format-DqLuBCE3.js               0.66 kB │ gzip:   0.44 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-DUfLLxzb.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-CGeTjuvy.js            1.98 kB │ gzip:   1.02 kB
dist/assets/AuditLogPage-E76Bxo7n.js         2.04 kB │ gzip:   1.04 kB
dist/assets/ListToolbar-CwzkzizX.js          2.06 kB │ gzip:   0.94 kB
dist/assets/useMutation-CPh81u1u.js          2.32 kB │ gzip:   0.97 kB
dist/assets/RiskParts-BdheHJRv.js            2.59 kB │ gzip:   0.97 kB
dist/assets/ClassesPage-D43GoEgN.js          2.79 kB │ gzip:   1.32 kB
dist/assets/DashboardPage-iZphQuxR.js        2.99 kB │ gzip:   1.24 kB
dist/assets/CsvImportDialog-CustKNbb.js      3.07 kB │ gzip:   1.32 kB
dist/assets/DataTable-iyqIzl6l.js            3.21 kB │ gzip:   1.23 kB
dist/assets/StudentsListPage-URdAojF8.js     3.24 kB │ gzip:   1.48 kB
dist/assets/RiskListPage-DlkQftTd.js         3.56 kB │ gzip:   1.71 kB
dist/assets/ClassDetailPage-BdDe4LZ9.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-ClizUYX2.js            4.67 kB │ gzip:   1.97 kB
dist/assets/TeachersPage-CGJQmGEl.js         4.86 kB │ gzip:   2.02 kB
dist/assets/AttendancePage-C6co3xBa.js       4.91 kB │ gzip:   1.99 kB
dist/assets/StudentDetailPage-CC5Lte0Q.js    5.14 kB │ gzip:   1.91 kB
dist/assets/StudentForm-C9gakEZh.js          5.97 kB │ gzip:   2.22 kB
dist/assets/StudentRiskPage-BycqRfBw.js      6.14 kB │ gzip:   2.26 kB
dist/assets/RiskTrendCharts-oHxtjvnt.js      6.55 kB │ gzip:   2.75 kB
dist/assets/GradesPage-BhRi_vq4.js           7.00 kB │ gzip:   2.69 kB
dist/assets/useQuery-B86WbdLh.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/DashboardCharts-BKet6WYV.js     24.30 kB │ gzip:   8.17 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/useElementWidth-MynoTyFU.js    347.70 kB │ gzip: 101.49 kB
dist/assets/index-DOKzYCNu.js              352.85 kB │ gzip: 110.93 kB

✓ built in 760ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 10 tests using 1 worker

(node:19860) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 32 rules passed; violations: none
[axe] light students: 38 rules passed; violations: none
[axe] light student detail: 42 rules passed; violations: none
[axe] light student form: 35 rules passed; violations: none
[axe] light teachers: 39 rules passed; violations: none
[axe] light staff: 39 rules passed; violations: none
[axe] light classes: 36 rules passed; violations: none
[axe] light class detail: 34 rules passed; violations: none
[axe] light attendance: 36 rules passed; violations: none
[axe] light grades: 36 rules passed; violations: none
[axe] light early warning: 42 rules passed; violations: none
[axe] light student risk: 39 rules passed; violations: none
[axe] light audit log: 38 rules passed; violations: none
  ok  1 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (34.5s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 32 rules passed; violations: none
[axe] dark students: 38 rules passed; violations: none
[axe] dark student detail: 42 rules passed; violations: none
[axe] dark student form: 35 rules passed; violations: none
[axe] dark teachers: 39 rules passed; violations: none
[axe] dark staff: 39 rules passed; violations: none
[axe] dark classes: 36 rules passed; violations: none
[axe] dark class detail: 34 rules passed; violations: none
[axe] dark attendance: 36 rules passed; violations: none
[axe] dark grades: 36 rules passed; violations: none
[axe] dark early warning: 42 rules passed; violations: none
[axe] dark student risk: 39 rules passed; violations: none
[axe] dark audit log: 38 rules passed; violations: none
  ok  2 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (33.3s)
  ok  3 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.0s)
  ok  4 [mobile-375] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (7.3s)
  -   5 [mobile-375] › e2e\screenshots.spec.ts:28:1 › documentation screenshots
(node:18240) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 30 rules passed; violations: none
[axe] light students: 37 rules passed; violations: none
[axe] light student detail: 40 rules passed; violations: none
[axe] light student form: 33 rules passed; violations: none
[axe] light teachers: 38 rules passed; violations: none
[axe] light staff: 38 rules passed; violations: none
[axe] light classes: 34 rules passed; violations: none
[axe] light class detail: 32 rules passed; violations: none
[axe] light attendance: 34 rules passed; violations: none
[axe] light grades: 34 rules passed; violations: none
[axe] light early warning: 41 rules passed; violations: none
[axe] light student risk: 38 rules passed; violations: none
[axe] light audit log: 37 rules passed; violations: none
  ok  6 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (33.5s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 30 rules passed; violations: none
[axe] dark students: 37 rules passed; violations: none
[axe] dark student detail: 40 rules passed; violations: none
[axe] dark student form: 33 rules passed; violations: none
[axe] dark teachers: 38 rules passed; violations: none
[axe] dark staff: 38 rules passed; violations: none
[axe] dark classes: 34 rules passed; violations: none
[axe] dark class detail: 32 rules passed; violations: none
[axe] dark attendance: 34 rules passed; violations: none
[axe] dark grades: 34 rules passed; violations: none
[axe] dark early warning: 41 rules passed; violations: none
[axe] dark student risk: 38 rules passed; violations: none
[axe] dark audit log: 37 rules passed; violations: none
  ok  7 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (33.4s)
  ok  8 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (5.6s)
  ok  9 [desktop-1440] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (6.7s)
  -  10 [desktop-1440] › e2e\screenshots.spec.ts:28:1 › documentation screenshots

  2 skipped
  8 passed (2.8m)
[exit 0]

GATE RESULT: PASS
```

First CI run failures and fixes: (1) dependency-audit — scripts/*.sh lacked the executable bit in git (Windows checkout); fixed with git update-index --chmod=+x. (2) ml reproduction — Linux reproduced the logistic-regression CV means within ~2e-5 of the Windows values (0.803047 vs 0.803069); chosen model, thresholds and all test metrics matched. The tolerance (1e-6) was stricter than the published precision; it is now 5e-4 (half of the last published digit), so every published 3-decimal number must still reproduce. The privacy-scan commit was amended once before the first push (its doc spelled out a path pattern literally); nothing had been pushed at that point.

## T-R1 — Supervisor review: ML validity, feature mapping, security fixes (2026-10-25)

Scope: A1 split audit (both UCI files; 366 identity groups span both; 0 crossings of holdout and of all 15 CV folds; no run discarded), A2 prediction moment stated as 'after first-period grades' + pre-term variant with CIs, A3 input justification (no private-life/family inputs ever), A4 app mapping incl. what demo students get + test-set permutation importance (100 % app-computable), A5 fairness wording 'inconclusive / not evidence of fairness'; holdout guard; B1 CSV-injection tests for all prefixes incl. risk export; B2 refresh token cookie-only (httpOnly, Secure by default, SameSite=Strict), removed from JSON bodies; B3 startup/seed refusals; B4 dashboard chart loading measured, not kept.

### ML evidence

```text
$ (cd ml && uv run python -m edupulse_ml.train) -> ml/reports/run_record.md (excerpt: split audit, pre-term variant, permutation importance, fairness)
## Fairness check by sex (chosen model, high threshold)

Sex is not a model input; it is used here only to compare error rates. With these group
sizes the result is **inconclusive and is not evidence of fairness**.

| Set | Group | n | Positives | Recall | Precision | Flag rate |
|---|---|---|---|---|---|---|
| test | F | 128 | 30 | 0.833 [0.682, 0.952] | 0.641 [0.484, 0.780] | 0.305 [0.225, 0.387] |
| test | M | 81 | 16 | 0.750 [0.500, 0.945] | 0.600 [0.353, 0.812] | 0.247 [0.148, 0.358] |
| test | gap F-M | | | +0.083 | +0.041 | +0.058 |
| out_of_fold | F | 463 | 95 | 0.832 [0.755, 0.901] | 0.669 [0.585, 0.752] | 0.255 [0.215, 0.294] |
| out_of_fold | M | 372 | 89 | 0.775 [0.685, 0.854] | 0.657 [0.560, 0.752] | 0.282 [0.232, 0.334] |
| out_of_fold | gap F-M | | | +0.056 | +0.012 | -0.027 |

## Split audit (students in both course files)

- Identity attributes used for matching: 13.
- Rows produced by the dataset documentation's merge on them: 382.
- Identity groups: 662; groups with rows in both files: 366 (74 in the test set); groups with more than two rows (attribute collisions, kept together): 9.
- Groups on both sides of the holdout: **0**; on both sides of any CV fold: **0** (checked for all 15 folds).

Holdout access log: freeze: chosen, t_high, t_medium, t_pre_term → score: dummy_prior → score: logistic_regression → score: gradient_boosting → score: pre_term.

## Pre-term variant (no period grades)

Same model family, inputs absences, failures; own threshold 0.148 (80 % out-of-fold recall); test scored once.

| Model | CV average precision | Test AP | Test ROC AUC | Precision @ t | Recall @ t |
|---|---|---|---|---|---|
| After first-period grades (deployed) | 0.803 ± 0.057 | 0.817 [0.705, 0.901] | 0.936 [0.900, 0.966] | 0.627 [0.500, 0.740] | 0.804 [0.674, 0.915] |
| Pre-term (no grades) | 0.470 ± 0.058 | 0.489 [0.361, 0.646] | 0.702 [0.599, 0.792] | 0.233 [0.167, 0.299] | 0.804 [0.684, 0.915] |

## Permutation importance on the test set (deployed model; descriptive only)

| Feature | Mean drop in AP | SD | Share | Computable by EduPulse |
|---|---|---|---|---|
| g1 | 0.564 | 0.034 | 96.8% | yes |
| absences | 0.008 | 0.010 | 1.4% | yes |
| failures | 0.010 | 0.005 | 1.8% | yes |


$ comparison with the committed M5 run (python, metrics.json before/after)
chosen model: logistic_regression -> logistic_regression; thresholds identical (0.315 / 0.134); test AP 0.8168440003250651 -> 0.8168440003250651; model file SHA-256 identical
```

### B2/B3 evidence on the Docker build

```text
$ docker compose run --rm --no-deps -e EDUPULSE_JWT_SECRET='' api python -c 'import app.main'
RuntimeError: EDUPULSE_JWT_SECRET is not set
[exit 1]
$ docker compose run --rm --no-deps -e EDUPULSE_JWT_SECRET='change-me' api python -c 'import app.main'
Value error, EDUPULSE_JWT_SECRET is a placeholder value; generate a random one [type=value_error, input_value='change-me', input_type=str]
[exit 1]
$ docker compose run --rm --no-deps -e EDUPULSE_JWT_SECRET='short-secret-31-characters-long' api python -c 'import app.main'
Value error, EDUPULSE_JWT_SECRET must be at least 32 bytes [type=value_error, input_value='short-secret-31-characters-long', input_type=str]
[exit 1]
$ docker compose exec -T -e EDUPULSE_DEMO_PASSWORD='' api python -m app.seed --reset
Set EDUPULSE_DEMO_PASSWORD (see .env.example); refusing to seed.
[exit 1]
$ docker compose exec -T -e EDUPULSE_DEMO_PASSWORD='change-me' api python -m app.seed --reset
EDUPULSE_DEMO_PASSWORD is a default value; choose your own.
[exit 1]
$ curl -s -D - -o /dev/null -X POST http://127.0.0.1:8088/api/v1/auth/login -d "username=admin@edupulse.example&password=<demo>" | grep -i set-cookie   # + body keys
set-cookie: edupulse_refresh=<redacted>; HttpOnly; Max-Age=604800; Path=/api/v1/auth; SameSite=strict; Secure
body keys: ['access_token', 'expires_in', 'token_type']
```

### B4: dashboard Lighthouse (mobile), 3 runs per variant, Docker build

```text
| Variant | Performance (3 runs) | Median | TBT (3 runs) |
|---|---|---|---|
| eager import (no lazy, no deferral) | 79, 78, 79 | 79 | 520 ms, 560 ms, 530 ms |
| lazy chunk only | 80, 82, 76 | 80 | 700 ms, 630 ms, 650 ms |
| lazy + render near viewport (current) | 87, 84, 84 | 84 | 420 ms, 530 ms, 540 ms |
```

### Lighthouse after T-R1 (all audited pages)

```text
$ (cd frontend && node scripts/lighthouse.mjs)   # Docker build, final code
┌─────────┬─────────────────┬──────────────────────────────────────────┬─────────────┬───────────────┬────────────────┬─────┬─────────┬─────────┬──────────┬─────┐
│ (index) │ page            │ path                                     │ performance │ accessibility │ best_practices │ seo │ fcp     │ lcp     │ tbt      │ cls │
├─────────┼─────────────────┼──────────────────────────────────────────┼─────────────┼───────────────┼────────────────┼─────┼─────────┼─────────┼──────────┼─────┤
│ 0       │ 'login'         │ '/login'                                 │ 96          │ 100           │ 92             │ 91  │ '2.1 s' │ '2.5 s' │ '50 ms'  │ '0' │
│ 1       │ 'dashboard'     │ '/'                                      │ 76          │ 100           │ 100            │ 91  │ '2.3 s' │ '2.9 s' │ '630 ms' │ '0' │
│ 2       │ 'students'      │ '/students'                              │ 97          │ 100           │ 100            │ 91  │ '1.9 s' │ '2.1 s' │ '80 ms'  │ '0' │
│ 3       │ 'attendance'    │ '/attendance?class_id=1&date=2025-10-07' │ 96          │ 100           │ 96             │ 91  │ '2.0 s' │ '2.2 s' │ '110 ms' │ '0' │
│ 4       │ 'early-warning' │ '/early-warning?class_id=1'              │ 97          │ 100           │ 96             │ 91  │ '1.9 s' │ '2.4 s' │ '40 ms'  │ '0' │
│ 5       │ 'student-risk'  │ '/early-warning/students/429'            │ 97          │ 100           │ 100            │ 91  │ '1.9 s' │ '2.4 s' │ '50 ms'  │ '0' │
└─────────┴─────────────────┴──────────────────────────────────────────┴─────────────┴───────────────┴────────────────┴─────┴─────────┴─────────┴──────────┴─────┘
Lighthouse 13.5.0, form factor: mobile
Below target (90): dashboard
[exit 1]
```

### Gate output (scripts/gate.sh --e2e)

```text
$ (cd backend && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd backend && uv run ruff format --check .)
77 files already formatted
[exit 0]

$ (cd backend && uv run mypy app tests)
Success: no issues found in 76 source files

[exit 0]

$ (cd backend && uv run pytest --cov --cov-report=term-missing -p no:cacheprovider)
........................................................................ [ 39%]

........................................................................ [ 79%]

......................................                                   [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                            Stmts   Miss Branch BrPart  Cover   Missing

---------------------------------------------------------------------------

app\api\routes\assessments.py     130      1     42      2    98%   63, 177->176

app\api\routes\auth.py             76      0     18      1    99%   151->157

app\api\routes\catalog.py          42      0      4      1    98%   44->46

app\api\routes\classes.py         152      0     40      1    99%   163->167

app\api\routes\dashboard.py        55      0     20      3    96%   51->53, 73->75, 100->99

app\api\routes\staff.py            64      0      6      3    96%   67->69, 69->71, 71->73

app\api\routes\students.py        133      1     24      1    99%   89

app\core\logging.py                35      1     10      1    96%   28

app\seed.py                       208      3     64      2    98%   181-182, 464

app\services\auth.py               49      1     14      2    95%   41, 92->exit

app\services\csv_io.py            115      1     42      3    97%   55->57, 57->59, 89

app\services\risk.py              150      2     30      2    98%   136, 214

---------------------------------------------------------------------------

TOTAL                            2653     10    446     22    99%



39 files skipped due to complete coverage.

182 passed in 81.14s (0:01:21)

[exit 0]

$ (cd ml && uv run ruff check .)
All checks passed!
[exit 0]

$ (cd ml && uv run ruff format --check .)
18 files already formatted
[exit 0]

$ (cd ml && uv run mypy edupulse_ml tests)
Success: no issues found in 16 source files

[exit 0]

$ (cd ml && uv run pytest --cov -p no:cacheprovider)
.......................                                                  [100%]

=============================== tests coverage ================================

______________ coverage: platform win32, python 3.12.13-final-0 _______________



Name                       Stmts   Miss Branch BrPart  Cover

------------------------------------------------------------

edupulse_ml\__init__.py        1      0      0      0   100%

edupulse_ml\data.py           57      5     18      1    89%

edupulse_ml\evaluate.py       45      1     12      1    96%

edupulse_ml\explain.py        17      0      2      0   100%

edupulse_ml\export.py         14     14      2      0     0%

edupulse_ml\features.py       23      0      0      0   100%

edupulse_ml\guard.py          33      0      8      0   100%

edupulse_ml\report.py         49      0     24      1    99%

edupulse_ml\reproduce.py      31      9     14      0    76%

edupulse_ml\train.py         164      1     22      2    98%

------------------------------------------------------------

TOTAL                        434     30    102      5    92%

23 passed in 96.61s (0:01:36)

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

Not implemented: navigation to another Document

 Test Files  8 passed (8)
      Tests  39 passed (39)
   Start at  22:06:56
   Duration  7.40s (environment 59%, tests 21%, setup 9%, import 8%, transform 1%, worker 1%)

[exit 0]

$ (cd frontend && npm run build)

> edupulse-web@0.1.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 780 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.61 kB │ gzip:   0.36 kB
dist/assets/index-r9nMhY3h.css              38.25 kB │ gzip:   7.81 kB
dist/assets/coerce-CHtFiwVw.js               0.09 kB │ gzip:   0.10 kB
dist/assets/queries-mGl7_x1x.js              0.51 kB │ gzip:   0.26 kB
dist/assets/classSchema-D5ATFxNC.js          0.57 kB │ gzip:   0.33 kB
dist/assets/ClassPicker-B7vl99eI.js          0.66 kB │ gzip:   0.41 kB
dist/assets/format-DqLuBCE3.js               0.66 kB │ gzip:   0.44 kB
dist/assets/schemas-sqRQT-v-.js              0.93 kB │ gzip:   0.48 kB
dist/assets/RecordFormDialog-134_xAPz.js     1.83 kB │ gzip:   0.98 kB
dist/assets/LoginPage-CmOEbiMt.js            1.98 kB │ gzip:   1.02 kB
dist/assets/AuditLogPage-BhNVoCQl.js         2.04 kB │ gzip:   1.04 kB
dist/assets/ListToolbar-B8TBbfPo.js          2.06 kB │ gzip:   0.94 kB
dist/assets/useMutation-C2yr09Gz.js          2.32 kB │ gzip:   0.97 kB
dist/assets/RiskParts-DAa7O2FQ.js            2.59 kB │ gzip:   0.97 kB
dist/assets/ClassesPage-BZ5NlxSf.js          2.79 kB │ gzip:   1.32 kB
dist/assets/CsvImportDialog-D_o-4iy4.js      3.07 kB │ gzip:   1.32 kB
dist/assets/DataTable-Ct2HILfY.js            3.21 kB │ gzip:   1.23 kB
dist/assets/StudentsListPage-CdrzHIUS.js     3.24 kB │ gzip:   1.48 kB
dist/assets/RiskListPage-C9dcHwLy.js         3.58 kB │ gzip:   1.72 kB
dist/assets/ClassDetailPage-Dgg9iAJ4.js      4.61 kB │ gzip:   1.81 kB
dist/assets/StaffPage-Dd-4gVLc.js            4.67 kB │ gzip:   1.98 kB
dist/assets/TeachersPage-Da5H8BO5.js         4.86 kB │ gzip:   2.02 kB
dist/assets/AttendancePage-CJ5ezVsJ.js       4.91 kB │ gzip:   2.00 kB
dist/assets/StudentDetailPage-DL19yS0g.js    5.14 kB │ gzip:   1.91 kB
dist/assets/StudentForm-a-28p3Vh.js          5.97 kB │ gzip:   2.22 kB
dist/assets/RiskTrendCharts-Utx5FNQY.js      6.55 kB │ gzip:   2.75 kB
dist/assets/StudentRiskPage-CI0UKkEG.js      6.64 kB │ gzip:   2.48 kB
dist/assets/GradesPage-pXT_LqYe.js           7.00 kB │ gzip:   2.70 kB
dist/assets/useQuery-CvzSKuG7.js             7.97 kB │ gzip:   2.94 kB
dist/assets/jsx-runtime-Wy9s6hX0.js          8.91 kB │ gzip:   3.39 kB
dist/assets/DashboardPage-C6rBnFbb.js       26.35 kB │ gzip:   8.85 kB
dist/assets/Field-BARBEQsd.js              124.54 kB │ gzip:  37.53 kB
dist/assets/useElementWidth-j6cjnRRa.js    347.70 kB │ gzip: 101.49 kB
dist/assets/index-Cq4T2w61.js              352.85 kB │ gzip: 110.93 kB

✓ built in 731ms
[exit 0]

$ (cd frontend && npx playwright test --reporter=list)

Running 10 tests using 1 worker

(node:10284) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 31 rules passed; violations: none
[axe] light students: 38 rules passed; violations: none
[axe] light student detail: 42 rules passed; violations: none
[axe] light student form: 35 rules passed; violations: none
[axe] light teachers: 39 rules passed; violations: none
[axe] light staff: 39 rules passed; violations: none
[axe] light classes: 36 rules passed; violations: none
[axe] light class detail: 34 rules passed; violations: none
[axe] light attendance: 36 rules passed; violations: none
[axe] light grades: 36 rules passed; violations: none
[axe] light early warning: 42 rules passed; violations: none
[axe] light student risk: 39 rules passed; violations: none
[axe] light audit log: 38 rules passed; violations: none
  ok  1 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (32.6s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 31 rules passed; violations: none
[axe] dark students: 38 rules passed; violations: none
[axe] dark student detail: 42 rules passed; violations: none
[axe] dark student form: 35 rules passed; violations: none
[axe] dark teachers: 39 rules passed; violations: none
[axe] dark staff: 39 rules passed; violations: none
[axe] dark classes: 36 rules passed; violations: none
[axe] dark class detail: 34 rules passed; violations: none
[axe] dark attendance: 36 rules passed; violations: none
[axe] dark grades: 36 rules passed; violations: none
[axe] dark early warning: 42 rules passed; violations: none
[axe] dark student risk: 39 rules passed; violations: none
[axe] dark audit log: 38 rules passed; violations: none
  ok  2 [mobile-375] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (32.6s)
  ok  3 [mobile-375] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (4.8s)
  ok  4 [mobile-375] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (6.1s)
  -   5 [mobile-375] › e2e\screenshots.spec.ts:28:1 › documentation screenshots
(node:3472) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
[axe] light login: 29 rules passed; violations: none
[axe] light dashboard: 29 rules passed; violations: none
[axe] light students: 37 rules passed; violations: none
[axe] light student detail: 40 rules passed; violations: none
[axe] light student form: 33 rules passed; violations: none
[axe] light teachers: 38 rules passed; violations: none
[axe] light staff: 38 rules passed; violations: none
[axe] light classes: 34 rules passed; violations: none
[axe] light class detail: 32 rules passed; violations: none
[axe] light attendance: 34 rules passed; violations: none
[axe] light grades: 34 rules passed; violations: none
[axe] light early warning: 41 rules passed; violations: none
[axe] light student risk: 38 rules passed; violations: none
[axe] light audit log: 37 rules passed; violations: none
  ok  6 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (light mode) (26.9s)
[axe] dark login: 29 rules passed; violations: none
[axe] dark dashboard: 29 rules passed; violations: none
[axe] dark students: 37 rules passed; violations: none
[axe] dark student detail: 40 rules passed; violations: none
[axe] dark student form: 33 rules passed; violations: none
[axe] dark teachers: 38 rules passed; violations: none
[axe] dark staff: 38 rules passed; violations: none
[axe] dark classes: 34 rules passed; violations: none
[axe] dark class detail: 32 rules passed; violations: none
[axe] dark attendance: 34 rules passed; violations: none
[axe] dark grades: 34 rules passed; violations: none
[axe] dark early warning: 41 rules passed; violations: none
[axe] dark student risk: 38 rules passed; violations: none
[axe] dark audit log: 37 rules passed; violations: none
  ok  7 [desktop-1440] › e2e\a11y.spec.ts:58:3 › no serious accessibility violations (dark mode) (25.9s)
  ok  8 [desktop-1440] › e2e\core-flow.spec.ts:8:1 › login → add student → mark attendance → enter grade (4.1s)
  ok  9 [desktop-1440] › e2e\early-warning.spec.ts:4:1 › teacher reviews early-warning scores; the views are audited (5.8s)
  -  10 [desktop-1440] › e2e\screenshots.spec.ts:28:1 › documentation screenshots

  2 skipped
  8 passed (2.4m)
[exit 0]

GATE RESULT: PASS
```

Bugs found while doing this review: (1) a rejected refresh never cleared the cookie (the header was set on a response the error handler discarded) — now sent with the error, covered by a test; (2) during the change my first token-reuse test helper did not attach the cookie, so tests passed for the wrong reason — caught by a coverage drop in services/auth.py and fixed (reuse branch covered again); (3) the ML test fixture never shared identities across files, so the new disjointness test could not exercise grouping — fixture fixed (200 shared synthetic students). Documentation correction: '382 students in both files' was the merge row count; 366 identity groups span both files. Counterfactual for A1 (ad-hoc check, not part of the pipeline): an ungrouped stratified split with the same seed would have put 120 shared students on both sides.
