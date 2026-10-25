# Dataset provenance

| Item | Value |
|------|-------|
| Name | Student Performance |
| Creators | Paulo Cortez, Alice Silva (University of Minho) |
| Publisher | UCI Machine Learning Repository |
| DOI | [10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T) |
| Download URL | https://archive.ics.uci.edu/static/public/320/student+performance.zip |
| Licence | [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode) (stated on the dataset page, checked 2026-10-25) |
| Fetched | 2026-10-25 with `python -m edupulse_ml.data` |

Citation: P. Cortez and A. Silva. *Using Data Mining to Predict Secondary School Student
Performance.* In A. Brito and J. Teixeira (eds.), Proceedings of 5th FUture BUsiness TEChnology
Conference (FUBUTEC 2008), pp. 5–12, Porto, Portugal, April 2008, EUROSIS.

## Integrity (SHA-256)

| File | SHA-256 |
|------|---------|
| `student+performance.zip` (as downloaded) | `82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177` |
| `student-mat.csv` (395 rows) | `e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80` |
| `student-por.csv` (649 rows) | `a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f` |

The same values are hard-coded in `edupulse_ml/data.py`; loading fails if a file differs.
The raw files are not committed (`ml/data/raw/` is git-ignored); re-download them with the
command above.

## Description

Secondary-school students from two Portuguese public schools (Gabriel Pereira and Mousinho da
Silveira), school year 2005–2006, collected from school reports and questionnaires. One file per
course (Mathematics, Portuguese language). Students can appear in both files. The dataset documentation's merge on 13 identifying attributes yields 382 matched rows; in EduPulse's grouping 370 maths rows have a Portuguese match, forming 366 identity groups that span both files (9 groups with more than two rows are attribute collisions, kept together).
EduPulse keeps all of a student's rows on the same side of every split. Grades are on a 0–20 scale; G1 and G2 are the
first and second period grades and G3 the final grade.
