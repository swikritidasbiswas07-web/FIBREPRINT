# FIBREPRINT v0.21 — Fabric-group split-conformal evaluation

## What this does

Runs 20 exploratory **train / calibration / test** partitions, grouped by `fabric_id` so every wash for a fabric remains in exactly one set within each partition. Fits the previously selected Ridge + description-keyword model using **training fabrics only**, calculates a **maximum absolute prediction error per calibration fabric** and uses a finite-sample order statistic to construct symmetric (clipped-at-zero) error bands on unseen test fabrics. All imputation and scaling are fit on training data only.

The calibration target is simultaneous coverage of all *recorded* washes of a randomly sampled fabric, subject to assumptions that are not yet validated for this dataset. It is not a verified consumer prediction interval. All results remain **RESEARCH_ONLY_NOT_DEPLOYABLE**.

## Install

Place `check_group_conformal.py` in `backend/`. Keep your existing `backend/data/vassilenko_extracted_washes.csv` and `backend/data/vassilenko_source_alignment.json`.

From the `backend/` directory:

```powershell
.venv\Scripts\python.exe check_group_conformal.py --csv data/vassilenko_extracted_washes.csv --audit data/vassilenko_source_alignment.json
```

Outputs:

- `backend/data/vassilenko_group_conformal.json`
- `backend/data/vassilenko_group_conformal_predictions.csv`

Upload both after running. No changes to your React app, authentication, API or public prediction status.

## Interpretation

- **Test fabric coverage**: fraction of test fabrics for which *every available measured wash* lies within its band.
- **Test observation coverage**: fraction of individual test washes inside the band. Correlated washes do not make independent samples.
- **High-release coverage**: retrospective evaluation using the observed outcome >=400 mg/kg, **never** an inference-time classification.
- **Applicability flag**: descriptive notice from input features available ahead of prediction; it flags unseen training categories or density outside the training range. It does **not** establish model reliability for unflagged fabrics.
- **Band half-width**: error amount added/subtracted from the prediction (with negative release clipped at zero). Extremely wide bands can provide poor decision support.

## Serious limitations

The research team chose Ridge and keywords after examining earlier errors in this same study. Splitting those observations anew does **not** undo that selection bias or create an independent external dataset. Some source workbook measurements for early washes are absent; this requires paper/protocol review. Conformal ranks rely on exchangeability of fabric-level samples, which is not established. The output is an exploratory diagnostic, **not guaranteed 90% coverage, not a calibrated deployment artifact and not a safety certification**.
