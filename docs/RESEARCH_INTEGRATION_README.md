# FIBREPRINT v0.25 — Research status integration (no UI redesign)

## Individual file placement

- `backend/app/research_status.py` → `FIBREPRINT/backend/app/research_status.py` **NEW**
- `frontend/src/ResearchStatus.jsx` → `FIBREPRINT/frontend/src/ResearchStatus.jsx` **NEW**
- `backend/install_v25.py` → `FIBREPRINT/backend/install_v25.py` **NEW**
- `backend/fix_applicability_v22.py` → `FIBREPRINT/backend/fix_applicability_v22.py` **NEW**, optional but recommended
- this file → `FIBREPRINT/docs/RESEARCH_INTEGRATION_README.md`

Keep all your existing `App.jsx`, `main.py`, authentication, UI, fabric photographs, and models. **Do not overwrite them.** The installer edits only the original files, saves backups, and can be run again safely.

## Run from PowerShell

```powershell
cd "C:\Users\suhit\Downloads\FIBREPRINT\backend"
.venv\Scripts\python.exe install_v25.py
.venv\Scripts\python.exe fix_applicability_v22.py
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Restart the frontend from a separate terminal if needed:

```powershell
cd "C:\Users\suhit\Downloads\FIBREPRINT\frontend"
npm.cmd run dev
```

## What should change

- The evidence ledger now displays a `ResearchStatus` panel, replacing the old `NOT TRAINED` readout. Research evaluation and public model deployment are **different** statuses.
- The new authenticated endpoint is `GET /api/research/status`. Because it requires a user token, test it in the app or FastAPI `/docs` with authentication. Browsing the URL without a token should return 401/403.
- When present in `backend/data`, source-integrity, grouped conformal, applicability, and external gate JSON reports are read, not modified.
- The workbench remains non-predictive. The original `/api/model/status` API may still say `NOT_TRAINED` for a *serving artifact*; this is technically correct and is now labelled more clearly in the UI.
- The optional v0.22 field patch corrects a counting **label**, not measured errors or the underlying study.

## Required report locations

Place these existing research JSON reports in `FIBREPRINT/backend/data/` if not already present:

- `vassilenko_source_alignment.json`
- `vassilenko_group_conformal.json`
- `vassilenko_applicability_report.json`
- `cross_study_gate_report.json`

If a report is missing or inconsistent, the UI shows `NOT VERIFIED` / `REPORT NOT FOUND`, not a fabricated success. The external validation gate must remain blocked until valid independent observations and reviewed protocols exist.

## Browser checks

1. Sign in, go to the Research Ledger, and verify `RESEARCH ONLY — NOT DEPLOYABLE` and `155 / 155 MATCHED` (if the audit report is present).
2. Confirm grouped conformal and applicability status are `RUN AND DOCUMENTED` *only* if the source-aligned reports are installed. The prior applicability report misnamed 12 detected failures as “missed”; the correct diagnostic counts are **12 flagged, 16 unflagged, 28 total**.
3. Verify External Evidence, microscope, fabric passports, login/logout and the four-step workbench remain unchanged.
4. Verify that trying to evaluate a fabric does **not** return a numerical model estimate.
5. Open browser DevTools Network: `/api/research/status` should return 200 after login (401/403 before login). Check both terminals for errors.

## Safety and interpretation

The source alignment is structural, not a peer review of laboratory protocols. Grouped calibration remains exploratory; the same 37 fabrics were reused across model choices. Predicted intervals are often too wide and can miss high-shedding cases. No external predictive performance is claimed. None of these scripts trains or deploys a model.

## Undo

For each edited file, the installer creates `main.py.before_v25.bak` or `App.jsx.before_v25.bak` alongside it. Restore the backup only if needed and restart the relevant service. The optional applicability fixer likewise saves `.before_v25.bak` copies of files it modifies.
