"""FIBREPRINT v0.19 — compare extracted study observations against source Excel cells.

Runs without modifying the source workbook or extracted CSV. Checks column mapping,
row identity, release mass/count, source hash and missing values.
This is a structural/data-integrity audit, NOT a manual scientific protocol review.

Run inside backend/:
.venv\\Scripts\\python.exe audit_source_alignment.py --xlsx data/source_figshare_14675760_v4/figshare_microfiber_data.xlsx --csv data/vassilenko_extracted_washes.csv
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError as exc:
    raise SystemExit('Missing openpyxl. Install: .venv\\Scripts\\python.exe -m pip install openpyxl') from exc

SHEET = 'Laundry data master'
MASS_COLS = {wash:24 + wash for wash in range(1, 6)}
COUNT_COLS = {wash:31 + wash for wash in range(1, 6)}
MISSING = {'', 'na', 'n/a', 'none', 'null', '-', '—'}


def number(value):
    if value is None or str(value).strip().lower() in MISSING:
        return None
    try:
        num = float(str(value).strip().replace(',', ''))
        return num if math.isfinite(num) else None
    except (TypeError, ValueError):
        return None


def audit(xlsx: Path, extracted_csv: Path):
    checksum = hashlib.sha256(xlsx.read_bytes()).hexdigest()
    wb = load_workbook(xlsx, data_only=True, read_only=True)
    try:
        if SHEET not in wb:
            raise ValueError(f'Source worksheet missing: {SHEET}')
        ws = wb[SHEET]
        headers = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
        units = list(next(ws.iter_rows(min_row=2, max_row=2, values_only=True)))
        for n, column in MASS_COLS.items():
            if str(headers[column-1]).strip() != f'Wash{n}' or 'mg/kg' not in str(units[column-1]).lower():
                raise ValueError(f'Mass header or unit mismatch in source column {column}')
        for n, column in COUNT_COLS.items():
            if str(headers[column-1]).strip() != f'Wash{n}' or 'fiber/kg' not in str(units[column-1]).lower():
                raise ValueError(f'Count header or unit mismatch in source column {column}')
        source = {}
        skipped_by_wash = Counter()
        count_with_mass_missing = []
        negative_source_mass = []
        for excel_row, row in enumerate(ws.iter_rows(min_row=3, values_only=True), 3):
            if not row or not str(row[0] or '').strip():
                continue
            for wash, mass_col in MASS_COLS.items():
                mass = number(row[mass_col - 1] if len(row) >= mass_col else None)
                count_col = COUNT_COLS[wash]
                count = number(row[count_col - 1] if len(row) >= count_col else None)
                key = (excel_row, wash)
                if mass is None:
                    skipped_by_wash[str(wash)] += 1
                    if count is not None:
                        count_with_mass_missing.append({'excel_row':excel_row,'wash':wash,'fibre_count_per_kg':count})
                elif mass < 0:
                    negative_source_mass.append({'excel_row':excel_row,'wash':wash,'mass':mass})
                else:
                    source[key] = {'mass':mass,'count':count,'description':str(row[0]).strip()}
    finally:
        wb.close()
    mismatches = []
    seen = set()
    observed_wash = Counter()
    csv_rows = 0
    missing_count_in_csv = 0
    with extracted_csv.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'source_excel_row','wash_number','fabric_id','source_file_sha256','release_mg_per_kg','release_fibres_per_kg'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f'CSV missing required columns: {sorted(required - set(reader.fieldnames or []))}')
        for r in reader:
            csv_rows += 1
            try:
                rownum, wash = int(r['source_excel_row']), int(r['wash_number'])
            except (TypeError, ValueError):
                mismatches.append({'csv_row':csv_rows+1,'error':'invalid source row or wash number'})
                continue
            key = (rownum,wash)
            observed_wash[str(wash)] += 1
            if key in seen:
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'duplicate extracted record'})
            seen.add(key)
            if r['fabric_id'] != f'vassilenko_row_{rownum}':
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'fabric_id does not match Excel row'})
            if r['source_file_sha256'].strip().lower() != checksum:
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'source SHA-256 mismatch'})
            actual = source.get(key)
            if actual is None:
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'no corresponding valid source mass cell'})
                continue
            val = number(r['release_mg_per_kg'])
            if val is None or not math.isclose(val,actual['mass'],rel_tol=1e-10,abs_tol=1e-7):
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'mass mismatch','source_mass':actual['mass'],'csv_mass':r['release_mg_per_kg']})
            csv_count = number(r['release_fibres_per_kg'])
            if (csv_count is None) != (actual['count'] is None) or (csv_count is not None and not math.isclose(csv_count,actual['count'],rel_tol=1e-10,abs_tol=1e-7)):
                mismatches.append({'excel_row':rownum,'wash':wash,'error':'fibre count mismatch','source_count':actual['count'],'csv_count':r['release_fibres_per_kg']})
            if csv_count is None: missing_count_in_csv += 1
    unextracted = sorted(source.keys() - seen)
    for rownum,wash in unextracted:
        mismatches.append({'excel_row':rownum,'wash':wash,'error':'valid source mass cell missing from extracted CSV'})
    status = 'STRUCTURAL_AUDIT_PASS' if not mismatches and not negative_source_mass else 'STRUCTURAL_AUDIT_FAIL'
    report = {
        'status':status,
        'scientific_status':'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'source_file_sha256':checksum,
        'source_workbook':str(xlsx),
        'csv_path':str(extracted_csv),
        'csv_rows':csv_rows,
        'valid_source_mass_cells':len(source),
        'matched_source_cells':len(seen & source.keys()),
        'csv_fabric_count':len({row for row,_ in seen}),
        'csv_rows_by_wash':dict(sorted(observed_wash.items())),
        'missing_source_mass_cells_by_wash':dict(sorted(skipped_by_wash.items())),
        'count_present_but_mass_missing':count_with_mass_missing,
        'missing_fibre_count_values_among_extracted_rows':missing_count_in_csv,
        'negative_mass_cells':negative_source_mass,
        'mismatches':mismatches,
        'limitations':[
            'Passing checks proves structural agreement between workbook cells and extracted CSV, not correctness of the source study.',
            'The original paper and experimental protocol must be manually reviewed for sample definitions, conditions and missingness.',
            'No temperature or water-to-fabric ratio values are inferred.',
            'Missing source mass cells must never be zero-filled.',
            'All predictions remain research-only; structural validation is not external predictive validation.'
        ]
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--xlsx',type=Path,required=True)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--report',type=Path,default=Path('data/vassilenko_source_alignment.json'))
    a=parser.parse_args()
    result=audit(a.xlsx,a.csv)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    summary={k:result[k] for k in ['status','csv_rows','valid_source_mass_cells','matched_source_cells','csv_fabric_count','csv_rows_by_wash','missing_source_mass_cells_by_wash']}
    print(json.dumps(summary,indent=2))
    print('Saved:',a.report)
    if result['status'] != 'STRUCTURAL_AUDIT_PASS':
        raise SystemExit('AUDIT FAILED — inspect mismatches in the JSON report')

if __name__=='__main__':
    main()
