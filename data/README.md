# MSK 2024 Data

The project uses the public cBioPortal study `pdac_msk_2024` as its sole real-patient cohort. Run from the repository root:

```bash
python data/download_msk_paad.py
```

The script writes `data/private/msk_paad_2024.csv`. Raw patient-level data are local inputs and are excluded from Git. The source dataset is available at [cBioPortal PDAC MSK 2024](https://www.cbioportal.org/study/summary?id=pdac_msk_2024).

The generated CSV contains `duration` (overall-survival follow-up converted from months to days), `event` (1 = recorded death, 0 = right-censored), and `clinical_` predictor columns. The downloader retains patients with known survival time/status and positive follow-up. For the 270-day classification task, records censored before the cutoff are excluded because their label is unknown.
