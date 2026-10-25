# Case study: an explainable early-warning model for EduPulse

## The question

Teachers usually learn that a student is failing when the final grades come in — too late to
help. The question for EduPulse was narrower and answerable: **at the end of the first term,
using only information the school already records, can we point staff to the students most
likely to fail the year — in a way they can understand, check and challenge?**

Every figure below is copied from the generated run record
([`ml/reports/run_record.md`](../ml/reports/run_record.md)); CI re-runs the pipeline and fails if
the numbers change.

## Data

There is no real school data in this project, so the model was trained on the public **UCI
Student Performance** dataset (Cortez & Silva, 2008; CC BY 4.0): two Portuguese secondary schools,
school year 2005–06, one file for Mathematics (395 rows) and one for Portuguese (649 rows).
`python -m edupulse_ml.data` downloads it and checks SHA-256 hashes recorded in
[`ml/data/SOURCE.md`](../ml/data/SOURCE.md); the pipeline refuses to load a changed file.

Two properties of the data shaped the design:

1. **The same student appears twice.** The dataset documentation's merge on 13 identifying attributes yields 382 matched rows; in EduPulse's grouping 370 maths rows have a Portuguese match, forming 366 identity groups that span both files (9 groups with more than two rows are attribute collisions, kept together). Splitting rows at
   random would put a student's Maths row in training and their Portuguese row in the test set,
   inflating results. Using the attributes the dataset authors themselves use to match students,
   every split is **grouped by student** (662 groups).
2. **Grades arrive in three periods** (G1, G2, G3). G3 is the final grade; G1 is known after the
   first term. The **prediction moment is therefore after first-period grades (end of Term 1)**: G1 may be used, G2 and
   G3 may not (G3 only defines the target: fail = G3 < 10/20, 22.0 % of rows).

## Choosing inputs: deployable and fair by construction

The UCI data has 30 attributes, many of them sensitive — sex, parents' education and jobs,
family size, alcohol use, romantic relationships, home internet. A model can often squeeze a
little more accuracy out of such columns, at the cost of scoring students partly on who their
family is.

EduPulse uses **three inputs only**, all of which the app records itself:

| Input | Meaning |
|---|---|
| Term 1 average (G1) | first-period grade, 0–20 |
| Absences | school absences |
| Previous failures | school years failed before |

Sex and every family or socio-economic attribute are excluded; sex is kept aside only to *measure*
error-rate differences. Age was considered and left out as a protected characteristic; the
ablation showed it added nothing (CV AP 0.801 ± 0.061 with age vs 0.803 ± 0.057 without).

## Evaluation protocol (decided before looking at test results)

| Step | What was done |
|---|---|
| Holdout | One stratified, student-grouped 20 % test set (209 rows, 46 fails), created once with a fixed seed |
| Model comparison | 3 × repeated stratified grouped 5-fold CV on the other 80 %; dummy baseline, logistic regression and gradient boosting on **identical folds** |
| Metric | **Average precision** (precision–recall), suited to a minority class and to "who should we look at first" |
| Selection rule | Best mean CV AP; a simpler model within 0.01 wins |
| Threshold | Highest threshold reaching 80 % recall on **out-of-fold** predictions (the test set never influences it); a "medium" band at 95 % recall |
| Final test | Refit on the 80 %, score the test set **once**, 95 % CIs from 2,000 student-level bootstrap resamples |

## Results

Cross-validation (15 folds):

| Model | Average precision | ROC AUC |
|---|---|---|
| Dummy (prior) | 0.220 ± 0.002 | 0.500 ± 0.000 |
| Logistic regression | **0.803 ± 0.057** | 0.939 ± 0.014 |
| Gradient boosting | 0.800 ± 0.036 | 0.937 ± 0.012 |

The two real models were indistinguishable, so the rule picked **logistic regression** — easier
to explain, with exact per-input contributions.

Held-out test set, scored once:

| Model | AP [95 % CI] | Recall @ 0.315 | Precision @ 0.315 |
|---|---|---|---|
| Logistic regression | **0.817 [0.705, 0.901]** | 0.804 [0.674, 0.915] | 0.627 [0.500, 0.740] |
| Gradient boosting | 0.804 [0.678, 0.905] | 0.848 [0.735, 0.941] | 0.709 [0.585, 0.824] |
| Dummy | 0.220 [0.166, 0.275] | 0.000 | 0.000 |

