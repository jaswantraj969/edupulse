# Case study: an explainable early-warning model for EduPulse

> **The honest summary.** The first-term grade carries almost all of the predictive signal
> (99.2 % of the deployed model's permutation importance on the test set). Without any grade the
> model is weak: using only previous failures it reaches a test average precision of 0.414
> [95 % CI 0.290, 0.565] and, at the 80 % recall target, flags every student. The tool mainly
> organises and explains a signal teachers can already see.

## The question

Teachers usually learn that a student is failing when the final grades come in — too late to
help. The question for EduPulse was narrower and answerable: **after the first term's grades,
using only information the school already records, can we point staff to the students most
likely to fail the year — in a way they can understand, check and challenge?**

Every figure below is copied from the generated run record
([`ml/reports/run_record.md`](../ml/reports/run_record.md)); CI re-runs the pipeline and fails if
the published numbers change.

## Data

There is no real school data in this project, so the model was trained on the public **UCI
Student Performance** dataset (Cortez & Silva, 2008; CC BY 4.0): two Portuguese secondary schools,
school year 2005–06, one file for Mathematics (395 rows) and one for Portuguese (649 rows).
`python -m edupulse_ml.data` downloads it and checks SHA-256 hashes recorded in
[`ml/data/SOURCE.md`](../ml/data/SOURCE.md); the pipeline refuses to load a changed file.

Three properties of the data shaped the design:

1. **The same student appears twice.** The dataset documentation's merge on 13 identifying
   attributes yields 382 matched rows; in EduPulse's grouping 370 maths rows have a Portuguese
   match, forming 366 identity groups that span both files (9 groups with more than two rows are
   attribute collisions, kept together). Splitting rows at random would put a student's Maths row
   in training and their Portuguese row in the test set, inflating results, so every split is
   **grouped by student** (662 groups) and every run audits it (0 crossings). The 13-attribute
   key is not a true identifier: two distinct students with identical attributes are merged into
   one group. That only ever keeps extra rows together, so it makes the splits more
   conservative, not leakier.
2. **Grades arrive in three periods** (G1, G2, G3). G3 is the final grade; G1 is known after the
   first term. The **prediction moment is after first-period grades (end of Term 1)**: G1 may be
   used, G2 and G3 may not (G3 only defines the target: fail = G3 < 10/20, 22.0 % of rows).
3. **Absences are counted over the whole year.** They are therefore *not* known at the
   prediction moment. Version 1.0.0 used them; review T-R2 found this timing mismatch and the
   current model does not (see Protocol history).

## Choosing inputs: deployable and fair by construction

The UCI data has 30 attributes, many of them sensitive — sex, parents' education and jobs,
family size, alcohol use, romantic relationships, home internet. A model can often squeeze a
little more accuracy out of such columns, at the cost of scoring students partly on who their
family is.

EduPulse uses **two inputs only**, both known at the prediction moment and recorded by the app:

| Input | Meaning |
|---|---|
| Term 1 average (G1) | first-period grade, 0–20 |
| Previous failures | school years failed before |

Sex and every family or socio-economic attribute are excluded; sex is kept aside only to *measure*
error-rate differences. Age is excluded as a protected characteristic (decided before the run;
the ablation shows CV AP 0.780 ± 0.065 with age vs 0.769 ± 0.062 without — within noise).

## Evaluation protocol (pre-registered before the current run)

| Step | What was done |
|---|---|
| Holdout | A new stratified, student-grouped 20 % test set (seed 20261026; 209 rows, 46 fails), created once |
| Model comparison | 3 × repeated stratified grouped 5-fold CV on the other 80 %; dummy baseline, logistic regression and gradient boosting on **identical folds** |
| Metric | **Average precision** (precision–recall), suited to a minority class and to "who should we look at first" |
| Selection rule | Best mean CV AP; a simpler model within 0.01 wins |
| Threshold | Highest threshold reaching 80 % recall on **out-of-fold** predictions (the test set never influences it), using each training row's mean OOF probability over the 3 CV repeats; a "medium" band at 95 % recall |
| Final test | Refit on the 80 %, score the test set **once** (enforced by a holdout guard), 95 % CIs from 2,000 student-level bootstrap resamples |

The plan (seed, inputs, candidates, rules) was committed and pushed before the run
(`PROJECT_STATUS.md`, D78).

## Results

Cross-validation (15 folds):

| Model | Average precision | ROC AUC |
|---|---|---|
| Dummy (prior) | 0.220 ± 0.002 | 0.500 ± 0.000 |
| Logistic regression | **0.769 ± 0.062** | 0.933 ± 0.014 |
| Gradient boosting | 0.761 ± 0.067 | 0.929 ± 0.016 |

The two real models were indistinguishable, so the rule picked **logistic regression** — easier
to explain, with exact per-input contributions.

Held-out test set, scored once:

| Model | AP [95 % CI] | ROC AUC | Recall @ 0.327 | Precision @ 0.327 |
|---|---|---|---|---|
| Logistic regression | **0.845 [0.740, 0.924]** | 0.953 [0.924, 0.977] | 0.891 [0.792, 0.976] | 0.651 [0.527, 0.767] |
| Gradient boosting | 0.855 [0.756, 0.928] | 0.956 [0.928, 0.978] | 0.913 [0.818, 0.981] | 0.627 [0.507, 0.739] |
| Dummy | 0.220 [0.164, 0.278] | 0.500 [0.500, 0.500] | 0.000 | 0.000 |

In words: at the "high risk" threshold the model finds about nine in ten of this test set's
students who go on to fail, and about two in three students it flags do fail. The test AP comes
from one 209-row holdout; the cross-validated AP (0.769 ± 0.062) is the steadier estimate.
Compared with v1.0.0, CV AP dropped from 0.803 to 0.769 when absences were removed; the higher
test AP than v1.0.0's (0.817) reflects a different holdout, not a better model.

What the model learned (log-odds per standard deviation): Term 1 average **−2.772**, previous
failures +0.257.

## What the first-period grade is worth

A pre-term variant without any period grade — previous failures only — evaluated with the same
protocol and its own out-of-fold threshold, reaches CV AP 0.399 ± 0.052 and test AP 0.414
[0.290, 0.565] (ROC AUC 0.725 [0.641, 0.803]). It **collapses to a near-trivial model**: with only
four possible input values, its 80 %-recall threshold falls at the score of students without
previous failures, so it flags every student (recall 1.000 [1.000, 1.000], precision 0.220
[0.164, 0.278] = the base rate). Permutation importance on the test set attributes 99.2 % of the
deployed model's importance to `g1` (failures 0.8 %). The model is therefore honest about its
timing — a warning issued *after* first-period grades — and modest about its value: it ranks and
explains what the Term 1 grades already show.

## Fairness check

| Set | Group | n | Fails | Recall | Precision |
|---|---|---|---|---|---|
| Test | girls | 101 | 25 | 0.840 [0.680, 0.966] | 0.636 [0.464, 0.800] |
| Test | boys | 108 | 21 | 0.952 [0.833, 1.000] | 0.667 [0.476, 0.846] |
| Out-of-fold | girls | 490 | 100 | 0.840 [0.767, 0.907] | 0.636 [0.555, 0.714] |
| Out-of-fold | boys | 345 | 84 | 0.762 [0.672, 0.853] | 0.621 [0.526, 0.717] |

The recall gap changes sign between the test set (−0.112) and the out-of-fold predictions
(+0.078), and the intervals overlap heavily. The result is **inconclusive and is not evidence of
fairness**: it neither confirms nor rules out a real difference.

## Protocol history

| Run | When | Inputs | Holdout seed | What happened | Status |
|---|---|---|---|---|---|
| 1 | M5 | g1, absences, failures | 20251025 | Initial protocol: grouped holdout and CV, three candidates, OOF threshold, test once; logistic regression, thresholds 0.315 / 0.134, test AP 0.817 | **Superseded** |
| 2 | Review T-R1 | same | 20251025 | Added split audit (0 crossings), holdout guard, pre-term variant, test-set permutation importance; all results identical to run 1 | **Superseded** |
| 3 | Review T-R2 | g1, failures | 20261026 (new) | Pre-registered re-run after absences were found to be a whole-year count (feature-timing mismatch); results above | Current (v1.1.0) |

Runs 1–2 are superseded because one input, absences, was not available at the stated prediction
moment. Because their holdout had already been scored, the re-run uses a new holdout rather than
re-scoring the old one.

## From research data to the app

The backend computes the same two inputs from EduPulse's own records
([`backend/app/services/risk.py`](../backend/app/services/risk.py)):

- **Term 1 subject average** = weight-averaged percentage of the student's Term 1 assessments
  **in one subject** ÷ 5;
- **previous failures** = the student's recorded prior failures.

A UCI row is one student in one course, so the app scores **each (student, subject) pair**
with the same model (review T-R3). The student's band is that of their highest-risk subject,
the class list shows and sorts by that subject, the student panel lists every subject with its
own probability, band and two factors, and the CSV export has one row per pair. A subject
without Term 1 grades is "insufficient data" for that subject only. The earlier version
averaged all subjects, which could hide one failing subject: a synthetic demo student scored
low on the average (Term 1 average 10.4/20, probability 0.12) but is high risk in English
(33.5 %, probability 0.81) and Biology (44.5 %, 0.35).

Attendance is still recorded and shown in the app (student page and the trend chart next to the
estimate) but is not part of the score. The persisted model is loaded only after its SHA-256
matches the metadata written at training. A backend test feeds the backend the exact rows scored
in `ml/` and checks it reproduces the same probabilities and explanations. Subjects without
Term 1 grades are shown as "insufficient data" rather than guessed at.

Each score is explained by **reference substitution**: how much the log-odds change if one input
is replaced by a typical value (the training median). For logistic regression this is exact, and
it translates directly into sentences such as "Term 1 Mathematics average of 6.5/20 (32 %) is
below the typical 11/20; this raises the estimate."

## Guard-rails in the product

- A visible banner on every early-warning screen: *"Decision support; review with the student's
  context."* — plus "Demo — synthetic data" while demo data is loaded.
- Bands are always written out ("High risk"), never colour alone; factors read as sentences.
- Teachers see only their own classes, enforced by the API.
- Every view and export of scores is written to an audit log that administrators can review.
- Exports repeat the decision-support notice on every row.

## Limitations and what would come next

- **Different place, different time.** The model encodes two Portuguese schools in 2005–06.
  Before any real use it must be re-validated on local data (with consent and a data-protection
  assessment), and the thresholds re-chosen there.
- **Input shift.** `g1` is per subject like the UCI per-course G1, but EduPulse's subjects,
  assessments and weights differ from the two UCI courses, and a student with many subjects has
  more chances to be flagged on one of them.
- **Small evaluation set** (46 test fails): wide confidence intervals.
- **Fairness beyond sex** could not be assessed with this data, and EduPulse deliberately does not
  store sex — so local monitoring would need a separate, consented process.
- Natural next steps: calibrate on local data, re-score each term with the latest grades, use
  in-year attendance only if it is recorded at the same moment the model is trained for, and
  measure whether flagged students who received support did better — the only metric that
  ultimately matters.
