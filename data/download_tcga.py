#!/usr/bin/env python3
"""Download and prepare open-access TCGA-CDR PAAD clinical survival data."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
import pandas as pd

FILE_ID = "1b5f413e-a8d1-4d10-92eb-7c4ae739ed81"
URL = f"https://api.gdc.cancer.gov/data/{FILE_ID}"
DEST = Path(__file__).resolve().parent / "private" / "tcga_paad.csv"


def norm(name: object) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def main() -> None:
    with urlopen(URL, timeout=120) as response:
        workbook_bytes = response.read()
    book = pd.ExcelFile(BytesIO(workbook_bytes))
    chosen = None
    for sheet in book.sheet_names:
        candidate = pd.read_excel(book, sheet_name=sheet)
        candidate.columns = [norm(c) for c in candidate.columns]
        if {"type", "os", "os.time"}.issubset(candidate.columns):
            chosen = candidate
            break
    if chosen is None:
        raise RuntimeError(f"Could not find TCGA-CDR sheet with type, OS, and OS.time columns. Sheets: {book.sheet_names}")
    df = chosen.loc[chosen["type"].astype(str).str.upper().eq("PAAD")].copy()
    df["duration"] = pd.to_numeric(df["os.time"], errors="coerce")
    df["event"] = pd.to_numeric(df["os"], errors="coerce")
    df = df.loc[df.duration.gt(0) & df.event.isin([0, 1])].copy()
    # Harmonize a deliberately small, interpretable clinical subset. Original
    # source columns remain untouched until selection below.
    aliases = {
        "age_at_initial_pathologic_diagnosis": "age",
        "gender": "gender",
        "ajcc_pathologic_tumor_stage": "stage",
        "tumor_grade": "grade",
        "histological_type": "histology",
        "race": "race",
    }
    cols = ["duration", "event"]
    for source, target in aliases.items():
        if source in df.columns:
            df["clinical_" + target] = df[source]
            if target == "age":
                df["clinical_" + target] = pd.to_numeric(df["clinical_" + target], errors="coerce")
            cols.append("clinical_" + target)
    result = df[cols].replace({"--": pd.NA, "[Not Available]": pd.NA, "[Not Evaluated]": pd.NA})
    DEST.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(DEST, index=False)
    print(f"Saved {len(result)} PAAD records to {DEST}")
    print(f"Observed deaths: {int(result.event.sum())}; censored: {int((result.event == 0).sum())}")
    print(f"Predictors: {', '.join(cols[2:])}")


if __name__ == "__main__":
    main()
