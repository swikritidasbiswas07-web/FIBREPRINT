"""FIBREPRINT v0.23: read-only external study compatibility / provenance gate.

No web scraping, no invented experimental data, no prediction or model fitting.
Uses only the Python standard library. Require human transcription and source tracing.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["study_id","source_doi","source_locator","record_type","fabric_id","wash_id",
          "release_value","release_unit","measurement_basis","collection_method",
          "wash_protocol","fabric_composition","fabric_construction","gsm","notes"]
CANONICAL_UNIT = "mg/kg"
CANONICAL_BASIS = "released_fibre_mass_per_kg_textile_per_wash"


def clean(value):
    return str(value or "").strip()


def audit(path, study_id, original_study_id="vassilenko_2021"):
    raw = path.read_bytes()
    result = {"status":"NOT_READY_FOR_EXTERNAL_VALIDATION", "analysis":"EXTERNAL_STUDY_COMPATIBILITY_AUDIT",
              "scientific_status":"RESEARCH_ONLY_NOT_DEPLOYABLE", "created_utc":datetime.now(timezone.utc).isoformat(),
              "source_csv":str(path),"source_csv_sha256":hashlib.sha256(raw).hexdigest(),
              "target_study_id":study_id,"rows_read":0,"eligible_rows":0,"unique_fabrics_eligible":0,
              "errors":[],"warnings":[],"reason_counts":{},"eligible_row_ids":[],
              "limitations":["Compatibility does not imply comparable experimental conditions or independent generalisation.",
                             "This audit cannot establish source transcription correctness without manual source-cell/table verification.",
                             "This audit does not train, calibrate or evaluate a model."]}
    with path.open("r",encoding="utf-8-sig",newline="") as fh:
        reader=csv.DictReader(fh)
        if not reader.fieldnames:
            result["errors"].append("CSV has no header")
            return result
        missing=sorted(set(FIELDS)-set(reader.fieldnames))
        if missing:
            result["errors"].append("Missing mandatory columns: "+", ".join(missing))
            return result
        seen=set(); eligible=set(); reasons=Counter(); studies=set()
        for idx,row in enumerate(reader,start=2):
            result["rows_read"] += 1
            row = {key:clean(value) for key,value in row.items() if key is not None}
            issues=[]
            sid=row["study_id"]
            studies.add(sid)
            if not sid: issues.append("missing_study_id")
            if sid!=study_id: issues.append("incorrect_study_id")
            if sid==original_study_id: issues.append("same_study_as_training")
            doi=row["source_doi"].replace("https://doi.org/","").replace("http://doi.org/","")
            if not doi.startswith("10.") or "/" not in doi: issues.append("missing_or_invalid_doi")
            if not row["source_locator"]: issues.append("missing_exact_source_locator")
            if row["record_type"] != "individual_measurement": issues.append("not_individual_measurement")
            if not row["fabric_id"]: issues.append("missing_fabric_id")
            if not row["wash_id"]: issues.append("missing_wash_id")
            key=(sid,row["fabric_id"],row["wash_id"],row["source_locator"])
            if key in seen: issues.append("duplicate_exact_record")
            seen.add(key)
            if row["release_unit"].lower().replace(" ","") not in ("mg/kg","mgkg-1","mgkg^-1","mg/kgtextile"):
                issues.append("release_unit_not_explicit_mg_per_kg")
            if row["measurement_basis"]!=CANONICAL_BASIS: issues.append("incompatible_measurement_basis")
            if not row["collection_method"]: issues.append("collection_method_missing")
            if not row["wash_protocol"]: issues.append("wash_protocol_missing")
            if not row["fabric_composition"]: issues.append("fabric_composition_missing")
            if not row["fabric_construction"]: issues.append("fabric_construction_missing")
            try:
                value=float(row["release_value"])
                if not math.isfinite(value) or value<0: issues.append("release_not_finite_nonnegative")
            except ValueError: issues.append("release_not_numeric")
            if row["gsm"]:
                try:
                    gsm=float(row["gsm"])
                    if not math.isfinite(gsm) or gsm<=0: issues.append("gsm_invalid")
                except ValueError: issues.append("gsm_invalid")
            if not issues:
                result["eligible_rows"] += 1
                eligible.add(row["fabric_id"])
                result["eligible_row_ids"].append(idx)
            else:
                reasons.update(issues)
                if len(result["errors"])<40:
                    result["errors"].append({"csv_line":idx,"fabric_id":row["fabric_id"],"reasons":sorted(set(issues))})
        result["reason_counts"]=dict(sorted(reasons.items()))
        result["unique_fabrics_eligible"]=len(eligible)
        result["study_ids_seen"]=sorted(studies)
        if result["rows_read"]==0: result["warnings"].append("No external observations supplied: discovery only")
        if result["eligible_rows"]>0:
            result["warnings"].append("Eligible means schema-compatible only. Manual protocol/source verification is still required before any external evaluation.")
            result["status"]="SCHEMA_COMPATIBLE_REQUIRES_MANUAL_REVIEW"
        if result["eligible_rows"]<result["rows_read"]:
            result["warnings"].append("Ineligible rows must not be silently used or zero-filled")
        return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv",required=True,help="Human-transcribed external-study CSV")
    ap.add_argument("--study-id",required=True,help="Must exactly match study_id in all records")
    ap.add_argument("--out",default="data/external_study_compatibility.json")
    args=ap.parse_args()
    path=Path(args.csv)
    if not path.is_file(): ap.error(f"Cannot find CSV: {path}")
    report=audit(path,args.study_id)
    destination=Path(args.out); destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"{report['status']} | rows={report['rows_read']} | compatible={report['eligible_rows']} | fabrics={report['unique_fabrics_eligible']}")
    print("Reasons:",report["reason_counts"])
    print("Saved:",destination)
    return 0 if report["status"]=="SCHEMA_COMPATIBLE_REQUIRES_MANUAL_REVIEW" else 2

if __name__=="__main__":
    raise SystemExit(main())
