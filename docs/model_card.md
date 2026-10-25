# Model card — EduPulse early-warning model v1.0.0

All numbers below are copied from the generated run record
[`ml/reports/run_record.md`](../ml/reports/run_record.md) (full detail in
`ml/reports/metrics.json`). Re-run with `cd ml && uv run python -m edupulse_ml.train`;
CI re-runs it and fails if any published (3-decimal) number differs (`python -m edupulse_ml.reproduce`).

## Summary

| | |
|---|---|
| Task | Estimate the probability that a student **fails the year** (final grade below 10/20) |
| Prediction moment | **After first-period grades** (end of Term 1): G1 is an input; G2 and G3 are not |
| Model | Logistic regression (standardised inputs), scikit-learn 1.9.1 |
| Inputs (complete list) | `g1` Term 1 average (0–20), `absences`, `failures` (previous years failed) — nothing else |
| Output | Probability and a band: **high** ≥ 0.315, **medium** ≥ 0.134, **low** otherwise; per-input contributions in plain language |
| Training data | UCI Student Performance (Cortez & Silva, 2008), CC BY 4.0, DOI 10.24432/C5TG7T |
| Owner | EduPulse project; model file SHA-256 `48f819e394dfefc38d982c54215781de01bfe94679fcbdff052352698a614b75` |

## Intended use

- **Decision support for school staff** (teachers, year heads, counsellors) to decide which
  students to talk to first after Term 1. A score is a prompt to look at the student's whole
  context — it is not a judgement about the student.
- **Never an automatic sanction.** It must not be used to place students in tracks, deny
  opportunities, discipline, or report to third parties, and no action may be taken on the
  score alone.
- Teachers see scores only for their own classes; every view and export of scores is recorded
  in an audit log (see `docs/process/PROJECT_STATUS.md`, M6).

**Out of scope:** use outside secondary schools; use on individual subjects; use before any
Term 1 grade exists (the app shows "insufficient data" instead); any use on real students
before local re-validation (see Limitations).

## Data

- **Both UCI files are used:** 1,044 rows = 395 Mathematics + 649 Portuguese course records
  from two Portuguese public secondary schools, school year 2005–06.
- **Students in both files.** Matching on the 13 identifying attributes from the dataset
  documentation gives 382 rows in its merge; 370 Mathematics rows have a Portuguese match.
  EduPulse forms 662 identity groups, 366 of which have rows in both files (9 groups with more
  than two rows are attribute collisions and are kept together, which is conservative).
  **Grouped splitting:** no group was on both sides of the holdout (0) or of any of the 15 CV
  folds (0 in each); 74 of the shared students are in the test set. An ungrouped split with
  the same seed would have put 120 shared students on both sides. No run was discarded.
- Positive class (final grade G3 < 10): 230 rows (22.0 %).
- Files verified by SHA-256 on every load (`ml/data/SOURCE.md`).
- **Leakage control.** G2 (second-period grade) and G3 are never inputs; G3 only defines the
  target. A student's two course rows are always in the same split (grouped splitting) so the
  model is never tested on a student it saw in training.
- **Excluded on purpose:** every attribute about a student's private life or family — sex,
  age, home address type, family size, parents' cohabitation, parents' education and jobs,
  guardian, family and paid educational support, school support, internet at home, romantic
  relationship, alcohol use (Dalc, Walc), health, going out, free time, family relationship,
  activities, nursery, wish for higher education, study time, school choice reason, travel time,
  school. None was ever a model input. Sex is used *only* to measure error-rate differences.

### Inputs and why each is kept

| Input | What it is | Why it is acceptable |
|---|---|---|
| `g1` | First-period grade (0–20) | A school record of the student's own work; the main signal and what teachers already act on |
| `absences` | Days absent | A school attendance record the school can act on |
| `failures` | Previous school years failed (0–3) | A school record of past academic outcomes |

All three are things the school records itself; none describes family, health or private life.

## Evaluation protocol

