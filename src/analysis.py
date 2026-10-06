#!/usr/bin/env python3
"""Reproducible survival-analysis replication and binary-classifier extension.

Input CSV must have `duration` (time from diagnosis to event or last follow-up)
and `event` (1=event observed, 0=right-censored). Other columns are predictors.
The synthetic demo is for checking the workflow only; it is not patient data and
cannot reproduce the Jamalian report's results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (balanced_accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, GridSearchCV
from sklearn.naive_bayes import CategoricalNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier


def make_demo(n: int = 160, seed: int = 229) -> pd.DataFrame:
    """Create an explicitly synthetic cohort to exercise the CLI."""
    rng = np.random.default_rng(seed)
    age = rng.normal(64, 10, n).clip(35, 90)
    tumor_width = rng.lognormal(2.7, .35, n)
    stage = rng.choice([1, 2, 3, 4], n, p=[.12, .38, .38, .12])
    chemo = rng.binomial(1, .62, n)
    latent = .025 * (age - 60) + .42 * (stage - 2) + .28 * (tumor_width - 15) / 10 - .45 * chemo
    event_time = rng.exponential(430 / np.exp(latent))
    censor_time = rng.uniform(180, 1050, n)
    return pd.DataFrame({
        "duration": np.minimum(event_time, censor_time).round(1),
        "event": (event_time <= censor_time).astype(int),
        "age": age.round(1), "tumor_width": tumor_width.round(1),
        "stage": stage, "chemotherapy": chemo,
        "resectability": rng.choice(["resectable", "borderline", "locally_advanced"], n),
    })


def known_binary_outcome(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, np.ndarray]:
    """Label known status at threshold; exclude early-censored unknown outcomes."""
    known = (df.duration >= threshold) | ((df.duration < threshold) & (df.event == 1))
    sub = df.loc[known]
    # Positive means observed event before threshold (high risk).
    y = ((sub.duration < threshold) & (sub.event == 1)).astype(int).to_numpy()
    return sub, y


def classifier_scores(df: pd.DataFrame, threshold: float, folds: int, seed: int) -> tuple[pd.DataFrame, dict]:
    sub, y = known_binary_outcome(df, threshold)
    if len(np.unique(y)) != 2 or min(np.bincount(y)) < folds:
        raise ValueError("Not enough examples in both known outcome classes for requested CV folds.")
    X = sub.drop(columns=["duration", "event"])
    num = X.select_dtypes(include=np.number).columns.tolist()
    cat = [c for c in X.columns if c not in num]
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    prep = ColumnTransformer([("num", numeric, num), ("cat", categorical, cat)])
    # NB follows the paper's discretized clinical-feature concept.
    nbprep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                           ("bins", KBinsDiscretizer(n_bins=4, encode="ordinal", strategy="quantile"))]), num),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                           ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat),
    ])
    models = {
        "Naive Bayes": Pipeline([("prep", nbprep), ("model", CategoricalNB(class_prior=[0.5, 0.5]))]),
        "Logistic Regression": Pipeline([("prep", prep), ("model", LogisticRegression(class_weight="balanced", max_iter=2000))]),
        "SVM (RBF)": Pipeline([("prep", prep), ("model", SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=seed))]),
        "Random Forest": Pipeline([("prep", prep), ("model", RandomForestClassifier(n_estimators=300, class_weight="balanced", min_samples_leaf=2, random_state=seed, n_jobs=1))]),
        "Gradient Boosting": Pipeline([("prep", prep), ("model", HistGradientBoostingClassifier(max_iter=150, l2_regularization=1.0, random_state=seed))]),
    }
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    rows = []
    for name, model in models.items():
        pred = cross_val_predict(model, X, y, cv=cv, method="predict", n_jobs=1)
        prob = cross_val_predict(model, X, y, cv=cv, method="predict_proba", n_jobs=1)[:, 1]
        rows.append({"classifier": name, "balanced_accuracy": balanced_accuracy_score(y, pred),
                     "precision": precision_score(y, pred, zero_division=0),
                     "recall": recall_score(y, pred, zero_division=0),
                     "f1": f1_score(y, pred, zero_division=0),
                     "roc_auc": roc_auc_score(y, prob), "n_known": len(y),
                     "n_high_risk": int(y.sum()), "threshold_days": threshold})
    return pd.DataFrame(rows).sort_values("balanced_accuracy", ascending=False), {"n_known": len(y), "n_excluded_censored_before_threshold": int((~((df.duration >= threshold) | ((df.duration < threshold) & (df.event == 1)))).sum())}


def tuned_classifier_scores(df: pd.DataFrame, threshold: float, folds: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Nested CV: select hyperparameters in inner folds and score outer held-out folds."""
    from sklearn.model_selection import ParameterGrid

    sub, y = known_binary_outcome(df, threshold)
    if len(np.unique(y)) != 2 or min(np.bincount(y)) < folds:
        raise ValueError("Not enough examples in both known outcome classes for requested CV folds.")
    X = sub.drop(columns=["duration", "event"])
    num = X.select_dtypes(include=np.number).columns.tolist()
    cat = [c for c in X.columns if c not in num]
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    prep = ColumnTransformer([("num", numeric, num), ("cat", categorical, cat)])
    nbprep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                           ("bins", KBinsDiscretizer(n_bins=4, encode="ordinal", strategy="quantile"))]), num),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                           ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat),
    ])
    searches = {
        "Naive Bayes": (Pipeline([("prep", nbprep), ("model", CategoricalNB())]), {
            "model__alpha": [0.1, 1.0, 5.0], "model__class_prior": [None, [0.5, 0.5]],
        }),
        "Logistic Regression": (Pipeline([("prep", prep), ("model", LogisticRegression(max_iter=2000))]), {
            "model__C": [0.1, 1.0, 10.0], "model__class_weight": [None, "balanced", {0: 1, 1: 2}],
        }),
        "SVM (RBF)": (Pipeline([("prep", prep), ("model", SVC(kernel="rbf", probability=False, random_state=seed))]), {
            "model__C": [0.1, 1.0, 10.0], "model__gamma": ["scale", "auto"],
            "model__class_weight": [None, "balanced"],
        }),
        "Random Forest": (Pipeline([("prep", prep), ("model", RandomForestClassifier(n_estimators=250, random_state=seed, n_jobs=1))]), {
            "model__max_depth": [None, 6], "model__min_samples_leaf": [2, 10],
            "model__max_features": ["sqrt", 0.75], "model__class_weight": [None, "balanced"],
        }),
        "Gradient Boosting": (Pipeline([("prep", prep), ("model", HistGradientBoostingClassifier(random_state=seed))]), {
            "model__max_iter": [75, 150], "model__learning_rate": [0.05, 0.1],
            "model__max_leaf_nodes": [7, 15],
        }),
    }
    outer = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    oof = {name: {"pred": np.zeros(len(y), dtype=int), "score": np.zeros(len(y), dtype=float)} for name in searches}
    param_rows = []
    for fold, (train_idx, test_idx) in enumerate(outer.split(X, y), start=1):
        inner = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed + fold)
        for name, (estimator, grid) in searches.items():
            search = GridSearchCV(estimator, grid, scoring="balanced_accuracy", cv=inner, n_jobs=1, refit=True)
            search.fit(X.iloc[train_idx], y[train_idx])
            fitted = search.best_estimator_
            oof[name]["pred"][test_idx] = fitted.predict(X.iloc[test_idx])
            if hasattr(fitted, "predict_proba"):
                scores = fitted.predict_proba(X.iloc[test_idx])[:, 1]
            else:
                scores = fitted.decision_function(X.iloc[test_idx])
            oof[name]["score"][test_idx] = scores
            param_rows.append({"classifier": name, "outer_fold": fold,
                               "best_inner_balanced_accuracy": float(search.best_score_),
                               "best_params": json.dumps(search.best_params_, sort_keys=True)})
    rows = []
    for name, values in oof.items():
        pred, score = values["pred"], values["score"]
        rows.append({"classifier": name, "balanced_accuracy": balanced_accuracy_score(y, pred),
                     "precision": precision_score(y, pred, zero_division=0),
                     "recall": recall_score(y, pred, zero_division=0),
                     "f1": f1_score(y, pred, zero_division=0), "roc_auc": roc_auc_score(y, score),
                     "n_known": len(y), "n_high_risk": int(y.sum()), "threshold_days": threshold,
                     "evaluation": "5-fold outer CV; 3-fold inner hyperparameter search"})
    result = pd.DataFrame(rows).sort_values("balanced_accuracy", ascending=False)
    return result, pd.DataFrame(param_rows)


