"""Extract observed wash-level release from the original Vassilenko et al. Figshare workbook.

Run from FIBREPRINT/backend:
  .venv\\Scripts\\python.exe prepare_vassilenko.py --xlsx data/source_figshare_14675760_v4/figshare_microfiber_data.xlsx

Reads the source workbook without modification. Never invents unreported conditions,
and NEVER merges mass [mg/kg] with count [fibres/kg].
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError as exc:
    raise SystemExit('Missing openpyxl: run .venv\\Scripts\\python.exe -m pip install openpyxl') from exc

SOURCE_DOI = '10.1371/journal.pone.0250346'
FIGSHARE_URL = 'https://doi.org/10.6084/m9.figshare.14675760.v4'
SHEET_NAME = 'Laundry data master'
# 1-based Excel column indices, verified against the uploaded workbook audit.
COL = {
    'description': 1, 'polyester_pct': 2, 'cotton_pct': 3,
    'nylon_pct': 4, 'elastane_pct': 5, 'polyurethane_pct': 6,
    'spandex_pct': 7, 'polyamide_pct': 8, 'wool_pct': 9,
    'recycled_pct': 10, 'composite': 11, 'fabric_type': 12,
    'yarn_type': 13, 'yarn_notes': 14, 'construction': 15,
    'construction_notes': 16, 'mechanical_finishing': 17,
    'mechanical_presence': 18, 'chemical_finishing': 19,
    'dye_approach': 20, 'dye_method': 21, 'colour': 22,
    'density_gsm': 23, 'load_weight_g': 24,
}
MASS_COLS = [25, 26, 27, 28, 29]
COUNT_COLS = [32, 33, 34, 35, 36]
FIELDS = [
    'study_id', 'source_doi', 'source_file_sha256', 'source_excel_row',
    'fabric_id', *COL.keys(), 'wash_number', 'release_mg_per_kg',
    'release_fibres_per_kg', 'measurement_method', 'temperature_c',
    'water_fabric_ratio', 'record_status'
]
MISSING = {'', 'na', 'n/a', 'none', 'null', '-', '—'}


def clean(v):
    return '' if v is None else str(v).strip()


def numeric(v):
    value = clean(v)
    if value.lower() in MISSING:
        return ''
    try:
        n = float(value.replace(',', ''))
    except (ValueError, TypeError):
        return ''
    return n if math.isfinite(n) else ''


def verify_headers(ws):
    expected = {1: 'Description', 2: 'Polyester_%', 23: 'Density_gsm', 24: 'Load_Weight',
                25: 'Wash1', 29: 'Wash5', 32: 'Wash1', 36: 'Wash5'}
    incorrect = [(c, name, ws.cell(1, c).value) for c, name in expected.items()
                 if clean(ws.cell(1, c).value).casefold() != name.casefold()]
    if incorrect:
        raise ValueError(f'Workbook columns do not match the audited source: {incorrect}')
    if '[mg/kg]' not in clean(ws.cell(2, 25).value).lower():
        raise ValueError('Mass-release units (column 25) are not mg/kg. Stop and inspect source.')
    if '[fiber/kg]' not in clean(ws.cell(2, 32).value).lower():
        raise ValueError('Count-release units (column 32) are not fiber/kg. Stop and inspect source.')


def prepare(workbook: Path, output: Path, report_path: Path):
    raw = workbook.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    wb = load_workbook(workbook, read_only=True, data_only=True)
    try:
        if SHEET_NAME not in wb.sheetnames:
            raise ValueError(f'Missing worksheet {SHEET_NAME!r}; available: {wb.sheetnames}')
        ws = wb[SHEET_NAME]
        verify_headers(ws)
        observations = []
        skips = Counter()
        fabric_rows = 0
        quality_flags = []
        for excel_row, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            if not row or len(row) < 36:
                continue
            def get(c):
                return row[c-1] if c <= len(row) else None
            desc = clean(get(1))
            if not desc:
                continue
            fabric_rows += 1
            fab_id = f'vassilenko_row_{excel_row}'
            base = {key: clean(get(c)) for key, c in COL.items()}
            base['density_gsm'] = numeric(get(23))
            base['load_weight_g'] = numeric(get(24))
            for name in ('polyester_pct','cotton_pct','nylon_pct','elastane_pct',
                         'polyurethane_pct','spandex_pct','polyamide_pct','wool_pct','recycled_pct'):
                base[name] = numeric(get(COL[name]))
            pct = [base[k] for k in ('polyester_pct','cotton_pct','nylon_pct','elastane_pct',
                                     'polyurethane_pct','spandex_pct','polyamide_pct','wool_pct')]
            if all(v != '' for v in pct) and abs(sum(pct)-100) > 1:
                quality_flags.append({'excel_row':excel_row,'flag':'fibre percentages do not sum to 100',
                                      'observed_sum':sum(pct)})
            for n, (mcol, ccol) in enumerate(zip(MASS_COLS, COUNT_COLS), start=1):
                mass, count = numeric(get(mcol)), numeric(get(ccol))
                if mass == '':
                    skips['missing_mass_measurement'] += 1
                    continue
                if mass < 0:
                    skips['negative_mass_measurement'] += 1
                    quality_flags.append({'excel_row':excel_row,'wash':n,'flag':'negative mg/kg'})
                    continue
                observations.append({
                    'study_id':'vassilenko_2021', 'source_doi':SOURCE_DOI,
                    'source_file_sha256':sha, 'source_excel_row':excel_row,
                    'fabric_id':fab_id, **base,
                    'wash_number':n, 'release_mg_per_kg':mass,
                    'release_fibres_per_kg':count,
                    # Source method must be verified from the paper; never guess it.
                    'measurement_method':'needs_protocol_review',
                    'temperature_c':'', 'water_fabric_ratio':'',
                    'record_status':'EXTRACTED_UNVERIFIED',
                })
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(observations)
        summary={
          'source_workbook':str(workbook),'source_file_sha256':sha,
          'source_doi':SOURCE_DOI,'figshare':FIGSHARE_URL,
          'sheet':SHEET_NAME,'fabric_rows_examined':fabric_rows,
          'fabric_ids_with_mass_observations':len({x['fabric_id'] for x in observations}),
          'mass_observation_rows_extracted':len(observations),
          'rows_by_wash_number':dict(sorted(Counter(str(x['wash_number']) for x in observations).items())),
          'skipped_cells':dict(skips),'quality_flags':quality_flags,
          'mass_source_excel_columns':'Y:AC (25–29), mg/kg',
          'count_source_excel_columns':'AF:AJ (32–36), fibres/kg',
          'unavailable_from_workbook_columns':['temperature_c','water_fabric_ratio'],
          'scientific_status':'UNVERIFIED_EXTRACTION; study-specific exploration only',
          'important':'This file is not curated_observations.csv; do not pass it to the existing v0.13 trainer.'
        }
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
        return summary
    finally:
        wb.close()

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--xlsx',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('data/vassilenko_extracted_washes.csv'))
    parser.add_argument('--report',type=Path,default=Path('data/vassilenko_extraction_report.json'))
    a=parser.parse_args()
    summary=prepare(a.xlsx,a.output,a.report)
    print(json.dumps({k:summary[k] for k in ('fabric_rows_examined','fabric_ids_with_mass_observations','mass_observation_rows_extracted','rows_by_wash_number','skipped_cells','scientific_status')},indent=2))
    print('Saved:',a.output,'and',a.report)
