# FIBREPRINT v0.19 — source alignment and research ledger

## Files to install (only changed/new files)

| File | Location | Action |
|---|---|---|
| `audit_source_alignment.py` | `backend/audit_source_alignment.py` | New |
| `App.jsx` | `frontend/src/App.jsx` | Replace (from v0.13 model-integrated App) |
| `ResearchResults.jsx` | `frontend/src/ResearchResults.jsx` | New |
| `research-results.css` | `frontend/src/research-results.css` | New |
| `VALIDATION_CHECKPOINT.md` | `docs/VALIDATION_CHECKPOINT.md` | New |

**Important:** `App.jsx` is derived from the v0.13 model-integrated version, including the Material Passport. If you made your own edits to App.jsx since that version, compare/merge before replacing. The added lines are:

```jsx
import ResearchResults from './ResearchResults';
// ... inside the app, immediately before <MicroscopeExplorer/>:
<ResearchResults/>
```

The results component itself imports its CSS.

## Step 1 — Structural audit

From `FIBREPRINT/backend`, run:

```powershell
.venv\Scripts\python.exe audit_source_alignment.py --xlsx data/source_figshare_14675760_v4/figshare_microfiber_data.xlsx --csv data/vassilenko_extracted_washes.csv
```

Report: `backend/data/vassilenko_source_alignment.json`.

What it checks:
- Original XLSX source SHA-256 against every extracted row.
- Mass [mg/kg] Y–AC and count [fiber/kg] AF–AJ header/unit mapping.
- Each source Excel row + wash index, exact source mass and count numeric values.
- Duplicate/missing extracted records, missing source measurements and record counts.
- Does not insert zeros, infer missing conditions or alter the source workbook.

`STRUCTURAL_AUDIT_PASS` validates the **extractor's cell-by-cell fidelity only**. It does **not** confirm that the source metadata or measurement protocols were interpreted correctly. The physical paper, methods and supplementary file should be reviewed manually. The observed 30 missing mass cells require an explanation from the original source before training claims are strengthened.

A failed audit returns a nonzero exit code and records offending Excel rows in JSON.

## Step 2 — Frontend research record

From `FIBREPRINT/frontend`:

```powershell
npm.cmd run dev
```

Scroll to the new `Research Record` section (near the research library/microscope). This display is a **static historical snapshot** based on the user-generated v0.17 and v0.18 research JSON files. It deliberately does not call the prediction endpoint or alter the model status. Do not update results without a documented, reproducible rerun and clear version tag.

## What isn't solved yet

- Protocol and missingness verification against original publication.
- External validation on independent studies, before any real-world claims.
- Predictive uncertainty and applicability bounds.
- Single-study sample count is 37 independent fabrics, not 155 independent textiles.
- No internet download or live browser build was performed in this environment.
