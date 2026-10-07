# Pancreatic Cancer Survival Analysis

This mini-project applies a survival-analysis workflow to the public cBioPortal PDAC MSK 2024 cohort. It compares five classifiers for recorded death by 270 days and evaluates a clinical Cox proportional-hazards model. The Stanford cohort described by Jamalian is restricted, so this project does not reproduce the paper's patients, radiomic features, or numerical results.

## Team

- Abhishek Aithal — PES1UG24CS651
- Shreeranganath Manjunath Saravade — PES1UG24CS622

## Dataset

The analysis uses the cBioPortal study `pdac_msk_2024`. The downloader retrieves 2,336 patient records; the analysis retains 2,260 with known overall-survival time/status and positive follow-up time. Survival is recorded in months by the source and converted to days. The model inputs include age, sex, stage, genomic group, tumor location, tobacco exposure, and recorded medical histories. Treatment fields are excluded to avoid using information collected after diagnosis as a predictor. No radiomic features are included.

At the 270-day classifier cutoff, 2,027 records have known labels. The 233 patients censored before 270 days are omitted from classification because their status at that cutoff is unknown. Of the remaining cases, 533 are high-risk events (recorded death before 270 days).

The CSV is downloaded locally to `data/private/msk_paad_2024.csv` and is excluded from Git. See [data/README.md](data/README.md) for source and schema notes.

## Methods

- **Survival model:** penalized Cox proportional hazards using age, sex, and stage; evaluated with five-fold cross-validation and Harrell's C-index. The Kaplan–Meier/log-rank analysis uses a full-cohort median-risk split and is descriptive, not out-of-fold validation.
- **Classification target:** recorded death before a configurable horizon (default 270 days). Patients censored before the horizon are excluded because their status is unknown.
- **Classifiers:** discretized Naive Bayes, Logistic Regression, RBF SVM, Random Forest, and Histogram Gradient Boosting. Results include balanced accuracy, precision, recall, F1, and ROC-AUC.
- **Validation:** preprocessing is fitted inside training folds. `--tune` runs a three-fold grid search inside each of five outer folds; held-out outer folds are used only for scoring.
- **Imbalance:** SMOTE is not used because synthetic interpolation can create invalid censored survival records. Class weighting is used where supported.

## Setup in VS Code

Open the project folder in VS Code. In the integrated terminal, run these commands from the project root. Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Select `.venv/bin/python` (macOS/Linux) or `.venv\Scripts\python.exe` (Windows) with **Python: Select Interpreter**.

## Download and run

Download the MSK cohort once, then run the five-fold baseline and nested hyperparameter search:

```bash
python data/download_msk_paad.py
python src/analysis.py --data data/private/msk_paad_2024.csv --threshold 270 --folds 5 --seed 229 --output outputs/msk_paad_2024 --tune
```

To regenerate the comparison figures and the two-page PDF write-up:

```bash
python src/create_plots.py
python src/create_writeup.py
```

The editable Word version is included as `outputs/mini_project_writeup.docx`.

`python src/analysis.py --demo --threshold 270 --folds 5 --seed 229` runs synthetic data only. Demo metrics are not project results.

## Results and deliverables

The fixed 270-day MSK comparison gives Logistic Regression a balanced accuracy of 0.653 and ROC-AUC of 0.692. With nested tuning, RBF SVM reaches the highest balanced accuracy (0.661); tuned Random Forest reaches 0.658. The three-feature Cox model has a mean C-index of 0.657 (SD 0.016) across five folds. These are exploratory cohort-specific results, not clinical predictions or a like-for-like comparison with Jamalian's Stanford results.

Analysis tables and the Kaplan–Meier plot are saved under `outputs/msk_paad_2024/`. Comparison plots are saved in `outputs/`. Deliverables:

- Two-page write-up: `outputs/mini_project_writeup.pdf`
- Editable write-up: `outputs/mini_project_writeup.docx`
- Team presentation: `outputs/survival_project_presentation_msk2024.pptx`

The assignment requires a private GitHub repository shared with faculty/TAs. Add the instructor-assigned problem statement and member contribution details when those are provided.

## Replication limits

The Jamalian report describes 80 Stanford patients, clinical and radiomic features, Naive Bayes threshold selection, and Cox models. The MSK cohort is a different public population with a different feature set and no radiomics. This project reproduces the general survival-analysis and classifier-comparison workflow, not the paper's dataset or exact scores.
