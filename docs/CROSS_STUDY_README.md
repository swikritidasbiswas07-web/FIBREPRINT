# FIBREPRINT v0.24 — Cross-study protocol gate

This adds **no UI changes and no publicly deployed model**. It introduces an auditable decision record about whether external observations can be used for predictive testing.

## Put these files here

- `backend/cross_study_protocols.json`
- `backend/check_cross_study_gate.py`
- `docs/CROSS_STUDY_README.md` (create `docs/` if needed)

## Run

From `C:\Users\suhit\Downloads\FIBREPRINT\backend`:

```powershell
.venv\Scripts\python.exe check_cross_study_gate.py --candidate hazlehurst_2023
```

Output: `backend/data/cross_study_gate_report.json`.

**Expected:** `BLOCKED_EXTERNAL_VALIDATION`. This is a successful functioning gate, not a coding error. It correctly refuses to invent external predictions from inaccessible replicate-level measurements.

## What was verified from the published article

Hazlehurst et al. (2023), DOI: https://doi.org/10.1007/s11356-023-25246-8

- Gyrowash simulated laundering apparatus with controlled 40 rpm rotation, distinct from the domestic washer protocol in Vassilenko et al. (2021).
- Fabric-variable experiment: 16 fabric types, generally 24 replicates each (PET_1: 8), 40 °C, 45 minutes, 15 L/m² liquor ratio, 50 steel balls, distilled water and no detergent.
- Outcome normalised to **mg released fibre per kg textile**; cited results are **means with 95% confidence intervals**, not individual machine-learning rows.
- Article prose reports **180 ± 11 mg/kg** (PET-VIS-ELA) to **2412 ± 222 mg/kg** (PET_1).
- The published **Data availability** statement says “Not applicable”. We could not verify a downloadable raw replicate-level dataset; **absence of a discoverable dataset does not prove the authors have no raw data**.

The published summary observations are recorded in the JSON **for context only**. Neither is a new dataset row, and neither is input to the model.

## Scientific decision

The existing study is 37 textile specimens and 155 mass-release records, structurally checked against the original workbook. The external paper has meaningful quantitative findings but **different apparatus and no verified individual replicate dataset**. No fair out-of-study predictive accuracy can yet be claimed.

The next meaningful step is to request anonymised raw specimen-level release observations (and metadata/protocols) from the corresponding author, or locate another independently archived release-mass dataset with enough compatible fabric fields.

No missing values should be replaced with zero, and no plotted means should be treated as replicate-level measurements.
