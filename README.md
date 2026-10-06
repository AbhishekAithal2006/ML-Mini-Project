# Pancreatic Cancer Survival Analysis

This mini-project follows the survival-analysis workflow in Jamalian's report and extends its binary Naive Bayes baseline with four additional classifiers. Since the Stanford Cancer Center cohort described in that report is not publicly included, this implementation uses the open-access TCGA Pan-Cancer Clinical Data Resource (PAAD cohort) as a documented substitute. It does **not** claim to reproduce the paper's cohort or published scores and has no radiomic features.

## Methods

- Survival endpoint: overall survival time (`duration`, days) and event indicator (`event`, 1=death, 0=right-censored).
- Survival models: penalized Cox proportional hazards with clinical-only input and Harrell's C-index, using shuffled 5-fold cross-validation. A full-cohort Cox median-risk split also produces descriptive Kaplan–Meier curves and a log-rank test; this is not independent validation.
- Classifier task: predict observed death before a configurable time horizon (default 270 days). Patients censored before the horizon are excluded from that binary task because their status at the horizon is unknown.
- Classifiers: discretized Naive Bayes, logistic regression, RBF SVM, random forest, and histogram gradient boosting. Report balanced accuracy, precision, recall, F1, and ROC-AUC from out-of-fold predictions.
- Preprocessing is fit within each fold. SMOTE is not applied: synthetic interpolation of censored survival records can distort event times and censoring, and oversampling before cross-validation would leak information. The classifier models use class weighting where supported.

The synthetic `--demo` option is only for checking that the command-line workflow runs. Never report its metrics as clinical findings.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

## Get the public cohort

```bash
python data/download_tcga.py
```

This downloads the NCI GDC TCGA-CDR workbook and creates `data/private/tcga_paad.csv` locally. See [data/README.md](data/README.md) for source notes and schema.

## Run

```bash
python src/analysis.py --data data/private/tcga_paad.csv --threshold 270 --folds 5 --seed 229
```

For workflow demonstration only:

```bash
python src/analysis.py --demo --threshold 270 --folds 5 --seed 229
```

Results are written under `outputs/`: classifier results at the selected horizon, the full threshold sweep, Cox C-index, Kaplan–Meier plot, log-rank summary, and run metadata. Result summaries and the final PDF/PPTX are included in the repository; the downloaded cohort remains local and is ignored by Git.

## Replication differences and limits

Jamalian et al.'s report describes 80 Stanford patients, 900 radiomic features, SMOTE, Naive Bayes threshold selection, and Cox models. The included public TCGA-CDR cohort has a different population and clinical variables only. The code preserves the general survival-analysis and risk-classification comparison but cannot recreate the original cohort, radiomics, split assignments, or numbers. No radiomic-only or combined clinical-radiomic model is produced unless compatible feature columns are supplied. Any result must be reported as an analysis of TCGA PAAD, not as reproduction of Jamalian's numerical findings.

## Assignment deliverables checklist

- [x] Runnable source code and setup/run instructions.
- [ ] Private GitHub repository shared with faculty/TAs.
- [x] Two-page PDF write-up with actual run results.
- [x] Presentation deck for the review; run the included command for the live demonstration.
- [ ] Team-specific assigned problem statement and contribution details (distributed separately; add when available).