def survival_models(df: pd.DataFrame, folds: int, seed: int, output: Path) -> pd.DataFrame:
    """Evaluate Cox models with fold-local preprocessing and held-out C-index."""
    from lifelines import CoxPHFitter
    from lifelines.utils import concordance_index
    from sklearn.model_selection import KFold

    feature_sets = {"clinical": [c for c in df.columns if c not in ("duration", "event")]}
    # The report specifies the clinical/radiomic split. Keep explicit split via
    # column prefixes; users can set radiomic_ on radiomics and clinical_ on clinical features.
    clinical = [c for c in ("clinical_age", "clinical_gender", "clinical_stage") if c in df.columns]
    radiomic = [c for c in df.columns if c.startswith("radiomic_")]
    if clinical: feature_sets["clinical"] = clinical
    if radiomic: feature_sets["radiomic"] = radiomic
    if clinical and radiomic: feature_sets["clinical_and_radiomic"] = clinical + radiomic

    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    rows = []
    for set_name, cols in feature_sets.items():
        scores = []
        for train_idx, test_idx in kf.split(df):
            train, test = df.iloc[train_idx], df.iloc[test_idx]
            tr = train[["duration", "event"] + cols].copy()
            te = test[["duration", "event"] + cols].copy()
            cats = tr[cols].select_dtypes(exclude=np.number).columns
            if len(cats):
                combined = pd.concat([tr[cats], te[cats]], axis=0)
                combined = pd.get_dummies(combined, columns=list(cats), dummy_na=False, drop_first=True, dtype=float)
                trx, tex = combined.iloc[:len(tr)], combined.iloc[len(tr):]
                tr = pd.concat([tr[["duration", "event"]].reset_index(drop=True), trx.reset_index(drop=True)], axis=1)
                te = pd.concat([te[["duration", "event"]].reset_index(drop=True), tex.reset_index(drop=True)], axis=1)
            medians = tr.drop(columns=["duration", "event"]).median()
            tr = tr.fillna(medians).fillna(0)
            te = te.fillna(medians).fillna(0)
            predictors = tr.columns.difference(["duration", "event"])
            varying = tr[predictors].nunique(dropna=False) > 1
            covars = list(predictors[varying.to_numpy()])
            if not covars:
                raise ValueError("No varying predictors in this fold")
            # Scale on training fold only; helps numerical stability with radiomics.
            means, stds = tr[covars].mean(), tr[covars].std().replace(0, 1).fillna(1)
            tr[covars] = (tr[covars] - means) / stds
            te[covars] = (te[covars] - means) / stds
            cph = CoxPHFitter(penalizer=0.5, l1_ratio=0.0)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    cph.fit(tr, duration_col="duration", event_col="event", show_progress=False)
                risk = cph.predict_partial_hazard(te[covars]).to_numpy().ravel()
                scores.append(concordance_index(te.duration, -risk, te.event))
            except Exception as exc:
                warnings.warn(f"Skipping failed {set_name} fold: {exc}")
        rows.append({"feature_set": set_name, "n_features": len(cols), "mean_c_index": float(np.mean(scores)) if scores else np.nan,
                     "std_c_index": float(np.std(scores, ddof=1)) if len(scores) > 1 else np.nan,
                     "successful_folds": len(scores), "requested_folds": folds})
    return pd.DataFrame(rows)


