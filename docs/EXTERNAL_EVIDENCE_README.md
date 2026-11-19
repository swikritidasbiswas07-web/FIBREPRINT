# FIBREPRINT v0.23 — external evidence and validation gate

## What has been built

- Curated **candidate** source registry with source DOI links (`backend/external_study_registry.json`), not a database of independently tested observations.
- Strict standard-library external-data checker (`backend/audit_external_study.py`) to reject incompatible units, missing provenance, summary figures, unsupported measurement basis and incorrectly mixed studies.
- Empty **schema-only** transcription CSV (`backend/external_study_template.csv`). No measurements have been fabricated.
- Compact React source-evidence section (`frontend/src/ExternalEvidence.jsx` and `external-evidence.css`).
- An updated `ResearchResults.jsx` that reflects the completed structural alignment audit.
- An updated `App.jsx` based on the prior **v0.19** component state; if your local `App.jsx` has newer edits, do NOT overwrite it. Instead merge the new import and `<ExternalEvidence/>` after `<ResearchResults/>`.

## Install changed files

- Copy `audit_external_study.py`, `external_study_registry.json`, and `external_study_template.csv` into `FIBREPRINT/backend/`.
- Copy `ExternalEvidence.jsx`, `external-evidence.css`, and `ResearchResults.jsx` into `FIBREPRINT/frontend/src/`.
- If your App.jsx is based on v0.19, replace with the provided App.jsx. Otherwise, **merge only**:

```jsx
import ExternalEvidence from './ExternalEvidence';
```

and in the render alongside `<ResearchResults/>`:

```jsx
<ResearchResults/>
<ExternalEvidence/>
```

- No backend API or npm package changes required.

## Preparing an authentic external data file

Open the registry and original studies. Request/download their raw supplemental **individual fabric** measurements where available. Only transcribe readings for which the exact table, sheet or row is traceable. Leave unavailable fields empty, never guess experimental conditions. The audit requires: `study_id`, actual DOI, source locator, `record_type=individual_measurement`, distinct `fabric_id`, `wash_id`, measured mass `release_value`, `release_unit=mg/kg`, `measurement_basis=released_fibre_mass_per_kg_textile_per_wash`, collection method, washing protocol, composition and construction. GSM may be omitted if missing from the paper.

Never fill the template with study-level means, estimated fabric measurements, or unit conversions from fibre count. The original model cannot be externally tested until comparable row-level data and the feature definitions needed for that model have been verified.

```powershell
cd "C:\Users\suhit\Downloads\FIBREPRINT\backend"
.venv\Scripts\python.exe audit_external_study.py --csv data/external_study_observations.csv --study-id hazlehurst_2023 --out data/external_study_compatibility.json
```

The command should return exit status 2 for empty/incompatible data and 0 when at least one row passes *schema-only* checks. Either outcome still needs manual verification against the publication. No external model evaluation or calibrated uncertainty is implemented.

## Candidate suitability

| Candidate | Reported format | Interpretation |
|---|---|---|
| Vassilenko et al. 2021, DOI 10.1371/journal.pone.0250346 | 37 materials, 5 washes, mg/kg measurements | Current training/internal-study source; NOT external |
| Hazlehurst et al. 2023, DOI 10.1007/s11356-023-25246-8 | Fabric release mass in mg/kg with test-method comparisons | Priority for acquisition; protocols and raw observations require verification |
| Lant et al. 2020, DOI 10.1371/journal.pone.0233332 | Mixed household wash loads, mg/kg | Contextual external reference, not an individual-fabric ground truth |
| Evaluation of microfiber release from jeans, 2021 | Count and washing-condition findings | Useful contextual evidence, not automatically mass-comparable |

## Current scientific status

`RESEARCH_ONLY_NOT_DEPLOYABLE`. The original source audit passed, but the 20 internal grouped splits reused the same study. We have **not** obtained or benchmarked independently sourced fabric measurements yet. The front-end makes this distinction explicit.
