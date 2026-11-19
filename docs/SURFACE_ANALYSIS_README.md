# FIBREPRINT v0.17 — Surface Structure & High-Shedding Failure Analysis

**Scientific status: `RESEARCH_ONLY_NOT_DEPLOYABLE`.** This is a post-hoc, one-study model investigation; do not put the resulting predictions on the public website.

## Placement

Copy `analyze_surface_structure.py` to `FIBREPRINT/backend/`. Keep the existing `prepare_vassilenko.py`, `train_vassilenko.py`, `diagnose_vassilenko.py` and all frontend files unchanged.

## Run from `FIBREPRINT/backend` in PowerShell

```powershell
.venv\Scripts\python.exe analyze_surface_structure.py --oof data/vassilenko_oof_predictions.csv --csv data/vassilenko_extracted_washes.csv
```

Requires the same `numpy`, `pandas`, and `scikit-learn` dependencies installed for v0.16.

Outputs:

- `data/vassilenko_surface_analysis.json` — error analysis and exploratory fixed-split model comparison.
- `data/vassilenko_surface_comparison_oof.csv` — held-out predictions from **four** experimental approaches (original RF, RF + textual surface flags, Ridge, Ridge + textual flags).

To run **diagnostics only**, without retraining:

```powershell
.venv\Scripts\python.exe analyze_surface_structure.py --oof data/vassilenko_oof_predictions.csv
```

## What is being tested?

The script extracts transparent 0/1 keyword indicators from the original specimen **description text**:

- `explicit_raised_surface` matches *velour, pile, shaggy, brushed, fuzzy, napped, sanded, raised*.
- `fleece_term` matches *fleece*.
- `jersey_term` matches *jersey*.
- `woven_or_plaid_term` matches *woven, plaid, denim, twill*.

These are **not measured pile height, texture, or morphology**. They are exploratory metadata proxies and may reflect confounding factors or sample-specific language. Surface claims require independent physical measurements or manual verification.

Every model uses the **same five grouped folds**, so observations from one fabric never appear in both a training and a test group. We compare the existing Random Forest model against an augmented RF and a simpler regularised Ridge model, using the same base features and log1p release target. No test-held-out targets are included in the input features.

The script also reports:

- Error in observed-release bands of `<100`, `100–<400`, and `>=400` mg/kg. These are **post-hoc groups defined by measured outcomes**, never usable as prediction-time flags.
- Wash-specific error summaries, noting early-wash missingness.
- A sensitivity comparison excluding the two most difficult fabrics from **already generated** OOF predictions, explicitly **without retraining** and without claiming a fair model benchmark.
- Per-text-keyword descriptive error groups.

## Interpretation safeguards

1. A lower MAE for the augmented model would be a preliminary observation, **not proof** that fibre surface morphology *causes* higher shedding or that it generalises to other studies.
2. The specific hypothesis follows examination of earlier OOF errors; therefore the ablation is **exploratory** and should be checked using new held-out fabrics or independent studies.
3. The source extraction is still marked `EXTRACTED_UNVERIFIED` and must be checked against the workbook and methods.
4. Do not drop high-release specimens to improve reported accuracy.
5. Do not infer wash temperature or water ratio from this workbook; neither is a recorded row-wise feature.
6. No saved deployable model is created.

## What to share next

Upload `vassilenko_surface_analysis.json` and, if feasible, `vassilenko_surface_comparison_oof.csv`. We will compare the matched-fold results and decide whether feature engineering warrants deeper research.
