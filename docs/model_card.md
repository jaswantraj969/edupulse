# Model card — EduPulse early-warning model v1.0.0

All numbers below are copied from the generated run record
[`ml/reports/run_record.md`](../ml/reports/run_record.md) (full detail in
`ml/reports/metrics.json`). Re-run with `cd ml && uv run python -m edupulse_ml.train`;
CI re-runs it and fails if the numbers differ (`python -m edupulse_ml.reproduce`).

## Summary

| | |
|---|---|
| Task | Estimate the probability that a student **fails the year** (final grade below 10/20) |
| Prediction moment | End of the first term: first-period grade known, later grades unknown |
| Model | Logistic regression (standardised inputs), scikit-learn 1.9.1 |
| Inputs | Term 1 average (0–20), absences, previous year failures |
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

- 1,044 rows: 395 Mathematics + 649 Portuguese course records from two Portuguese public
  secondary schools, school year 2005–06; 662 distinct students (382 appear in both courses).
- Positive class (final grade G3 < 10): 230 rows (22.0 %).
- Files verified by SHA-256 on every load (`ml/data/SOURCE.md`).
- **Leakage control.** G2 (second-period grade) and G3 are never inputs; G3 only defines the
  target. A student's two course rows are always in the same split (grouped splitting) so the
  model is never tested on a student it saw in training.
- **Excluded on purpose (protected / sensitive):** sex, age, home address type, family size,
  parents' cohabitation, parents' education and jobs, guardian, family/paid educational support,
  internet at home, romantic relationship, alcohol use, health, school choice reason, travel time.
  Sex is used *only* to measure error-rate differences (fairness check below).

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

Ablations (CV AP): adding age 0.801 ± 0.061 (no gain, so it stays out); without absences
0.786 ± 0.053; without the Term 1 grade 0.470 ± 0.058 — a start-of-year model without grades
would be far weaker.

## Fairness check (by sex, at the high threshold)

| Set | Group | n | Fails | Recall | Precision | Flag rate |
|---|---|---|---|---|---|---|
| Test | F | 128 | 30 | 0.833 [0.682, 0.952] | 0.641 [0.484, 0.780] | 0.305 [0.225, 0.387] |
| Test | M | 81 | 16 | 0.750 [0.500, 0.945] | 0.600 [0.353, 0.812] | 0.247 [0.148, 0.358] |
| Out-of-fold | F | 463 | 95 | 0.832 [0.755, 0.901] | 0.669 [0.585, 0.752] | 0.255 [0.215, 0.294] |
| Out-of-fold | M | 372 | 89 | 0.775 [0.685, 0.854] | 0.657 [0.560, 0.752] | 0.282 [0.232, 0.334] |

**Gaps (F − M):** recall +0.083 on test and +0.056 out-of-fold — the model misses failing boys
somewhat more often than failing girls; precision gaps are small (+0.041 / +0.012). All
intervals overlap heavily and the male test group has only 16 fails, so the data cannot
establish whether the gap is real. Staff should not read a low score for a boy as reassurance,
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

| Model input | UCI definition | EduPulse computation |
|---|---|---|
| `g1` | First-period grade, 0–20, per course | Weight-averaged percentage of all Term 1 assessments across subjects ÷ 5 |
| `absences` | School absences (whole year) | Term 1 days marked *absent* × (school days in the year ÷ school days in Term 1) |
| `failures` | Past class failures | `students.prior_failures` (0–3) |

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
- The fairness check covers sex only, on the source data; other groups could not be assessed.
- Probabilities are not re-calibrated for the app's population; use the bands, not the decimals.

## Licence and attribution

Training data: P. Cortez and A. Silva, *Using Data Mining to Predict Secondary School Student
Performance*, FUBUTEC 2008; UCI Machine Learning Repository, DOI 10.24432/C5TG7T, licensed
CC BY 4.0. See `NOTICE.md`.
