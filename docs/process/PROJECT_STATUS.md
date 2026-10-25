# EduPulse — Project Status

Status values: `not started`, `in progress`, `done`. "Done" means the milestone gate was run and
its output recorded in `REVIEW_PACKET.md`; it is not a claim of external verification.

| Milestone | Status | Commit |
|-----------|--------|--------|
| M0 Skeleton | done | see git log (M0) |
| M1 Data model + migrations | done | see git log (M1) |
| M2 Auth + security | done | see git log (M2) |
| M3 Core API | done | see git log (M3) |
| M4 Frontend core | done | see git log (M4) |
| M5 ML early-warning | done | see git log (M5) |
| M6 ML in the UI | done | see git log (M6) |
| M7 Hardening | done | see git log (M7) |
| M8 Docs + release | done | see git log (M8) |
| M9 Publish | done | see git log (M9); tag v1.0.0 |

## Resume point

T-R2 in progress: absences timing fix (pre-registered in D78). Repository stays private.

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
| D35 | M4 | Access token kept in module memory only; on load the SPA restores the session through `POST /auth/refresh` (cookie); any 401 triggers one shared refresh and a retry, else the user is signed out. | No token in localStorage (XSS exposure); seamless reloads. |
| D36 | M4 | List state (page, sort, search, filters) lives in the URL query string. | Reload-safe, shareable, back-button friendly. |
| D37 | M4 | Data tables render as `<table>` with `aria-sort` on md+ and as a card list below; only one is displayed at a time (`display:none` removes the other from the accessibility tree). | Usable at 360 px without horizontal scrolling. |
| D38 | M4 | Own modal dialog component (portal, `role=dialog`, `aria-modal`, focus trap, Escape, focus restore) used for confirmations, forms and the mobile "More" menu. | Consistent keyboard behaviour; jsdom-testable. |
| D39 | M4 | Routes are code-split with `React.lazy`; Recharts loads only with the dashboard charts. | Smaller first load for mobile (Lighthouse in M7). |
| D40 | M4 | Chart series colours `#4f46e5` (light) / `#6366f1` (dark) validated with the dataviz palette checker against the actual card surfaces; single-series charts, tooltips, and a "Show data table" view. | WCAG non-text contrast ≥ 3:1 and identity never by colour alone. |
| D41 | M4 | Frontend forms validate with Zod mirroring the API rules; server 409/422 field errors are mapped back onto the matching inputs. | Inline feedback without trusting the client. |
| D42 | M4 | Playwright runs serially (one worker) against a seeded API; each run creates a uniquely named student and deletes it at the end. | Repeatable on a shared database. |
| D43 | M5 | Train on both UCI course files (1,044 rows) and group splits by the dataset authors' student-matching attributes, so a student's two rows never straddle train/test. | More data than one file, without identity leakage. |
| D44 | M5 | Model inputs limited to what EduPulse records: Term 1 average (`g1`), absences, prior failures. Age excluded as a protected characteristic (ablation: no AP gain); sex and all family/socioeconomic attributes excluded. | Deployable mapping + privacy/fairness by design. |
| D45 | M5 | Prediction moment = end of Term 1; target = G3 < 10. G2 excluded as later information. | Matches when a school can act and what is known then. |
| D46 | M5 | Candidates: dummy (prior), logistic regression, gradient boosting with fixed conservative settings — no hyper-parameter search. Selection: best mean CV AP, simpler within 0.01. | Avoids overfitting model choice on ~800 rows; rule fixed before testing. |
| D47 | M5 | Bands: high = OOF recall 0.80 threshold; medium = OOF recall 0.95 threshold. | Early warning favours recall; both thresholds come from out-of-fold predictions only. |
| D48 | M5 | Bootstrap CIs resample whole students (cluster bootstrap). | Rows are not independent when a student has two courses. |
| D49 | M5 | Explanations by reference substitution in log-odds (training medians as reference); exact for logistic regression; implemented in ml/ and backend, cross-checked by a backend test against values recorded at training. | SHAP-equivalent for the linear model without an extra dependency. |
| D50 | M5 | Model persisted with joblib; its SHA-256 stored in `model_meta.json` and verified before unpickling; scikit-learn version pinned identically in ml/ and backend/. | Pickle safety and version compatibility. |
| D51 | M5 | App mapping: g1 = weight-averaged Term 1 percentage across subjects ÷ 5; absences = Term 1 "absent" days projected to the year by school-day ratio (excused not counted); students without Term 1 grades are "insufficient data". | Same features from EduPulse data; limitations stated in the model card. |
| D52 | M5 | `EDUPULSE_DEMO_MODE` (default true) adds "Demo — synthetic data" to every risk response. | Scores on synthetic data must never look real. |
| D53 | M5 | CI job re-downloads the dataset, verifies hashes and reproduces the committed metrics within 1e-6. | Published numbers are reproducible, not hand-copied. |
| D54 | M6 | Audit log records every successful risk view (class list, student panel) and export with user id + e-mail copy, action, target, IP and time; written and committed before the response is built; denied requests are not logged as views. Admin-only read API and page. | Accountability for sensitive scores; a request that cannot be logged returns no scores. |
| D55 | M6 | Risk CSV export repeats the decision-support (and demo) notice on every row and uses a `-demo` filename suffix in demo mode. | The caveat travels with the data. |
| D56 | M6 | Risk bands shown as text badges ("High risk"), factors as "↑ Raises / ↓ Lowers" chips plus sentences; trend shown as two single-series charts (attendance rate, average grade) with the prediction moment marked. | Never colour-only; no dual axis. |
| D57 | M6 | "Early warning" is a top-level page; on mobile it lives in the "More" menu with Classes/Teachers. | Keeps the bottom bar to four daily tasks. |
| D58 | M6 | Sign-out records the reason; the auth guard keeps the "return to" location only after session expiry. | The next person on a shared computer does not land on the previous user's page. |
| D59 | M7 | Pure ASGI middlewares for request context (id + JSON access log) and security headers; caller-supplied `X-Request-ID` accepted only if `[A-Za-z0-9._-]{1,64}`. | Correct with streaming responses and context variables; prevents log injection. |
| D60 | M7 | Error bodies carry `request_id`; unhandled exceptions return a generic 500 JSON and are logged with stack traces server-side only. | Supportable without leaking internals. |
| D61 | M7 | `/health` = liveness (no dependencies); `/ready` = database + model hash check, 503 otherwise; Docker Compose waits for the API to be ready before starting the web container. | Standard probe split. |
| D62 | M7 | API responses: `CSP default-src 'none'`, `Cache-Control: no-store`, frame/sniff/referrer/permissions/COOP headers; docs pages get a CSP allowing the Swagger/ReDoc CDN. nginx security headers moved to an include used per location so the API is not double-headed. | Defence in depth without breaking `/docs`. |
| D63 | M7 | Accessibility gate = axe (WCAG 2.0–2.2 A/AA + best practice) on 14 screens in light and dark mode at 375 and 1440 px; any serious/critical violation fails Playwright. | Covers both themes and both layouts. |
| D64 | M7 | Lighthouse runs against the Docker build with the mobile preset; signed-in pages get a fresh refresh-token cookie via `--extra-headers` (file). Script: `frontend/scripts/lighthouse.mjs`. | Measures the shipped artefact, including authenticated screens. |
| D65 | M7 | Charts: lazy chunk, rendered only near the viewport inside a transition, no animations, explicit tick intervals, width measured once (no ResponsiveContainer). Recharts kept. | Best achievable with the specified chart library; see deviation. |
| D66 | M7 | Dependency audits via `scripts/audit_deps.sh` (pip-audit on both uv lock files, npm audit) and a CI job. | Repeatable, recorded. |
| D67 | M8 | Screenshots generated by a Playwright spec against the Docker build after reseeding (deterministic synthetic data), light and dark, 375 and 1440 px; the spec is skipped unless `SCREENSHOTS=1`. | Reproducible documentation images; normal test runs stay fast. |
| D68 | M8 | Demo credentials are documented as "the `EDUPULSE_DEMO_PASSWORD` you set"; no password is committed. | No shared default secret. |
| D69 | M9 | Privacy scanner committed with generic rules; machine-specific terms (username, personal e-mail, folder, secret values) passed at runtime and never printed. | The scan can be repeated and reported without leaking what it looks for. |
| D70 | M9 | Repository created private; `v1.0.0` tagged on the commit containing the final report after CI is green. | Release matches the reviewed state; owner decides on publication. |
| D71 | T-R1 | Every training run records a split audit (identity groups spanning both UCI files, crossings of the holdout and of each CV fold) and fails if any student crosses. | Evidence of disjointness travels with the results (0 crossings; 366 groups span both files). |
| D72 | T-R1 | `HoldoutGuard`: model choice and thresholds are frozen before the test indices can be read; each model can be scored on the holdout once; the access log is published in the run record. | "Test scored once" is enforced by code and tests, not only by convention. |
| D73 | T-R1 | A pre-term variant (absences + failures, no period grades) is evaluated with the same protocol and its own OOF threshold, and reported but not served. | Shows what the first-period grade contributes (test AP 0.489 vs 0.817). |
| D74 | T-R1 | Test-set permutation importance (50 repeats, AP) is reported as descriptive only; no decision depends on it. | Answers "how much of the model the app can compute" (100 %). |
| D75 | T-R1 | Refresh token only in an httpOnly, Secure, SameSite=Strict cookie; removed from login/refresh JSON; `/refresh` and `/logout` read only the cookie; `Secure` on by default; HSTS is a separate `EDUPULSE_HSTS` flag. | Page JavaScript can never read the refresh token; HSTS should not be tied to cookie flags. |
| D76 | T-R1 | API refuses to start if the JWT secret is missing, < 32 bytes or a placeholder; the seed refuses an empty/default demo password (no auto-generated password any more). | Fail closed on unsafe configuration. |
| D77 | T-R1 | B4: dashboard chart loading measured in three variants (3 Lighthouse runs each, Docker build): eager import 79/78/79, lazy chunk 80/82/76, lazy + render near viewport 87/84/84. None reached 90, so per the review rule the dashboard uses the simplest variant (eager import inside the route-split page). | Keep a change only if it meets the target; the +5 median from deferral is recorded should the owner want it back. |
| D78 | T-R2 | **Pre-registration (written and pushed before any T-R2 training run).** Review finding: UCI `absences` is a whole-year count, so it is not known "after first-period grades". The deployed model drops it. New run from a NEW stratified, student-grouped 20 % holdout with seed **20261026** (previous runs used 20251025). Unchanged and fixed in advance: candidates dummy (prior) / logistic regression / gradient boosting (same settings); 3 × repeated grouped 5-fold CV on identical folds; primary metric average precision; selection = best mean CV AP, simpler model within 0.01; thresholds from out-of-fold predictions only (high = 80 % recall, medium = 95 %); test scored once via the holdout guard; 2,000 cluster-bootstrap resamples. Deployed inputs: `g1`, `failures`. Pre-term variant: `failures` only (reported even if near-trivial). Ablations: + age; g1 only. | Removes a feature-timing mismatch; a new holdout because the old one has already been scored. |