In words: at the "high risk" threshold the model finds about four in five students who go on to
fail, and about three in five students it flags do fail. Gradient boosting happened to do a little
better at the threshold on the test set; the selection stayed as pre-registered, because choosing
on test results would make the test estimate optimistic, and the intervals overlap widely.

What the model learned (log-odds per standard deviation): Term 1 average **−2.98**, absences
+0.24, previous failures +0.17. The first-term grade carries almost all the signal; without it
(a "start of year" model) CV AP falls to 0.470 ± 0.058.

## Fairness check

| Set | Group | Recall | Precision |
|---|---|---|---|
| Test | girls (30 fails) | 0.833 [0.682, 0.952] | 0.641 [0.484, 0.780] |
| Test | boys (16 fails) | 0.750 [0.500, 0.945] | 0.600 [0.353, 0.812] |
| Out-of-fold | girls (95 fails) | 0.832 [0.755, 0.901] | 0.669 [0.585, 0.752] |
| Out-of-fold | boys (89 fails) | 0.775 [0.685, 0.854] | 0.657 [0.560, 0.752] |

The point estimates show the model missing failing boys somewhat more often (recall gap +0.083 on
test, +0.056 out of fold), but with 30 and 16 test positives the intervals overlap heavily. The
result is **inconclusive and is not evidence of fairness**: it neither confirms nor rules out a
real difference. It is reported rather than hidden, and the model card tells staff not to read a
low score for a boy as reassurance.

## What the first-period grade is worth

A pre-term variant without any period grade (absences and previous failures only), evaluated with
the same protocol and its own out-of-fold threshold, reaches test AP 0.489 [0.361, 0.646] against
0.817 [0.705, 0.901] for the deployed model. At the same 80 % recall its precision is 0.233
[0.167, 0.299] versus 0.627 [0.500, 0.740]. Permutation importance on the test set attributes
96.8 % of the deployed model's importance to `g1` — so the model is honest about its timing: it
is a warning issued *after* first-period grades, not a prediction made from background.

## Protocol history

| Run | When | What changed | Decisions | Discarded? |
|---|---|---|---|---|
| 1 | M5 | Initial protocol: grouped holdout and CV, three candidates, OOF threshold, test once | Logistic regression; thresholds 0.315 / 0.134 | No |
| 2 | Supervisor review (T-R1) | Added a recorded split audit, a holdout guard (decisions frozen before the test set is read; each model scored once), the pre-term variant and test-set permutation importance | Unchanged: same model choice, thresholds, test metrics and model file SHA-256 | No |

The review asked whether any student fell on both sides of a split. The audit, now part of every
run, shows 0 crossings for the holdout and for each of the 15 CV folds, so no run had to be
discarded and the original holdout remains valid. The feature set did not change in the review
(no family or private-life attributes were ever inputs), so no re-run on a new holdout was needed.

## From research data to the app

The backend computes the same three inputs from EduPulse's own records
([`backend/app/services/risk.py`](../backend/app/services/risk.py)):

- **Term 1 average** = weight-averaged percentage of all Term 1 assessments ÷ 5;
- **absences** = Term 1 days marked *absent*, projected to a full year by the ratio of school days;
- **previous failures** = the student's recorded prior failures.

The persisted model is loaded only after its SHA-256 matches the metadata written at training.
A backend test feeds the backend the exact rows scored in `ml/` and checks it reproduces the same
probabilities and explanations. Students without Term 1 grades are shown as "insufficient data"
rather than guessed at.

Each score is explained by **reference substitution**: how much the log-odds change if one input
is replaced by a typical value (the training median). For logistic regression this is exact, and
it translates directly into sentences such as "Term 1 average of 6.5/20 (33 %) is below the
typical 11/20; this raises the estimate."

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
- **Input shift.** EduPulse averages all subjects, while the UCI G1 is per course; it projects
  absences from Term 1, while UCI counts the whole year. Both are reasonable proxies, not identical.
- **Small evaluation set** (46 test fails): wide confidence intervals.
- **Fairness beyond sex** could not be assessed with this data, and EduPulse deliberately does not
  store sex — so local monitoring would need a separate, consented process.
- Natural next steps: calibrate on local data, re-score each term with the latest grades, and
  measure whether flagged students who received support did better — the only metric that
  ultimately matters.