1. A stratified, student-grouped **20 % holdout** (209 rows, 46 fails) was created once with a
   fixed seed and not touched until the end.
2. On the other 80 % (835 rows): **3 × repeated stratified grouped 5-fold CV**; the dummy
   baseline, logistic regression and gradient boosting were scored on **identical folds**.
   Primary metric: **average precision** (AP).
3. Selection rule fixed in advance: best mean CV AP, preferring the simpler model when within
   0.01 → logistic regression (0.803) over gradient boosting (0.800).
4. **Threshold chosen on out-of-fold predictions only:** the highest threshold reaching 80 %
   recall (0.315); medium band at 95 % recall (0.134).
5. The chosen model was refit on the 80 % and the **test set scored once**; 95 % CIs from 2,000
   student-level (cluster) bootstrap resamples.

## Results

Cross-validation (mean ± SD over 15 folds):

| Model | Average precision | ROC AUC | Brier |
|---|---|---|---|
| Dummy (prior) | 0.220 ± 0.002 | 0.500 ± 0.000 | 0.172 ± 0.001 |
| **Logistic regression** | **0.803 ± 0.057** | 0.939 ± 0.014 | 0.081 ± 0.009 |
| Gradient boosting | 0.800 ± 0.036 | 0.937 ± 0.012 | 0.083 ± 0.009 |

Held-out test set (scored once; 95 % CI):

| Model | Average precision | ROC AUC | Precision @ 0.315 | Recall @ 0.315 | F1 @ 0.315 |
|---|---|---|---|---|---|
| Dummy (prior) | 0.220 [0.166, 0.275] | 0.500 [0.500, 0.500] | 0.000 | 0.000 | 0.000 |
| **Logistic regression** | **0.817 [0.705, 0.901]** | 0.936 [0.900, 0.966] | 0.627 [0.500, 0.740] | 0.804 [0.674, 0.915] | 0.705 [0.590, 0.795] |
| Gradient boosting | 0.804 [0.678, 0.905] | 0.946 [0.916, 0.972] | 0.709 [0.585, 0.824] | 0.848 [0.735, 0.941] | 0.772 [0.667, 0.857] |

Reading the numbers: at the high threshold the model finds about 4 in 5 students who go on to
fail, and about 3 in 5 students it flags do fail. On the test set gradient boosting scored a
little better at the threshold; the pre-registered selection was kept rather than choosing on
test results, and the confidence intervals overlap widely. The dummy flags nobody because its
constant probability (0.22) is below the threshold.

### Value of the first-period grade: pre-term variant

A variant **without any period grade** (inputs `absences`, `failures`; same model family; its own
threshold 0.148 from out-of-fold predictions; test scored once) shows what G1 adds:

| Model | CV AP | Test AP [95 % CI] | Test ROC AUC | Precision @ t | Recall @ t |
|---|---|---|---|---|---|
| After first-period grades (deployed) | 0.803 ± 0.057 | 0.817 [0.705, 0.901] | 0.936 [0.900, 0.966] | 0.627 [0.500, 0.740] | 0.804 [0.674, 0.915] |
| Pre-term (no grades) | 0.470 ± 0.058 | 0.489 [0.361, 0.646] | 0.702 [0.599, 0.792] | 0.233 [0.167, 0.299] | 0.804 [0.684, 0.915] |

At the same recall, the pre-term variant flags far more students who do not fail (precision 0.233
vs 0.627). It is reported for comparison only; EduPulse does not serve it.

Other ablations (CV AP): adding age 0.801 ± 0.061 (no gain, so it stays out); without absences
0.786 ± 0.053.

## Fairness check (by sex, at the high threshold)

