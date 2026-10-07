#!/usr/bin/env python3
"""Build the two-page MSK 2024 results summary PDF from saved analysis outputs."""
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
DATA = ROOT / "outputs" / "msk_paad_2024"
OUT = ROOT / "outputs" / "mini_project_writeup.pdf"


def build() -> None:
    results = pd.read_csv(DATA / "classifier_results.csv")
    threshold = pd.read_csv(DATA / "classifier_threshold_sweep.csv")
    tuned = pd.read_csv(DATA / "classifier_tuned_results.csv")
    survival = pd.read_csv(DATA / "survival_results.csv").iloc[0]
    metadata = json.loads((DATA / "run_metadata.json").read_text())
    logrank = json.loads((DATA / "logrank.json").read_text())

    style = getSampleStyleSheet()
    style.add(ParagraphStyle(name="TitleCustom", parent=style["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=colors.HexColor("#17324D"), alignment=TA_CENTER, spaceAfter=5))
    style.add(ParagraphStyle(name="HCustom", parent=style["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.HexColor("#176B72"), spaceBefore=6, spaceAfter=3))
    style.add(ParagraphStyle(name="BodyCustom", parent=style["BodyText"], fontName="Helvetica", fontSize=8.7, leading=11, spaceAfter=4))
    style.add(ParagraphStyle(name="SmallCustom", parent=style["BodyText"], fontName="Helvetica", fontSize=7.2, leading=8.7, textColor=colors.HexColor("#475569")))
    subtitle = ParagraphStyle(name="SubCustom", parent=style["BodyCustom"], alignment=TA_CENTER, textColor=colors.HexColor("#475569"), spaceAfter=2)
    teamstyle = ParagraphStyle(name="TeamCustom", parent=style["SmallCustom"], alignment=TA_CENTER, spaceAfter=5)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=13*mm, bottomMargin=13*mm, title="Pancreatic Cancer Survival Analysis on MSK 2024")

    story = [
        Paragraph("Pancreatic Cancer Survival Analysis", style["TitleCustom"]),
        Paragraph("MSK 2024 cohort · 270-day classification and survival modeling", subtitle),
        Paragraph("UE24CS352A · Machine Learning Mini-Project", teamstyle),
        Paragraph("Abhishek Aithal (PES1UG24CS651) · Shreeranganath Manjunath Saravade (PES1UG24CS622)", teamstyle),
        Paragraph("Problem and objective", style["HCustom"]),
        Paragraph("We study whether clinical data can help estimate pancreatic cancer survival risk. The analysis follows the broad workflow of Jamalian’s report and extends its Naive Bayes classifier with four additional classifiers. The Stanford cohort described in that report is restricted, so this project uses the public cBioPortal PDAC MSK 2024 cohort. Results describe MSK patients and do not reproduce the paper’s cohort, radiomic features, or numerical scores.", style["BodyCustom"]),
        Paragraph("Dataset", style["HCustom"]),
        Paragraph(f"The downloaded cBioPortal study contains 2,336 patients. We retain {metadata['rows']} with known overall-survival time/status and positive follow-up ({metadata['events']} observed deaths; {metadata['censored']} right-censored). Follow-up months are converted to days. Classification uses baseline age, sex, stage, genomic group, tumor location, tobacco exposure, and recorded medical histories. The Cox model uses age, sex, and stage. No radiomic features are included; treatment fields are omitted to avoid post-diagnosis predictors.", style["BodyCustom"]),
        Paragraph(f"The classification target is a recorded death before 270 days. Patients censored before that cutoff are excluded because their status is unknown. This leaves {metadata['n_known']} known labels, including {results.n_high_risk.iloc[0]} high-risk events; {metadata['n_excluded_censored_before_threshold']} early-censored patients are omitted from this classifier task.", style["BodyCustom"]),
        Paragraph("Approach", style["HCustom"]),
        Paragraph("We compare discretized Naive Bayes, Logistic Regression, RBF SVM, Random Forest, and Histogram Gradient Boosting. Numeric missing values are median-imputed and scaled; categorical values are most-frequent-imputed and one-hot encoded. Preprocessing is fitted inside each training fold. Fixed classifiers use stratified five-fold cross-validation (seed 229) and report balanced accuracy, precision, recall, F1, and ROC-AUC. Nested tuning uses a three-fold parameter search within each of five outer folds; held-out outer folds are used only for scoring. The penalized Cox model is evaluated with five-fold cross-validation and Harrell’s C-index. SMOTE is omitted because synthetic interpolation can create invalid censored survival records.", style["BodyCustom"]),
        PageBreak(),
        Paragraph("Results and Interpretation", style["TitleCustom"]),
        Paragraph("MSK 2024 · five-fold evaluation · 270-day primary cutoff", subtitle),
        Paragraph("Fixed classifier comparison", style["HCustom"]),
    ]

    rows = [["Classifier", "Bal. acc.", "Precision", "Recall", "F1", "ROC-AUC"]]
    for _, row in results.iterrows():
        rows.append([row.classifier, *(f"{row[key]:.3f}" for key in ["balanced_accuracy", "precision", "recall", "f1", "roc_auc"])])
    table = Table(rows, colWidths=[47*mm, 22*mm, 22*mm, 20*mm, 18*mm, 21*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17324D")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTNAME", (0,1), (-1,-1), "Helvetica"), ("FONTSIZE", (0,0), (-1,-1), 7.7), ("ALIGN", (1,1), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF4F6")]), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    story += [table, Spacer(1, 3)]
    best_fixed = results.iloc[0]
    story.append(Paragraph(f"Fixed Logistic Regression led balanced accuracy ({best_fixed.balanced_accuracy:.3f}) and ROC-AUC ({best_fixed.roc_auc:.3f}). Its recall was {best_fixed.recall:.3f} and precision {best_fixed.precision:.3f}, showing that many high-risk flags were false positives.", style["BodyCustom"]))

    story.append(Paragraph("Nested tuning and survival results", style["HCustom"]))
    tuned_rows = [["Classifier", "Fixed bAcc", "Tuned bAcc", "Tuned ROC-AUC"]]
    fixed_idx = results.set_index("classifier")
    for _, row in tuned.iterrows():
        tuned_rows.append([row.classifier, f"{fixed_idx.loc[row.classifier, 'balanced_accuracy']:.3f}", f"{row.balanced_accuracy:.3f}", f"{row.roc_auc:.3f}"])
    tuned_table = Table(tuned_rows, colWidths=[57*mm, 27*mm, 27*mm, 33*mm], repeatRows=1)
    tuned_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#176B72")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTNAME", (0,1), (-1,-1), "Helvetica"), ("FONTSIZE", (0,0), (-1,-1), 7.7), ("ALIGN", (1,1), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF4F6")]), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
    story += [tuned_table, Spacer(1, 3)]
    best_tuned = tuned.loc[tuned.balanced_accuracy.idxmax()]
    story.append(Paragraph(f"Tuned RBF SVM had the highest balanced accuracy ({best_tuned.balanced_accuracy:.3f}; ROC-AUC {best_tuned.roc_auc:.3f}); tuned Random Forest reached {tuned.loc[tuned.classifier == 'Random Forest', 'balanced_accuracy'].iloc[0]:.3f}. Tuning helped some classifiers and reduced scores for others. The clinical Cox model’s mean C-index was {survival.mean_c_index:.3f} (SD {survival.std_c_index:.3f}; {int(survival.successful_folds)}/{int(survival.requested_folds)} successful folds).", style["BodyCustom"]))

    nb = threshold[threshold.classifier == "Naive Bayes"].sort_values("threshold_days")
    horizon_rows = [["Horizon", "Known labels", "High risk", "Bal. acc."]]
    for _, row in nb.iterrows():
        horizon_rows.append([f"{int(row.threshold_days)} days", str(int(row.n_known)), str(int(row.n_high_risk)), f"{row.balanced_accuracy:.3f}"])
    horizon_table = Table(horizon_rows, colWidths=[37*mm, 38*mm, 38*mm, 38*mm], repeatRows=1)
    horizon_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17324D")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTNAME", (0,1), (-1,-1), "Helvetica"), ("FONTSIZE", (0,0), (-1,-1), 7.5), ("ALIGN", (1,1), (-1,-1), "CENTER"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF4F6")]), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
    story += [Paragraph("Naive Bayes horizon sensitivity", style["HCustom"]), horizon_table, Spacer(1, 3)]
    nb_best = nb.loc[nb.balanced_accuracy.idxmax()]
    story.append(Paragraph(f"The exploratory MSK threshold sweep was highest for Naive Bayes at {int(nb_best.threshold_days)} days ({nb_best.balanced_accuracy:.3f}); the primary comparison remains at 270 days to follow the reference cutoff. This horizon sweep is not nested selection. The full-cohort median-risk Kaplan–Meier split had a descriptive log-rank p-value of {logrank['logrank_p_value']:.3g}; it is not out-of-fold validation.", style["BodyCustom"]))
    story += [Paragraph("Conclusion and limitations", style["HCustom"]), Paragraph("These results describe one public MSK cohort and are not clinical decision support. The Stanford cohort and 900 radiomic features in the reference report are unavailable here, so the scores are not directly comparable. Early censoring reduces the classification sample, and the Kaplan–Meier split uses the full cohort. Report the cohort, 270-day label definition, exclusions, features, and nested evaluation whenever quoting results.", style["BodyCustom"]), Paragraph("Sources: Jamalian, A. (2020), CS229 Project Final Report: Pancreatic cancer prognosis using clinical and radiomic data. cBioPortal PDAC MSK 2024 study: https://www.cbioportal.org/study/summary?id=pdac_msk_2024. Code, metrics, and run metadata are in the accompanying repository.", style["SmallCustom"])]
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
