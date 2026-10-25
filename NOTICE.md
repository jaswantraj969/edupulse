# Notices

## Student Performance dataset (used to train the early-warning model)

EduPulse's early-warning model (`ml/`, persisted in `backend/model/`) was trained on:

> P. Cortez and A. Silva. *Using Data Mining to Predict Secondary School Student Performance.*
> In A. Brito and J. Teixeira (eds.), Proceedings of 5th FUture BUsiness TEChnology Conference
> (FUBUTEC 2008), pp. 5–12, Porto, Portugal, April 2008, EUROSIS.
> Dataset: *Student Performance*, UCI Machine Learning Repository,
> https://doi.org/10.24432/C5TG7T

The dataset is licensed under the **Creative Commons Attribution 4.0 International** licence
(CC BY 4.0, https://creativecommons.org/licenses/by/4.0/). The raw data is not redistributed in
this repository; `ml/edupulse_ml/data.py` downloads it from the UCI repository and verifies its
SHA-256 checksums (`ml/data/SOURCE.md`). The trained model parameters are derived from the
dataset. Changes made: the two course files were combined, two columns (G1, failures) were used as model
inputs and the final grade was converted into a pass/fail target.

## Synthetic demo data

All people and records loaded by `python -m app.seed` are synthetic (generated with Faker using
a fixed seed). Any resemblance to real persons is coincidental.
