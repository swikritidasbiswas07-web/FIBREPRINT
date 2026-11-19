# FIBREPRINT v0.16 — research-only model diagnostics

This is **not a newly validated model** and changes no website code.

## Install

Copy `diagnose_vassilenko.py` into `FIBREPRINT/backend/` alongside `train_vassilenko.py`.

From the `backend` directory in PowerShell:

```powershell
.venv\Scripts\python.exe diagnose_vassilenko.py --csv data/vassilenko_extracted_washes.csv
```

The script regenerates the **same** 5-fold fabric-grouped Random Forest evaluation, creating:

- `data/vassilenko_diagnostics.json`: metrics overall, by held-out fold, and by wash; worst-error fabrics/observations; missing wash coverage; measurement distribution.
- `data/vassilenko_oof_predictions.csv`: one held-out prediction per experimental observation, with source Excel row, fabric ID, wash number, median baseline, and signed/absolute error.

**Send both outputs for review.** The code does not modify the source Excel workbook, trained model status, frontend, or your existing research metrics JSON.

## How to interpret

- Compare `overall.model_mae_mg_per_kg` against the original `vassilenko_research_metrics.json`. Results should agree (modulo minor floating-point differences). If they don't, STOP: evaluate which inputs/scripts differ.
- `by_wash` reveals whether errors cluster in particular wash cycles, but the wash 1–2 groups are smaller and missingness is not assumed random.
- `worst_10_fabrics` helps identify outlying specimens. Do not remove them merely to improve R².
- All held-out records from a given `fabric_id` are in the **same fold** to prevent repeated-wash leakage.
- Source extraction is still marked `EXTRACTED_UNVERIFIED`, and no model inference API is enabled on its basis.

## Limitations

The dataset includes missing wash observations and unverified metadata. A one-study validation cannot establish out-of-study performance or calibrated prediction intervals. Do not publish numerical predictions as environmental impact claims.
