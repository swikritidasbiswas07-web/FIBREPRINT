"""FIBREPRINT API — evidence-first MVP scaffold.

No prediction is claimed before compatible experimental observations have
been collected and an independently evaluated model is integrated.
"""
from pathlib import Path
import csv
import io
from typing import Literal
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from .auth import RegisterRequest, LoginRequest, current_user, register, login, logout
from .model_engine import model_status, evaluate_model
from .research_status import router as research_router

app = FastAPI(title="FIBREPRINT Research API", version="0.13.0")
app.include_router(research_router)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])

SOURCES = [
    {"id":"napper-2016","authors":"Napper & Thompson","year":2016,"title":"Release of synthetic microplastic plastic fibres from domestic washing machines: Effects of fabric type and washing conditions","journal":"Marine Pollution Bulletin","doi":"10.1016/j.marpolbul.2016.09.025","finding":"An average 6 kg acrylic wash load was estimated to release over 700,000 fibres under the studied conditions.","limitation":"Not a universal per-wash emission factor."},
    {"id":"defalco-2019","authors":"De Falco et al.","year":2019,"title":"The contribution of washing processes of synthetic clothes to microplastic pollution","journal":"Scientific Reports","doi":"10.1038/s41598-019-43023-x","finding":"Measured release varied across tested synthetic garments, ranging from 124 to 308 mg per kg of washed fabric.","limitation":"Garment and protocol specific; not transferable without checking compatibility."},
    {"id":"kelly-2019","authors":"Kelly et al.","year":2019,"title":"Importance of Water-Volume on the Release of Microplastic Fibers from Laundry","journal":"Environmental Science & Technology","doi":"10.1021/acs.est.9b03022","finding":"In the tested first-wash comparison, the higher-water-volume delicate cycle released approximately 800,000 more fibres than the lower-water-volume standard cycle.","limitation":"This is a cycle difference under specific test conditions, not a guaranteed effect of every delicate cycle."},
    {"id":"gliaudelyte-2025","authors":"Gliaudelytė et al.","year":2025,"title":"Impact of textile composition, structure, and treatment on microplastic release during washing: a review","journal":"Textile Research Journal","doi":"10.1177/00405175241260066","finding":"A review finds that fibre content, yarn construction, fabric structure and treatments all affect fibre release.","limitation":"Literature review; findings are conditional on materials and methods."},
    {"id":"chem-2025","authors":"Critical review (2025)","year":2025,"title":"Critical review of microfiber release from textiles: Results, comparative challenges, mitigation strategies, and legislative perspectives","journal":"Chemosphere","doi":"10.1016/j.chemosphere.2025.144394","finding":"Testing methods and reporting units differ across studies, creating challenges for direct comparison.","limitation":"Literature review; not a unified set of raw modelling observations."},
]

class Fabric(BaseModel):
    name: str = Field(default="Untitled specimen", min_length=1, max_length=90)
    primary_fibre: Literal["polyester","cotton","acrylic","polyamide","blend","other"] = "polyester"
    construction: Literal["knit","woven","fleece","unknown"] = "knit"
    gsm: float | None = Field(default=None, gt=0, le=1500)
    wash_count: int | None = Field(default=None, ge=0, le=1000)

class Wash(BaseModel):
    load_mass_kg: float | None = Field(default=None, gt=0, le=30)
    measurement_method: str | None = Field(default=None, max_length=80)
    temperature_c: float = Field(default=30, ge=0, le=95)
    duration_min: int = Field(default=45, ge=1, le=360)
    water_l: float | None = Field(default=None, gt=0, le=400)
    cycle: Literal["normal","delicate","heavy"] = "normal"

class StudyRequest(BaseModel):
    fabric: Fabric
    wash: Wash

class CSVValidateRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=500000)

REQUIRED_COLUMNS = ["study_id","fabric_id","fibre_type","construction","temperature_c","water_fabric_ratio","wash_number","release_mg_per_kg","measurement_method"]

