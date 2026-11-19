# FIBREPRINT v0.22 — Applicability & Abstention Audit

## Purpose
Evaluate the **pre-outcome applicability flags** produced by v0.21 on existing held-out predictions. No new model, feature selection, or warning threshold is fitted. This is not a deployment approval.

## Install
Place `analyze_applicability.py` in `FIBREPRINT/backend/`. Preserve your existing raw research files and model scripts. Dependencies are the already-installed NumPy and pandas.

From `FIBREPRINT/backend/` in PowerShell:

```powershell
.venv\Scripts\python.exe analyze_applicability.py --predictions data/vassilenko_group_conformal_predictions.csv --audit data/vassilenko_source_alignment.json
```

Outputs under `backend/data/`:
- `vassilenko_applicability_report.json`: summary of retained/flagged error, interval coverage, missed high-release measurements, reasons and 20 per-split results.
- `vassilenko_applicability_by_fabric.csv`: fabric/repetition-level results; multiple washes from a fabric are aggregated.

## Fixed warning rule
Flag if a test fabric has a categorical value absent from the **training** group or its GSM is outside the **training** range. The warning uses no measured release value. There is no post-hoc optimization of cutoffs.

## Reading the results

- **Retained** means the existing warning did not fire; it does *not* mean safe or accurate.
- **Flagged** means an input falls outside a simple training-data support check; it does *not* prove high shedding.
- **High release** is a retrospective outcome-defined group (measured release >=400 mg/kg), useful for error analysis but impossible to select ahead of a wash using its true release value.
- **Coverage** describes intervals from v0.21. They are exploratory and can be too wide to help decisions.
- Repeated 20-way splits reuse the same 37 fabrics: avoid statistical significance claims or treating all prediction rows as independent.
- If a desired cutoff is developed from these outcomes, it needs a different independent dataset for a fair evaluation.

## Next science task
Confirm the protocol and missing early-wash measurements from the publication, and seek an independent textile shedding study with comparable units and physical sample descriptors. Keep website status `RESEARCH_ONLY_NOT_DEPLOYABLE`.
