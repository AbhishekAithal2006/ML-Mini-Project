# Pancreatic Cancer Survival Analysis

This mini-project follows the survival-analysis workflow in Jamalian's report and extends its binary Naive Bayes baseline with four additional classifiers. Since the Stanford Cancer Center cohort described in that report is not publicly included, this implementation uses the open-access TCGA Pan-Cancer Clinical Data Resource (PAAD cohort) as a documented substitute. It does **not** claim to reproduce the paper's cohort or published scores and has no radiomic features.

## Team

- Abhishek Aithal — PES1UG24CS651
- Shreeranganath Manjunath Saravade — PES1UG24CS622

## Methods

- Survival endpoint: overall survival time (`duration`, days) and event indicator (`event`, 1=death, 0=right-censored).
- Survival models: penalized Cox proportional hazards with clinical-only input and Harrell's C-index, using shuffled 5-fold cross-validation. A full-cohort Cox median-risk split also produces descriptive Kaplan–Meier curves and a log-rank test; this is not independent validation.
- Classifier task: predict observed death before a configurable time horizon (default 270 days). Patients censored before the horizon are excluded from that binary task because their status at the horizon is unknown.
- Classifiers: discretized Naive Bayes, logistic regression, RBF SVM, random forest, and histogram gradient boosting. Report balanced accuracy, precision, recall, F1, and ROC-AUC from out-of-fold predictions.
- Preprocessing is fit within each fold. SMOTE is not applied: synthetic interpolation of censored survival records can distort event times and censoring, and oversampling before cross-validation would leak information. The classifier models use class weighting where supported.

The synthetic `--demo` option is only for checking that the command-line workflow runs. Never report its metrics as clinical findings.

## Setup

Open this project folder in VS Code. In the VS Code terminal, run the commands below from the project root. Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

In VS Code, select the project interpreter at `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows) using **Python: Select Interpreter**. If the terminal prompt does not show `(.venv)`, activate the environment again before running the commands below.

## Get the public cohort

```bash
python data/download_tcga.py
```

This downloads the NCI GDC TCGA-CDR workbook and creates `data/private/tcga_paad.csv` locally. See [data/README.md](data/README.md) for source notes and schema.

For a larger independent pancreatic cohort, download the public cBioPortal MSK study:

```bash
python data/download_msk_paad.py
python src/analysis.py --data data/private/msk_paad_2024.csv --threshold 270 --folds 5 --seed 229 --output outputs/msk_paad_2024 --tune
```

This study includes 2,336 patients in the portal. The analysis retains 2,260 with known OS time/status and positive follow-up time; 10 zero-month records and 66 records missing OS time/status are excluded. Follow-up in months is converted to days. The additional features are baseline age, sex, stage, genomic group, tumor location, tobacco exposure, and recorded medical histories. Therapy fields are omitted to avoid using post-diagnosis treatment as a predictor. The public study is [PDAC MSK 2024 in cBioPortal](https://www.cbioportal.org/study/summary?id=pdac_msk_2024).

## Run

Download the TCGA PAAD cohort once, then run the main analysis from the VS Code terminal:

```bash
python data/download_tcga.py
python src/analysis.py --data data/private/tcga_paad.csv --threshold 270 --folds 5 --seed 229 --tune
```

For the larger MSK cohort, run `python data/download_msk_paad.py` first, then use the MSK analysis command in **Get the public cohort** above. Omit `--tune` for the fixed baseline run. The synthetic demonstration can be run without downloading a cohort:

For workflow demonstration only (uses synthetic data; do not report these metrics):

```bash
python src/analysis.py --demo --threshold 270 --folds 5 --seed 229
```

Results are written under `outputs/`: classifier results at the selected horizon, the full threshold sweep, Cox C-index, Kaplan–Meier plot, log-rank summary, and run metadata. The visualization files include `tuned_vs_baseline.png`, `threshold_sensitivity.png`, and `precision_recall_comparison.png`; the cohort-specific Kaplan–Meier plots are in the cohort output folders. Result summaries and the final PDF/PPTX are included in the repository; the downloaded cohort remains local and is ignored by Git.

The final assignment deck, including the larger-cohort and nested-tuning results, is `outputs/survival_project_presentation.pptx`.

Regenerate the two-page PDF after rerunning the analysis:

```bash
python src/create_writeup.py
```

The checked-in results use TCGA-CDR PAAD, seed `229`, and five folds. At 270 days, Logistic Regression had the highest balanced accuracy (0.642); the clinical Cox model's mean C-index was 0.522 (SD 0.035). These exploratory metrics are cohort-specific.

## Improvement experiments


Nested threshold and hyperparameter selection did not improve TCGA out-of-fold balanced accuracy: Logistic Regression scored 0.587 and 0.564, respectively, versus 0.642 for the fixed baseline. Expanding the TCGA Cox model to all available clinical fields reduced mean C-index to 0.487 and yielded only 3/5 successful folds. We therefore kept those variants out of the primary results. As a separate larger-cohort extension, the cBioPortal MSK study produced Logistic Regression balanced accuracy 0.653 and ROC-AUC 0.692 at 270 days (2,027 known labels), and a three-feature Cox C-index of 0.657 (SD 0.016). These scores are not a like-for-like gain over TCGA or Jamalian: the MSK cohort, feature set, outcome distribution, and missingness differ. The cBioPortal MSK outputs are saved separately in `outputs/msk_paad_2024/`.

Use `--tune` to select classifier hyperparameters using three-fold grid search inside each outer training fold. The held-out outer fold is used only for scoring. Tuned metrics are saved separately as `classifier_tuned_results.csv`; selected parameters and inner-CV scores for each outer fold are saved to `classifier_tuned_params.csv`. Keep these nested-CV scores distinct from fixed-baseline scores when presenting model comparisons.

The nested search was run at 270 days on both cohorts. On TCGA, tuned Naive Bayes improved from 0.574 to 0.606 balanced accuracy, while tuned Logistic Regression scored 0.624 versus its 0.642 fixed baseline. On MSK, tuned SVM reached 0.661 versus 0.652 fixed; tuned Random Forest reached 0.658 versus 0.590 fixed. The tuned MSK Logistic Regression was 0.650 versus 0.653 fixed. The best result across these evaluations is MSK SVM at 0.661 balanced accuracy (ROC-AUC 0.675); the gains vary by model and cohort, so keep the per-model comparisons and cohort identity visible. Outer-fold predictions and fold-level selected settings are saved alongside each cohort's baseline outputs.

## Replication differences and limits

Jamalian et al.'s report describes 80 Stanford patients, 900 radiomic features, SMOTE, Naive Bayes threshold selection, and Cox models. The included public TCGA-CDR cohort has a different population and clinical variables only. The code preserves the general survival-analysis and risk-classification comparison but cannot recreate the original cohort, radiomics, split assignments, or numbers. No radiomic-only or combined clinical-radiomic model is produced unless compatible feature columns are supplied. Any result must be reported as an analysis of TCGA PAAD, not as reproduction of Jamalian's numerical findings.


