# FIBREPRINT v0.18 — Fabric-grouped robustness study

**Status: research-only.** The Figshare workbook extraction has not been manually source-verified. This script never enables inference on the public website.

## Files
Place `check_model_robustness.py` in `backend/` and keep the existing `backend/data/vassilenko_extracted_washes.csv` unchanged.

## Run
From the `backend` directory:

```powershell
.venv\Scripts\python.exe check_model_robustness.py --csv data/vassilenko_extracted_washes.csv
```

The default is 20 repeated train/test partitions, each holding out 25% of distinct fabrics. All wash observations for a fabric stay together *within each split*. It evaluates **the same two preselected estimators** on each split: original Random Forest and Ridge with description-keyword indicators. Fitting is restricted to the training groups; there is no hyperparameter tuning in the script.

## Outputs
- `data/vassilenko_robustness.json`: individual split errors and a descriptive summary.
- `data/vassilenko_robustness_predictions.csv`: every test observation for every split, with paired predictions.

A fabric may occur in the test set in multiple different repetitions. Hence these are **dependent resamples**, and the percentile range is NOT a confidence interval or a p-value. This is an exploratory stability check, not external validation. The script does not calculate validated uncertainty intervals or qualify a model for deployment.

## Interpretation
- Check `ridge_better_splits / total_splits`; high proportions suggest better split-to-split stability, but do **not** prove statistical significance.
- `paired_mae_difference_median_ridge_minus_rf < 0` means Ridge had lower MAE for a typical tested split.
- Inspect extreme or high-release holdouts separately before deciding to adopt Ridge.
- Manually verify extracted workbook rows, missing washes, category definitions, and units before making scientific claims.
