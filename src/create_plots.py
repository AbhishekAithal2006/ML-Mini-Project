#!/usr/bin/env python3
"""Create MSK-only classifier comparison plots from saved analysis tables."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "msk_paad_2024"
OUT = ROOT / "outputs"
NAVY = "#17324D"
BLUE = "#3F7FA8"
TEAL = "#17817C"
ORANGE = "#C66D4A"
GRAY = "#5B6B78"


def finish(fig, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def threshold_sensitivity() -> None:
    data = pd.read_csv(DATA / "classifier_threshold_sweep.csv")
    fig, ax = plt.subplots(figsize=(9.2, 5.3))
    colors = {
        "Naive Bayes": TEAL,
        "Logistic Regression": NAVY,
        "SVM (RBF)": BLUE,
        "Random Forest": ORANGE,
        "Gradient Boosting": GRAY,
    }
    for name, group in data.groupby("classifier"):
        group = group.sort_values("threshold_days")
        ax.plot(group.threshold_days, group.balanced_accuracy, marker="o", linewidth=2.2,
                markersize=5, label=name, color=colors.get(name, GRAY))
    ax.axvline(270, color="#8997A3", linestyle="--", linewidth=1.2, label="Primary cutoff: 270 days")
    ax.set(title="MSK 2024 classifier sensitivity to the survival horizon",
           xlabel="Death cutoff after diagnosis (days)", ylabel="Balanced accuracy")
    ax.set_xticks(sorted(data.threshold_days.unique()))
    ax.set_ylim(0.45, 0.72)
    ax.grid(axis="y", alpha=.22)
    ax.legend(frameon=False, ncol=2, loc="lower right")
    ax.text(.01, -.22, "Exploratory horizon sweep; the 270-day classifier comparison is the prespecified primary result.",
            transform=ax.transAxes, fontsize=8.5, color=GRAY)
    finish(fig, "threshold_sensitivity.png")


def baseline_vs_tuned() -> None:
    base = pd.read_csv(DATA / "classifier_results.csv").set_index("classifier")
    tuned = pd.read_csv(DATA / "classifier_tuned_results.csv").set_index("classifier")
    models = [x for x in base.index if x in tuned.index]
    y = np.arange(len(models))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.3), sharey=True)
    for ax, metric, title in zip(axes, ["balanced_accuracy", "roc_auc"], ["Balanced accuracy", "ROC-AUC"]):
        ax.barh(y + .18, [base.loc[m, metric] for m in models], height=.34,
                color=BLUE, label="Fixed baseline")
        ax.barh(y - .18, [tuned.loc[m, metric] for m in models], height=.34,
                color=TEAL, label="Nested tuning")
        ax.set_title(title, color=NAVY, fontsize=12, weight="bold")
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score")
        ax.grid(axis="x", alpha=.2)
    axes[0].set_yticks(y, models)
    axes[0].invert_yaxis()
    axes[0].legend(frameon=False, loc="lower right")
    fig.suptitle("MSK 2024 at 270 days: fixed versus nested-tuned models", color=NAVY,
                 fontsize=15, weight="bold")
    finish(fig, "tuned_vs_baseline.png")


def precision_recall_comparison() -> None:
    base = pd.read_csv(DATA / "classifier_results.csv").set_index("classifier")
    tuned = pd.read_csv(DATA / "classifier_tuned_results.csv").set_index("classifier")
    models = [x for x in base.index if x in tuned.index]
    y = np.arange(len(models))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.3), sharey=True)
    for ax, metric, title in zip(axes, ["precision", "recall"], ["Precision", "Recall"]):
        ax.barh(y + .18, [base.loc[m, metric] for m in models], height=.34,
                color=BLUE, label="Fixed baseline")
        ax.barh(y - .18, [tuned.loc[m, metric] for m in models], height=.34,
                color=TEAL, label="Nested tuning")
        ax.set_title(title, color=NAVY, fontsize=12, weight="bold")
        ax.set_xlim(0, .8)
        ax.set_xlabel("Score")
        ax.grid(axis="x", alpha=.2)
    axes[0].set_yticks(y, models)
    axes[0].invert_yaxis()
    axes[0].legend(frameon=False, loc="lower right")
    fig.suptitle("MSK 2024 at 270 days: precision and recall", color=NAVY,
                 fontsize=15, weight="bold")
    finish(fig, "precision_recall_comparison.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for needed in ["classifier_threshold_sweep.csv", "classifier_results.csv", "classifier_tuned_results.csv"]:
        if not (DATA / needed).is_file():
            raise FileNotFoundError(f"Run src/analysis.py first; missing {DATA / needed}")
    threshold_sensitivity()
    baseline_vs_tuned()
    precision_recall_comparison()
    print(f"MSK comparison plots saved to {OUT}")


if __name__ == "__main__":
    main()
