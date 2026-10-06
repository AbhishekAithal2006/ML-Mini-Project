#!/usr/bin/env python3
"""Download and prepare public cBioPortal MSK pancreatic cohort clinical data."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

API = "https://www.cbioportal.org/api"
STUDY = "pdac_msk_2024"
FEATURES = [
    "AGE", "SEX", "STAGE", "GENOMIC_GROUP", "TUMOR_LOCATION",
    "TOBACCO_EXPOSURE", "DIABETES_HISOTRY", "PANCREATITIS_HISOTRY",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/private/msk_paad_2024.csv"))
    args = parser.parse_args()
    url = (f"{API}/studies/{STUDY}/clinical-data?clinicalDataType=PATIENT"
           "&projection=SUMMARY&pageSize=1000000&pageNumber=0")
    with urlopen(url, timeout=90) as response:
        records = json.load(response)
    patients: dict[str, dict[str, str]] = defaultdict(dict)
    for row in records:
        patients[row["patientId"]][row["clinicalAttributeId"]] = row["value"]

    rows = []
    for patient in patients.values():
        if not patient.get("OS_MONTHS") or not patient.get("OS_STATUS"):
            continue
        duration = float(patient["OS_MONTHS"]) * 30.4375
        # Cox fitting requires positive time; omit zero-month records.
        if duration <= 0:
            continue
        row = {
            "duration": duration,
            "event": int(patient["OS_STATUS"].startswith("1:")),
        }
        for feature in FEATURES:
            name = "clinical_gender" if feature == "SEX" else f"clinical_{feature.lower()}"
            row[name] = patient.get(feature)
        rows.append(row)

    result = pd.DataFrame(rows)
    result["clinical_age"] = pd.to_numeric(result["clinical_age"], errors="coerce")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"Saved {len(result)} patients ({int(result.event.sum())} deaths, "
          f"{int((result.event == 0).sum())} censored) to {args.output}")


if __name__ == "__main__":
    main()