def risk_group_kaplan_meier(df: pd.DataFrame, output: Path) -> dict:
    """Fit descriptive full-cohort Cox model and plot median-risk KM curves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from lifelines import CoxPHFitter, KaplanMeierFitter
    from lifelines.statistics import logrank_test

    cols = [c for c in ("clinical_age", "clinical_gender", "clinical_stage") if c in df.columns]
    features = df[cols].copy()
    cats = features.select_dtypes(exclude=np.number).columns
    features = pd.get_dummies(features, columns=list(cats), drop_first=True, dtype=float)
    features = features.apply(pd.to_numeric, errors="coerce")
    features = features.fillna(features.median()).fillna(0)
    features = features.loc[:, features.nunique(dropna=False) > 1]
    if features.shape[1] == 0:
        raise ValueError("No varying predictors available for Cox risk grouping")
    means, stds = features.mean(), features.std().replace(0, 1).fillna(1)
    features = (features - means) / stds
    fit_data = pd.concat([df[["duration", "event"]].reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    cph = CoxPHFitter(penalizer=0.5, l1_ratio=0.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cph.fit(fit_data, duration_col="duration", event_col="event")
    risk = cph.predict_partial_hazard(features).to_numpy().ravel()
    high = risk >= np.median(risk)
    durations, events = df.duration.to_numpy(), df.event.to_numpy()
    km_low, km_high = KaplanMeierFitter(), KaplanMeierFitter()
    km_low.fit(durations[~high], event_observed=events[~high], label="Lower Cox risk")
    km_high.fit(durations[high], event_observed=events[high], label="Higher Cox risk")
    lr = logrank_test(durations[high], durations[~high], event_observed_A=events[high], event_observed_B=events[~high])
    ax = km_low.plot_survival_function(ci_show=True, color="#3C78A5", linewidth=2)
    km_high.plot_survival_function(ax=ax, ci_show=True, color="#C66D4A", linewidth=2)
    ax.set_title("Kaplan–Meier survival by full-cohort Cox risk group")
    ax.set_xlabel("Days from diagnosis")
    ax.set_ylabel("Estimated survival probability")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=.2)
    ax.figure.tight_layout()
    ax.figure.savefig(output / "kaplan_meier.png", dpi=180, bbox_inches="tight")
    plt.close(ax.figure)
    return {"risk_grouping": "median full-cohort Cox partial hazard", "n_higher_risk": int(high.sum()),
            "n_lower_risk": int((~high).sum()), "logrank_statistic": float(lr.test_statistic),
            "logrank_p_value": float(lr.p_value),
            "interpretation": "Descriptive split and curves use the complete cohort; not out-of-fold validation."}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, help="Input CSV; omit only with --demo")
    ap.add_argument("--demo", action="store_true", help="Run on generated synthetic data (not clinical evidence)")
    ap.add_argument("--threshold", type=float, default=270, help="High-risk event horizon in days")
    ap.add_argument("--folds", type=int, default=5, help="Stratified folds for classifiers; K folds for Cox")
    ap.add_argument("--seed", type=int, default=229)
    ap.add_argument("--output", type=Path, default=Path("outputs"))
    ap.add_argument("--tune", action="store_true", help="Run nested 3-fold hyperparameter search inside the outer CV at the selected horizon")
    args = ap.parse_args()
    if args.demo == bool(args.data):
        ap.error("Provide exactly one of --demo or --data")
    df = make_demo(seed=args.seed) if args.demo else pd.read_csv(args.data)
    needed = {"duration", "event"}
    if not needed.issubset(df.columns):
        ap.error("CSV must include duration and event columns")
    df = df.dropna(subset=["duration", "event"]).copy()
    df["duration"] = pd.to_numeric(df["duration"], errors="raise")
    df["event"] = pd.to_numeric(df["event"], errors="raise").astype(int)
    if (df.duration <= 0).any() or not set(df.event.unique()).issubset({0, 1}):
        ap.error("duration must be positive and event must contain only 0/1")
    args.output.mkdir(parents=True, exist_ok=True)
    classifier_tables, sweep_meta = [], []
    horizons = list(dict.fromkeys([240, 270, 300, 330, 360, args.threshold]))
    for horizon in horizons:
        try:
            table, meta = classifier_scores(df, horizon, args.folds, args.seed)
            classifier_tables.append(table)
            sweep_meta.append(meta)
        except ValueError as exc:
            warnings.warn(f"Skipping {horizon}-day classifier comparison: {exc}")
    if not classifier_tables:
        ap.error("Could not evaluate any threshold; inspect class counts or reduce --folds")
    all_classifiers = pd.concat(classifier_tables, ignore_index=True)
    cls = all_classifiers.loc[all_classifiers.threshold_days == args.threshold]
    if cls.empty:
        warnings.warn(f"Requested threshold {args.threshold:g} days not in sweep; using closest evaluated horizon")
        nearest = all_classifiers.threshold_days.iloc[(all_classifiers.threshold_days - args.threshold).abs().argmin()]
        cls = all_classifiers.loc[all_classifiers.threshold_days == nearest]
    surv = survival_models(df, args.folds, args.seed, args.output)
    km = risk_group_kaplan_meier(df, args.output)
    selected_threshold = float(cls.threshold_days.iloc[0])
    selected_known = {"n_known": int(((df.duration >= selected_threshold) | ((df.duration < selected_threshold) & (df.event == 1))).sum()),
                      "n_excluded_censored_before_threshold": int(((df.duration < selected_threshold) & (df.event == 0)).sum())}
    cls.to_csv(args.output / "classifier_results.csv", index=False)
    all_classifiers.to_csv(args.output / "classifier_threshold_sweep.csv", index=False)
    surv.to_csv(args.output / "survival_results.csv", index=False)
    (args.output / "run_metadata.json").write_text(json.dumps({"synthetic_demo": args.demo, "rows": len(df), "events": int(df.event.sum()), "censored": int((df.event == 0).sum()), "threshold_days": selected_threshold, "folds": args.folds, "seed": args.seed, **selected_known}, indent=2) + "\n")
    (args.output / "logrank.json").write_text(json.dumps(km, indent=2) + "\n")
    if args.tune:
        tuned, params = tuned_classifier_scores(df, selected_threshold, args.folds, args.seed)
        tuned.to_csv(args.output / "classifier_tuned_results.csv", index=False)
        params.to_csv(args.output / "classifier_tuned_params.csv", index=False)
        print("\nNested hyperparameter tuning results at selected threshold:\n", tuned.to_string(index=False))
        print("\nFold-specific best parameters saved to classifier_tuned_params.csv")
    print("Classifier CV results at selected threshold:\n", cls.to_string(index=False))
    print("\nThreshold sweep saved to outputs/classifier_threshold_sweep.csv")
    print("\nSurvival CV results:\n", surv.to_string(index=False))
    print("\nKaplan–Meier log-rank result:\n", json.dumps(km, indent=2))
    if args.demo:
        print("\nNOTE: synthetic demonstration only; do not present these results as replication findings.")


if __name__ == "__main__":
    main()
