# Data

The reference report's Stanford cohort is not distributed with this assignment. The included download script retrieves the open-access TCGA Pan-Cancer Clinical Data Resource (TCGA-CDR) workbook from the National Cancer Institute and filters the pancreatic adenocarcinoma (PAAD) cohort. This is a public substitute cohort, not the Jamalian cohort; it has clinical data and does not include the report's 900 radiomic features.

Run from the repository root:

```bash
python data/download_tcga.py
```

The script writes `data/private/tcga_paad.csv`. That data file is excluded from Git by `.gitignore`; check applicable TCGA data-use terms before sharing derived data. The source page and data resource are documented at https://gdc.cancer.gov/about-data/publications/PanCan-Clinical-2018 .

The generated CSV contains `duration` (OS.time, days), `event` (OS: 1=death, 0=censored), and clinical predictors prefixed with `clinical_`. Clinical variables with missing or ambiguous coding are excluded by the downloader. Use a fixed seed and report the selected outcome and feature definitions in the write-up.

The larger MSK extension uses public cBioPortal study `pdac_msk_2024`. Run `python data/download_msk_paad.py` to prepare `data/private/msk_paad_2024.csv`. Both downloaded patient tables are local inputs and intentionally excluded from Git; the download scripts regenerate them.
