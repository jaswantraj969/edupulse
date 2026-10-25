# EduPulse — Final report (v1.0.0)

Prepared for supervisor review. Repository: <https://github.com/jaswantraj969/edupulse>
(**private**; not published). Full command output for every gate is in
[`REVIEW_PACKET.md`](REVIEW_PACKET.md); decisions are in [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

| | |
|---|---|
| CI (green, all jobs) | <https://github.com/jaswantraj969/edupulse/actions/runs/40206393249> |
| Release | <https://github.com/jaswantraj969/edupulse/releases/tag/v1.0.0> |

## Milestones

| Milestone | Status | Commit(s) | Gate |
|---|---|---|---|
| M0 Skeleton | done | `a561d71` | PASS |
| M1 Data model + migrations | done | `8bdb755` | PASS |
| M2 Auth + security | done | `179b281` | PASS |
| M3 Core API | done | `4e93d9f` | PASS |
| M4 Frontend core | done | `a003adc` | PASS (incl. Playwright 375/1440 px) |
| M5 ML early-warning | done | `61a4536` | PASS |
| M6 ML in the UI | done | `7e7709f` | PASS |
| M7 Hardening | done | `3a22169` | PASS (incl. 56 axe scans) |
| M8 Docs + release | done | `931fd1a` | PASS |
| M9 Publish | done | `6818def` (privacy scan), `c1a824a` (CI fixes), final-report commit tagged `v1.0.0` | PASS; CI green |

## Final gate (local, release code `c1a824a`)

Summary of [`REVIEW_PACKET.md` → M9](REVIEW_PACKET.md) (verbatim output there):

| Check | Result |
|---|---|
| Backend: ruff, ruff format, mypy --strict | all passed |
| Backend: pytest | **166 passed**, coverage **99 %** (2,647 statements) |
| ML: ruff, format, mypy --strict, pytest | **19 passed**, coverage 91 % |
| Frontend: ESLint (incl. jsx-a11y), tsc, Vitest | **39 passed** |
| Frontend: production build | OK |
| Playwright (Chromium, 375 px and 1440 px) | **8 passed**: core flow (login → add student → mark attendance → enter grade), early-warning flow with audit check, axe accessibility in light and dark mode; 2 skipped = screenshot generator (runs only with `SCREENSHOTS=1`) |
| axe (WCAG 2.0–2.2 A/AA + best practice) | 56 scans (14 screens × 2 themes × 2 widths), **0 violations of any impact** |

CI on GitHub re-runs all of the above on Linux plus migrations/seed on PostgreSQL 16, the ML
reproduction check (re-downloads the dataset, verifies SHA-256, retrains) and the dependency
audit.

## ML results (copied from [`ml/reports/run_record.md`](../../ml/reports/run_record.md))

Data: UCI Student Performance (DOI 10.24432/C5TG7T, CC BY 4.0); 1044 rows (maths + Portuguese),
662 student groups; 230 fails (22.0 %). Split: 835 train / 209 test rows (46 test positives),
grouped by student. Prediction moment: end of the first grading period (G1 known; G2, G3
unknown). Target: final grade G3 < 10. Features: g1, absences, failures. Chosen model:
**Logistic regression** (best mean CV AP; simpler model preferred within 0.01).

Cross-validation (3x repeated stratified group 5-fold, training part only):

| Model | Average precision | ROC AUC | Brier |
|---|---|---|---|
| Dummy (prior) | 0.220 ± 0.002 | 0.500 ± 0.000 | 0.172 ± 0.001 |
| Logistic regression | 0.803 ± 0.057 | 0.939 ± 0.014 | 0.081 ± 0.009 |
| Gradient boosting | 0.800 ± 0.036 | 0.937 ± 0.012 | 0.083 ± 0.009 |

Operating threshold (out-of-fold only): high ≥ 0.315 (OOF recall 0.804, precision 0.664);
medium ≥ 0.134.

Held-out test set (scored once; 2000 cluster (student) resamples, percentile 95 % CI):

| Model | Average precision | ROC AUC | Brier | Precision @ t | Recall @ t | F1 @ t |
|---|---|---|---|---|---|---|
| Dummy (prior) | 0.220 [0.166, 0.275] | 0.500 [0.500, 0.500] | 0.172 [0.141, 0.202] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Logistic regression | 0.817 [0.705, 0.901] | 0.936 [0.900, 0.966] | 0.084 [0.060, 0.109] | 0.627 [0.500, 0.740] | 0.804 [0.674, 0.915] | 0.705 [0.590, 0.795] |
| Gradient boosting | 0.804 [0.678, 0.905] | 0.946 [0.916, 0.972] | 0.082 [0.058, 0.108] | 0.709 [0.585, 0.824] | 0.848 [0.735, 0.941] | 0.772 [0.667, 0.857] |

Fairness check by sex (chosen model, high threshold; sex is not an input):

| Set | Group | n | Positives | Recall | Precision | Flag rate |
|---|---|---|---|---|---|---|
| test | F | 128 | 30 | 0.833 [0.682, 0.952] | 0.641 [0.484, 0.780] | 0.305 [0.225, 0.387] |
| test | M | 81 | 16 | 0.750 [0.500, 0.945] | 0.600 [0.353, 0.812] | 0.247 [0.148, 0.358] |
| test | gap F-M | | | +0.083 | +0.041 | +0.058 |
| out_of_fold | F | 463 | 95 | 0.832 [0.755, 0.901] | 0.669 [0.585, 0.752] | 0.255 [0.215, 0.294] |
| out_of_fold | M | 372 | 89 | 0.775 [0.685, 0.854] | 0.657 [0.560, 0.752] | 0.282 [0.232, 0.334] |
| out_of_fold | gap F-M | | | +0.056 | +0.012 | -0.027 |

Ablations (CV AP): primary 0.803 ± 0.057; + age 0.801 ± 0.061; − absences 0.786 ± 0.053;
− g1 (start-of-year) 0.470 ± 0.058. Model file SHA-256
`48f819e394dfefc38d982c54215781de01bfe94679fcbdff052352698a614b75`.

## Screenshots (`docs/screenshots/`, synthetic data)

| Desktop (1440 px) | Mobile (375 px) |
|---|---|
| `desktop-login.png` | `mobile-login.png` |
| `desktop-dashboard.png` | `mobile-dashboard.png` |
| `desktop-dashboard-dark.png` | `mobile-dashboard-dark.png` |
| `desktop-students.png` | `mobile-students.png` |
| `desktop-attendance.png` | `mobile-attendance.png` |
| `desktop-grades.png` | `mobile-grades.png` |
| `desktop-early-warning.png` | `mobile-early-warning.png` |
| `desktop-student-risk.png` | `mobile-student-risk.png` |
| `desktop-student-risk-dark.png` | `mobile-student-risk-dark.png` |

Largest file 273 KB; regenerate with `SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts`.

## Privacy scan ([`PRIVACY_SCAN.md`](PRIVACY_SCAN.md))

Full history (all refs; 10 commits / 294 file versions at the time of the scan, before the
CI-fix and report commits, which change no data files): **no findings** for commit identities
(GitHub noreply only), `Co-Authored-By` trailers, e-mail addresses, local absolute paths, secret
patterns, `.env`/key files, files > 1 MB, the local username, the owner's personal e-mail, the
local folder name, and the actual local secret values. The scanner was first validated against a
repository with planted examples of each problem. The scan is repeated on the final history
before tagging (see below).

## Deviations

1. **Lighthouse mobile performance on the dashboard is 82** (target ≥ 90). Other audited pages:
   login 95, students 92, attendance 96, early-warning list 96, student risk panel 96;
   accessibility 100 on all six. Cause, profiling evidence and mitigations: REVIEW_PACKET M7.
   Recharts was kept because it is the specified chart library.
2. **Python 3.12 via uv** instead of a system install (only 3.13 was present locally); CI uses 3.12.
3. **ESLint 9 / `@hookform/resolvers` 5** pinned for peer-dependency compatibility.
4. **Web port 8088** by default (8080 was taken on the development machine); configurable.
5. **ML reproduction tolerance** is half of the last published digit (5e-4) because Linux and
   Windows builds differ around 1e-5 (details in REVIEW_PACKET M9).
6. The first M4 e2e run failed after creating two students, which remained in the demo
   database until it was reseeded before the M7 Lighthouse run and the M8 screenshots.

## Limitations

- The model was trained on Portuguese secondary-school data (two schools, 2005–06) and **must be
  re-validated on local data before any real use**; EduPulse's inputs are computed slightly
  differently (multi-subject Term 1 average, projected absences) — see the model card.
- Small test set (46 fails) → wide confidence intervals; fairness assessed for sex only, on the
  source data; the recall gap (girls > boys) could not be shown to be real or spurious.
- Login rate limiting is per process; no HTTPS termination in the compose setup; no password
  reset/MFA; a single active academic year with no rollover workflow.
- Out of scope by design: payments, parent/student portals, messaging, multi-tenancy, cloud
  deployment, LLM features, mobile apps.

## Ready for supervisor review

All milestones M0–M9 are done; the repository is private and has not been made public.