| Set | Group | n | Fails | Recall | Precision | Flag rate |
|---|---|---|---|---|---|---|
| Test | F | 128 | 30 | 0.833 [0.682, 0.952] | 0.641 [0.484, 0.780] | 0.305 [0.225, 0.387] |
| Test | M | 81 | 16 | 0.750 [0.500, 0.945] | 0.600 [0.353, 0.812] | 0.247 [0.148, 0.358] |
| Out-of-fold | F | 463 | 95 | 0.832 [0.755, 0.901] | 0.669 [0.585, 0.752] | 0.255 [0.215, 0.294] |
| Out-of-fold | M | 372 | 89 | 0.775 [0.685, 0.854] | 0.657 [0.560, 0.752] | 0.282 [0.232, 0.334] |

**Gaps (F − M):** recall +0.083 on test and +0.056 out-of-fold; precision +0.041 / +0.012.
With 30 and 16 test positives the intervals overlap heavily: **the result is inconclusive and is
not evidence of fairness** — it can neither confirm nor rule out a real difference. Staff should not read a low score for a boy as reassurance,
and the check must be repeated on local data (which EduPulse itself does not hold, because it
does not store sex).

## Explanations

Each score lists the three inputs with their effect in log-odds against a typical value (the
training median: Term 1 average 11/20, 2 absences, 0 failures), sorted by size, in plain
language — e.g. "Term 1 average of 6.5/20 (32 %) is below the typical 11/20; this raises the
estimate." For logistic regression this attribution is exact. Coefficients per standard
deviation: Term 1 average −2.980, absences +0.244, failures +0.172 — the first-term grade
dominates.

## How EduPulse computes the inputs (mapping to the app)

| Model input | UCI definition | EduPulse source (column / computation) | What synthetic demo students get |
|---|---|---|---|
| `g1` | First-period grade, 0–20, per course | `grades.score` / `assessments.max_score` for Term 1 assessments, weight-averaged across subjects, ÷ 5 | Computed from their seeded synthetic Term 1 grades (no constant, no imputation) |
| `absences` | School absences (whole year) | `attendance_records` with status *absent* in Term 1 × (school days in the year ÷ school days in Term 1) | Computed from their seeded synthetic daily attendance |
| `failures` | Past class failures | `students.prior_failures` (0–3) | The seeded synthetic value of that column |

Every input is computable by EduPulse; nothing is constant-filled or imputed. A student with no
Term 1 grade is not scored ("insufficient data"). Permutation importance on the test set
(descriptive only, 50 repeats, drop in AP): `g1` 0.564 ± 0.034 (96.8 %), `failures`
0.010 ± 0.005 (1.8 %), `absences` 0.008 ± 0.010 (1.4 %) — 100 % of the importance comes from
app-computable inputs, so the deployed model is the model whose inputs the app really has.

Students with no Term 1 grade are shown as *insufficient data* and not scored. In this
installation all students are **synthetic demo data**; the UI labels every score
"Demo — synthetic data".

## Limitations

- **Trained on Portuguese secondary-school data from 2005–06** (two schools). Grading
  practices, absence recording and the meaning of a fail differ between countries, schools and
  years. **The model must be re-validated on local, consented data before any real use**, and
  the thresholds re-chosen there.
- **Input shift in the app:** in the UCI data G1 is a per-course grade; EduPulse averages all
  subjects, which narrows the spread. UCI absences are a whole-year count; EduPulse projects
  Term 1 absences linearly, which overstates early bursts and ignores later changes; excused
  absences are not counted.
- Small sample (1,044 rows, 230 fails; 46 in the test set) → wide confidence intervals.
- Only three inputs: the model cannot see anything about a student's circumstances. That is a
  deliberate privacy choice, and also why a human must interpret every score.
- The fairness check covers sex only, on the source data, and is inconclusive (not evidence of
  fairness); other groups could not be assessed.
- Probabilities are not re-calibrated for the app's population; use the bands, not the decimals.

## Licence and attribution

Training data: P. Cortez and A. Silva, *Using Data Mining to Predict Secondary School Student
Performance*, FUBUTEC 2008; UCI Machine Learning Repository, DOI 10.24432/C5TG7T, licensed
CC BY 4.0. See `NOTICE.md`.
