# Model card — EduPulse early-warning model v1.1.0

> **What this model really does.** The first-term grade carries almost all of the predictive
> signal (99.2 % of the deployed model's permutation importance on the test set). Without any
> grade the model is weak: a model using only previous failures reaches a test average precision
> of 0.414 [95 % CI 0.290, 0.565] and, at the 80 % recall target, flags every student. The tool
> mainly organises and explains a signal teachers can already see.

All numbers below are copied from the generated run record
[`ml/reports/run_record.md`](../ml/reports/run_record.md) (full detail in
`ml/reports/metrics.json`). Re-run with `cd ml && uv run python -m edupulse_ml.train`; CI re-runs
it and fails if any published (3-decimal) number differs (`python -m edupulse_ml.reproduce`).

## Summary

| | |
|---|---|
| Task | Estimate the probability that a student **fails the year** (final grade below 10/20) |
| Prediction moment | **After first-period grades** (end of Term 1): G1 is an input; G2, G3 and whole-year absences are not |
| Model | Logistic regression (standardised inputs), scikit-learn 1.9.1 |
| Inputs (complete list) | `g1` Term 1 average (0–20) and `failures` (previous school years failed) — nothing else |
| Output | Probability and a band: **high** ≥ 0.327, **medium** ≥ 0.162, **low** otherwise; per-input contributions in plain language |
| Training data | UCI Student Performance (Cortez & Silva, 2008), CC BY 4.0, DOI 10.24432/C5TG7T |
| Owner | EduPulse project; model file SHA-256 `0d6716084619bfa3b08a3a007454c387a2d21bd79865ad8cdda3586f56b51169` |
| Version history | v1.1.0 (review T-R2): absences removed, new holdout. v1.0.0 superseded (see Protocol history) |

## Intended use

- **Decision support for school staff** (teachers, year heads, counsellors) to decide which
  students to talk to first after Term 1. A score is a prompt to look at the student's whole
  context — it is not a judgement about the student.
- **Never an automatic sanction.** It must not be used to place students in tracks, deny
  opportunities, discipline, or report to third parties, and no action may be taken on the
  score alone.
- Teachers see scores only for their own classes; every view and export of scores is recorded
  in an audit log.

**Out of scope:** use outside secondary schools; use on individual subjects; use before any
Term 1 grade exists (the app shows "insufficient data" instead); any use on real students before
local re-validation (see Limitations).

## Data

- **Both UCI files are used:** 1,044 rows = 395 Mathematics + 649 Portuguese course records from
  two Portuguese public secondary schools, school year 2005–06. Positive class (G3 < 10):
  230 rows (22.0 %).
- **Students in both files.** Matching on the 13 identifying attributes from the dataset
  documentation gives 382 rows in its merge; 370 Mathematics rows have a Portuguese match.
  EduPulse forms 662 identity groups, 366 of which have rows in both files (9 groups with more
  than two rows are attribute collisions and are kept together). **Grouped splitting:** no group
  is on both sides of the holdout (0) or of any of the 15 CV folds (0 in each).
- Files verified by SHA-256 on every load (`ml/data/SOURCE.md`).
- **Not available at the prediction moment, never inputs:** G2 and G3 (later grades) and
  `absences` (a whole-year count in the UCI data — removed in review T-R2).
- **Excluded on purpose:** every attribute about a student's private life or family — sex, age,
  home address type, family size, parents' cohabitation, parents' education and jobs, guardian,
  family and paid educational support, school support, internet at home, romantic relationship,
  alcohol use (Dalc, Walc), health, going out, free time, family relationship, activities,
  nursery, wish for higher education, study time, school choice reason, travel time, school.
  Sex is used *only* to measure error-rate differences.

### Inputs and why each is kept

| Input | What it is | Why it is acceptable |
|---|---|---|
| `g1` | First-period grade (0–20) | A school record of the student's own work, known at the prediction moment; the main signal |
| `failures` | Previous school years failed (0–3) | A school record of past academic outcomes, known before the year starts |

## Evaluation protocol (pre-registered in `PROJECT_STATUS.md`, D78, before the run)

1. A **new** stratified, student-grouped **20 % holdout** (seed 20261026; 209 rows, 46 fails),
   created once. The previous holdout (seed 20251025) had already been scored and was not reused.
2. On the other 80 % (835 rows): **3 × repeated stratified grouped 5-fold CV**; dummy baseline,
   logistic regression and gradient boosting on **identical folds**. Primary metric: **average
   precision** (AP).
3. Selection: best mean CV AP, simpler model within 0.01 → logistic regression (0.769) over
   gradient boosting (0.761).
4. Thresholds from **out-of-fold predictions only**: high = highest threshold reaching 80 %
   recall (0.327); medium = 95 % recall (0.162).
5. Refit on the 80 %; the **test set is scored once** (enforced by a holdout guard: decisions are
   frozen first, each model can be scored once); 95 % CIs from 2,000 student-level bootstrap
   resamples.

## Results

Cross-validation (mean ± SD over 15 folds):

| Model | Average precision | ROC AUC | Brier |
|---|---|---|---|
| Dummy (prior) | 0.220 ± 0.002 | 0.500 ± 0.000 | 0.172 ± 0.001 |
| **Logistic regression** | **0.769 ± 0.062** | 0.933 ± 0.014 | 0.087 ± 0.011 |
| Gradient boosting | 0.761 ± 0.067 | 0.929 ± 0.016 | 0.090 ± 0.013 |

Held-out test set (scored once; 95 % CI):

| Model | Average precision | ROC AUC | Precision @ 0.327 | Recall @ 0.327 | F1 @ 0.327 |
|---|---|---|---|---|---|
| Dummy (prior) | 0.220 [0.164, 0.278] | 0.500 [0.500, 0.500] | 0.000 | 0.000 | 0.000 |
| **Logistic regression** | **0.845 [0.740, 0.924]** | 0.953 [0.924, 0.977] | 0.651 [0.527, 0.767] | 0.891 [0.792, 0.976] | 0.752 [0.652, 0.838] |
| Gradient boosting | 0.855 [0.756, 0.928] | 0.956 [0.928, 0.978] | 0.627 [0.507, 0.739] | 0.913 [0.818, 0.981] | 0.743 [0.641, 0.829] |

Reading the numbers: at the high threshold the model finds about 9 in 10 students in this test
set who go on to fail, and about 2 in 3 students it flags do fail. Treat the cross-validated AP
(0.769 ± 0.062) as the more stable estimate: the test AP comes from a single 209-row holdout and
its interval is wide. The test AP is higher than v1.0.0's (0.817) because the holdout is
different, not because the model improved — removing absences lowered CV AP from 0.803 to 0.769.

### Value of the first-period grade: pre-term variant

| Model | CV AP | Test AP [95 % CI] | Test ROC AUC | Precision @ t | Recall @ t |
|---|---|---|---|---|---|
| After first-period grades (deployed) | 0.769 ± 0.062 | 0.845 [0.740, 0.924] | 0.953 [0.924, 0.977] | 0.651 [0.527, 0.767] | 0.891 [0.792, 0.976] |
| Pre-term: `failures` only (not served) | 0.399 ± 0.052 | 0.414 [0.290, 0.565] | 0.725 [0.641, 0.803] | 0.220 [0.164, 0.278] | 1.000 [1.000, 1.000] |

The pre-term variant **collapses to a near-trivial model**: `failures` takes only four values, so
its 80 %-recall threshold (0.164) sits at the score of students with no previous failures and it
flags every student (flag rate 1.000; precision equals the base rate 0.220). It is reported for
comparison only.

Other ablations (CV AP): `g1` only 0.755 ± 0.059; adding age 0.780 ± 0.065 (age stays excluded as
a protected characteristic, a decision made before the run).

Permutation importance on the test set (descriptive only, 50 repeats, drop in AP): `g1`
0.582 ± 0.037 (**99.2 %**), `failures` 0.005 ± 0.011 (0.8 %).

## Fairness check (by sex, at the high threshold)

| Set | Group | n | Fails | Recall | Precision | Flag rate |
|---|---|---|---|---|---|---|
| Test | F | 101 | 25 | 0.840 [0.680, 0.966] | 0.636 [0.464, 0.800] | 0.327 [0.243, 0.413] |
| Test | M | 108 | 21 | 0.952 [0.833, 1.000] | 0.667 [0.476, 0.846] | 0.278 [0.187, 0.377] |
| Out-of-fold | F | 490 | 100 | 0.840 [0.767, 0.907] | 0.636 [0.555, 0.714] | 0.269 [0.229, 0.308] |
| Out-of-fold | M | 345 | 84 | 0.762 [0.672, 0.853] | 0.621 [0.526, 0.717] | 0.299 [0.248, 0.355] |

Recall gap (F − M): −0.112 on test, +0.078 out-of-fold — the sign differs between the two sets.
With 25 and 21 test positives the intervals overlap heavily: **the result is inconclusive and is
not evidence of fairness**. Staff should not read a low score as reassurance for anyone.

## Explanations

Each score lists both inputs with their effect in log-odds against a typical value (the training
median: Term 1 average 11/20, 0 failures), sorted by size, in plain language — e.g. "Term 1
average of 6.5/20 (32 %) is below the typical 11/20; this raises the estimate." For logistic
regression this attribution is exact. Coefficients per standard deviation: Term 1 average
−2.772, failures +0.257.

## How EduPulse computes the inputs (mapping to the app)

| Model input | UCI definition | EduPulse source (column / computation) | What synthetic demo students get |
|---|---|---|---|
| `g1` | First-period grade, 0–20, per course | `grades.score` / `assessments.max_score` for Term 1 assessments, weight-averaged across subjects, ÷ 5 | Computed from their seeded synthetic Term 1 grades (no constant, no imputation) |
| `failures` | Past class failures | `students.prior_failures` (0–3) | The seeded synthetic value of that column |

Every input is computable by EduPulse; nothing is constant-filled or imputed. Attendance is still
recorded and shown in the app, but it is not a model input. A student with no Term 1 grade is not
scored ("insufficient data").

## Protocol history

| Version | Holdout seed | Inputs | Status |
|---|---|---|---|
| v1.0.0 (M5, re-checked in T-R1) | 20251025 | g1, absences, failures | **Superseded** in review T-R2: UCI absences are a whole-year count and are not known after first-period grades (feature-timing mismatch) |
| v1.1.0 (T-R2) | 20261026 (new) | g1, failures | Current; pre-registered (D78) before the run |

## Limitations

- **Trained on Portuguese secondary-school data from 2005–06** (two schools). Grading practices
  and the meaning of a fail differ between countries, schools and years. **The model must be
  re-validated on local, consented data before any real use**, and the thresholds re-chosen there.
- **Input shift in the app:** in the UCI data G1 is a per-course grade; EduPulse averages all
  subjects, which narrows the spread.
- Small sample (1,044 rows, 230 fails; 46 in the test set) → wide confidence intervals.
- Two inputs only; essentially one signal (the Term 1 grade). The model cannot see anything about
  a student's circumstances — a deliberate privacy choice, and why a human must interpret every
  score.
- The fairness check covers sex only, on the source data, and is inconclusive (not evidence of
  fairness); other groups could not be assessed.
- Probabilities are not re-calibrated for the app's population; use the bands, not the decimals.

## Licence and attribution

Training data: P. Cortez and A. Silva, *Using Data Mining to Predict Secondary School Student
Performance*, FUBUTEC 2008; UCI Machine Learning Repository, DOI 10.24432/C5TG7T, licensed
CC BY 4.0. See `NOTICE.md`.
