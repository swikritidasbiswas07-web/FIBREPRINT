# FIBREPRINT MVP roadmap

## Included in this ZIP
- Responsive React + Vite frontend in the approved scientific-editorial / textile-lab style.
- Functional fabric profile and first wash scenario form.
- Functional second-wash comparison controls (no invented release figures).
- FastAPI health, evidence, research-readiness and CSV schema-validation endpoints.
- Three DOI-linked peer-reviewed sources, with study-specific limitations.
- A CSV template and API smoke tests.

## Recommended next steps

### Stage 1: evidence / ingestion
1. Extract data from supplementary tables or paper text, noting exact source and protocol.
2. Develop a robust observation schema with measured load mass, water-to-fabric ratio, fabric construction and uncertainty.
3. Add provenance traceability and a study-compatibility filter.

### Stage 2: scientific baseline
1. Add a transparent baseline (study median / simple regularised regression), where data volume permits.
2. Train candidate models only after assessing dataset size and leakage.
3. Evaluate MAE / RMSE on held-out studies or fabrics; assess prediction interval coverage.
4. Prevent unsupported out-of-distribution predictions.

### Stage 3: judges' prototype
1. Connect the validated model to /api/evaluate and enable numeric displays only when supported.
2. Compare real outcomes for different scenarios and link each estimate to evidence coverage.
3. Add optional material images: place properly licensed files in frontend/public/materials/ and reference them in UI.
4. Capture a walkthrough, test offline/slow networks, build and deploy.

## Stack
React 19, Vite 6, plain CSS, lucide-react, Python FastAPI, Pydantic. No database or paid API required for starter. No login in this phase.