@app.post("/api/auth/register", status_code=201)
def register_account(payload: RegisterRequest):
    return register(payload)

@app.post("/api/auth/login")
def sign_in(payload: LoginRequest):
    return login(payload)

@app.get("/api/auth/me")
def session_user(user=Depends(current_user)):
    return user

@app.post("/api/auth/logout")
def sign_out(result=Depends(logout)):
    return result

@app.get("/api/health")
def health():
    return {"status":"ok","product":"FIBREPRINT","phase":"pre-validation"}

@app.get("/api/model/status")
def get_model_status(user=Depends(current_user)):
    return model_status()

@app.get("/api/sources")
def sources():
    return {"items":SOURCES,"note":"Findings are context-specific and are not model outputs."}

@app.post("/api/evaluate")
def evaluate(request: StudyRequest, user=Depends(current_user)):
    """Return evidence readiness, not synthetic predictions."""
    missing = []
    if request.fabric.gsm is None: missing.append("Fabric GSM has not been supplied")
    if request.fabric.wash_count is None: missing.append("Prior wash count has not been supplied")
    if request.wash.water_l is None: missing.append("Water volume has not been supplied")
    if request.fabric.construction == "unknown": missing.append("Fabric construction is unspecified")
    if request.wash.load_mass_kg is None: missing.append("Wash load mass has not been supplied; water/fabric ratio is unavailable")
    if not request.wash.measurement_method: missing.append("Measurement protocol is not confirmed")
    result = evaluate_model(
        fibre_type=request.fabric.primary_fibre,
        construction=request.fabric.construction,
        temperature_c=request.wash.temperature_c,
        water_fabric_ratio=(request.wash.water_l / request.wash.load_mass_kg)
            if request.wash.water_l is not None and request.wash.load_mass_kg is not None else None,
        wash_number=request.fabric.wash_count,
        measurement_method=request.wash.measurement_method,
    )
    return {
        "fabric": request.fabric.model_dump(),
        "wash": request.wash.model_dump(),
        "prediction": result["prediction"],
        "prediction_unit": "mg/kg fabric",
        "prediction_status": ("NOT_VALIDATED" if result["prediction_status"] == "NOT_TRAINED" else result["prediction_status"]),
        "message": result["message"],
        "interval": result.get("interval"),
        "interval_label": result.get("interval_label"),
        "model_info": result["model_info"],
        "missing_context":missing,
        "evidence_links":["napper-2016","defalco-2019","kelly-2019"],
        "next_steps":["Curate protocol-compatible study observations", "Establish a simple baseline and train candidate models", "Validate error and prediction-interval coverage on held-out data"],
    }

@app.post("/api/validate-csv")
def validate_csv(payload: CSVValidateRequest, user=Depends(current_user)):
    try:
        reader = csv.DictReader(io.StringIO(payload.csv_text))
        columns = reader.fieldnames or []
        missing = [col for col in REQUIRED_COLUMNS if col not in columns]
        rows = list(reader)
    except (csv.Error, UnicodeError) as exc:
        raise HTTPException(400, f"CSV parsing failed: {exc}") from exc
    problems = []
    for index,row in enumerate(rows[:500],start=2):
        for field in ("temperature_c","release_mg_per_kg"):
            val=(row.get(field) or "").strip()
            if val:
                try:
                    if float(val)<0: problems.append(f"Row {index}: {field} must not be negative")
                except ValueError:
                    problems.append(f"Row {index}: {field} is not numeric")
        if not (row.get("study_id") or "").strip(): problems.append(f"Row {index}: missing study_id")
    return {"valid":not missing and not problems,"row_count":len(rows),"missing_columns":missing,"problems":problems[:20],"required_columns":REQUIRED_COLUMNS,"note":"Passing schema checks does not prove scientific compatibility or data quality. Uploaded CSV is not retained."}
