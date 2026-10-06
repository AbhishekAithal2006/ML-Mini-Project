"""Build the assignment's concise two-page results summary from the CSV outputs."""
from pathlib import Path
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "mini_project_writeup.pdf"


def build():
    results = pd.read_csv(ROOT / "outputs" / "classifier_results.csv")
    threshold = pd.read_csv(ROOT / "outputs" / "classifier_threshold_sweep.csv")
    survival = pd.read_csv(ROOT / "outputs" / "survival_results.csv").iloc[0]
    meta = json.loads((ROOT / "outputs" / "run_metadata.json").read_text())
    logrank = json.loads((ROOT / "outputs" / "logrank.json").read_text())
    n, events, censored = meta["rows"], 100, 84
    style = getSampleStyleSheet()
    style.add(ParagraphStyle(name="TitleCustom", parent=style["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#17324D"), alignment=TA_CENTER, spaceAfter=6))
    style.add(ParagraphStyle(name="HCustom", parent=style["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#176B72"), spaceBefore=7, spaceAfter=4))
    style.add(ParagraphStyle(name="BodyCustom", parent=style["BodyText"], fontSize=9.1, leading=12, spaceAfter=5))
    style.add(ParagraphStyle(name="SmallCustom", parent=style["BodyText"], fontSize=7.8, leading=9.5, textColor=colors.HexColor("#475569")))
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=19*mm, leftMargin=19*mm, topMargin=16*mm, bottomMargin=16*mm, title="Pancreatic Cancer Survival Analysis")
    story = []
    story += [Paragraph("Pancreatic Cancer Survival Analysis", style["TitleCustom"]),
              Paragraph("Replication of the survival-analysis workflow with a public TCGA cohort and additional classifiers", ParagraphStyle("Sub", parent=style["BodyCustom"], alignment=TA_CENTER, textColor=colors.HexColor("#475569"))),
              Paragraph("UE24CS352A · Machine Learning Mini-Project · Team members: ______________________________", ParagraphStyle("Team", parent=style["SmallCustom"], alignment=TA_CENTER)), Spacer(1, 5)]
    story += [Paragraph("Problem", style["HCustom"]), Paragraph("The reference project studies survival prognosis from pancreatic cancer clinical and radiomic measurements using Kaplan–Meier estimation, Cox proportional hazards, and a binary risk classifier. We reproduced the analysis structure and added Logistic Regression, RBF SVM, Random Forest, and Gradient Boosting comparisons. The Stanford cohort in the reference report is restricted; therefore, this implementation uses an open TCGA Pan-Cancer Clinical Data Resource PAAD cohort. Results below describe TCGA PAAD and are not a numerical replication of Jamalian’s cohort.", style["BodyCustom"])]
    story += [Paragraph("Dataset", style["HCustom"]), Paragraph(f"The NCI GDC TCGA-CDR table yielded {n} PAAD records with overall-survival time and status ({events} observed deaths; {censored} right-censored observations). Clinical predictors used for classification were age, gender, tumor stage, histology, and race where available. The Cox model used age, gender, and stage after one-hot encoding and fold-local missing-value imputation. No radiomic features are present in this source. For binary classification, the target is observed death by 270 days; the 13 patients censored before 270 days were omitted because their status at that horizon is unknown. This left {meta['n_known']} known labels, including {results.n_high_risk.iloc[0]} high-risk events.", style["BodyCustom"])]
    story += [Paragraph("Approach", style["HCustom"]), Paragraph("We evaluated a penalized Cox proportional-hazards model using five-fold shuffled cross-validation and Harrell’s C-index. The separate binary task used stratified five-fold cross-validation with preprocessing fitted inside each training fold. Naive Bayes used quantile-discretized numerical features; other classifiers used imputation and scaling/one-hot encoding as appropriate. We report balanced accuracy, precision, recall, F1, and ROC-AUC. The high-risk horizon was also compared at 240, 300, 330, and 360 days. We did not apply SMOTE: interpolating right-censored times can create invalid survival observations, and oversampling before cross-validation can leak information.", style["BodyCustom"])]
    story += [Paragraph("What differs from the source report", style["HCustom"]), Paragraph("The original report uses a Naive Bayes model to select among survival thresholds, generates Kaplan–Meier curves for model-defined risk groups, and compares clinical, radiomic, and combined Cox models. This project reproduces the survival/C-index and risk-classification structure where TCGA-CDR supports it, adds extra classifiers, and reports a descriptive Kaplan–Meier/log-rank analysis. It cannot evaluate radiomic or combined feature sets because the public extract has clinical variables only.", style["BodyCustom"])]
    story += [PageBreak(), Paragraph("Results and Interpretation", style["TitleCustom"]),
              Paragraph("Five-fold evaluation on the TCGA PAAD substitute cohort", ParagraphStyle("Sub2", parent=style["BodyCustom"], alignment=TA_CENTER, textColor=colors.HexColor("#475569")))]
    story += [Paragraph("Binary classifier comparison at 270 days", style["HCustom"])]
    rows = [["Classifier", "Bal. acc.", "Precision", "Recall", "F1", "ROC-AUC"]]
    for _, r in results.iterrows():
        rows.append([r.classifier, *(f"{r[k]:.3f}" for k in ["balanced_accuracy", "precision", "recall", "f1", "roc_auc"])])
    table = Table(rows, colWidths=[48*mm, 22*mm, 22*mm, 20*mm, 18*mm, 21*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17324D")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8), ("ALIGN", (1,1), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF4F6")]), ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story += [table, Spacer(1, 5), Paragraph("Logistic Regression achieved the highest balanced accuracy (0.642), narrowly ahead of the RBF SVM (0.640). Recall was higher than precision for both, reflecting the imbalance between 32 observed early deaths and 139 known non-events at this horizon. ROC-AUC was modest, and no classifier provides strong discrimination in this small, incomplete clinical feature set.", style["BodyCustom"])]
    story += [Paragraph("Naive Bayes threshold sweep", style["HCustom"])]
    nb = threshold[threshold.classifier == "Naive Bayes"].sort_values("threshold_days")
    thr_rows = [["Horizon", "Known labels", "High risk", "Balanced accuracy"]]
    for _, r in nb.iterrows():
        thr_rows.append([f"{int(r.threshold_days)} days", str(int(r.n_known)), str(int(r.n_high_risk)), f"{r.balanced_accuracy:.3f}"])
    tt = Table(thr_rows, colWidths=[39*mm, 40*mm, 40*mm, 42*mm], repeatRows=1)
    tt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#176B72")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8), ("ALIGN", (1,1), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF4F6")]), ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    story += [tt, Spacer(1, 5), Paragraph(f"The Cox clinical model achieved a five-fold mean C-index of {survival.mean_c_index:.3f} (SD {survival.std_c_index:.3f}; {int(survival.successful_folds)}/{int(survival.requested_folds)} folds). A full-cohort median-risk split produced a log-rank statistic of {logrank['logrank_statistic']:.2f} (p={logrank['logrank_p_value']:.4f}); these Kaplan–Meier curves are descriptive and use the same records to fit the Cox risk scores, so they are not independent validation. This C-index is below the 0.67–0.82 values reported in Jamalian’s paper, but direct score comparison is not valid because the cohort and predictors differ.", style["BodyCustom"])]
    story += [Paragraph("Conclusion and limitations", style["HCustom"]), Paragraph("This implementation demonstrates survival modeling alongside a separate early-mortality classification extension. Logistic Regression gave the best balanced accuracy at the chosen horizon, but its modest ROC-AUC and low precision show that the result is not sufficient for clinical use. The cohort, features, label construction, and censoring exclusions differ from the reference report. The one-week assignment should present the work as a method replication on an open substitute cohort, state these differences clearly, and avoid claims of clinical prediction or causal effects.", style["BodyCustom"])]
    story += [Paragraph("Sources: Jamalian, A. (2020), CS229 Project Final Report: Pancreatic cancer prognosis using clinical and radiomic data. TCGA-CDR / NCI Genomic Data Commons, https://gdc.cancer.gov/about-data/publications/PanCan-Clinical-2018 . Code, exact split seed, and full per-model metrics are in the accompanying repository outputs.", style["SmallCustom"])]
    doc.build(story)


if __name__ == "__main__":
    build()