## Deviations and limitations

- Login rate-limit state is per API process; a multi-instance deployment would need a shared store (e.g. Redis). (M2)
- Academic years and terms are read-only through the API (created by the seed/migrations); a year-rollover workflow is out of scope. (M3)
- The model is trained on 2005–06 Portuguese data and must be re-validated locally before real use; the app's averaged multi-subject G1 and projected absences are an input shift relative to training (see docs/model_card.md). (M5)
- On the test set, gradient boosting scored slightly higher than the selected logistic regression at the threshold; the pre-registered selection was kept (CIs overlap). (M5)
- **Lighthouse dashboard performance 76–79 (target ≥ 90)** on the simulated mobile profile after T-R1 (B4 attempt best median 84, not kept); other audited pages 96–97, accessibility 100 everywhere. Cause: Recharts render cost for the above-the-fold chart (profiling in REVIEW_PACKET M7). (M7, T-R1)
- ML reproduction check tolerance is 5e-4 (half of the last published digit): Linux and Windows differ around 1e-5 in CV means. (M9)
- Correction (T-R1): earlier docs said "382 students appear in both files"; 382 is the row count of the dataset documentation's merge. EduPulse's grouping has 366 identity groups spanning both files (370 maths rows matched). Splits were grouped from the start, so no result changed.
