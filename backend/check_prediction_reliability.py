"""FIBREPRINT v0.20: research-only diagnostics on *existing* held-out predictions.

This script DOES NOT train or serve a model and DOES NOT generate formal
conformal prediction intervals. Calibration residuals belong to overlapping
training procedures; exchangeability/independence is not established.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RIDGE_COL = 'ridge_plus_description_keywords_prediction'
RF_COL = 'rf_original_features_prediction'
TARGET_COL = 'measured_mg_per_kg'
REQUIRED = ('fabric_id', 'wash_number', TARGET_COL, RF_COL, RIDGE_COL)


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError('Cannot calculate quantile of an empty list')
    xs = sorted(values)
    p = (len(xs) - 1) * q
    a = math.floor(p)
    b = math.ceil(p)
    return float(xs[a] * (b - p) + xs[b] * (p - a)) if a != b else float(xs[a])


def read_predictions(path: Path) -> list[dict]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = set(REQUIRED) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing prediction CSV columns: {sorted(missing)}')
        rows = []
        seen = set()
        for line, raw in enumerate(reader, 2):
            try:
                name = raw['fabric_id'].strip()
                wash = int(raw['wash_number'])
                observed = float(raw[TARGET_COL])
                ridge = float(raw[RIDGE_COL])
                rf = float(raw[RF_COL])
            except (TypeError, ValueError, KeyError) as ex:
                raise ValueError(f'Bad prediction at CSV line {line}: {ex}') from ex
            key = (name, wash)
            if key in seen:
                raise ValueError(f'Duplicate fabric/wash observation: {key}')
            seen.add(key)
            if not name or wash not in range(1, 6):
                raise ValueError(f'Unexpected fabric ID/wash at CSV line {line}')
            if not all(map(math.isfinite, (observed, ridge, rf))) or observed < 0:
                raise ValueError(f'Invalid numeric value at CSV line {line}')
            rows.append({'fabric_id': name, 'wash': wash, 'observed': observed,
                         'ridge': ridge, 'rf': rf,
                         'ridge_abs_error': abs(observed - ridge),
                         'rf_abs_error': abs(observed - rf)})
    if not rows:
        raise ValueError('Prediction CSV has no records')
    return rows


def summarize(rows: list[dict]) -> dict:
    signed = [r['observed'] - r['ridge'] for r in rows]
    return {'n_observations': len(rows),
            'n_fabrics': len({r['fabric_id'] for r in rows}),
            'ridge_mae_mg_per_kg': sum(r['ridge_abs_error'] for r in rows) / len(rows),
            'rf_mae_mg_per_kg': sum(r['rf_abs_error'] for r in rows) / len(rows),
            'ridge_mean_signed_error_observed_minus_predicted': sum(signed) / len(rows),
            'ridge_underpredicted_fraction': sum(x > 0 for x in signed) / len(rows)}


def assess(data: list[dict], coverage: float, min_calibration_fabrics: int, min_wash_fabrics: int) -> tuple[dict, list[dict]]:
    all_ids = {r['fabric_id'] for r in data}
    if len(all_ids) < min_calibration_fabrics + 1:
        raise ValueError('Too few distinct fabrics for leave-one-fabric-out diagnostic')
    # Leave one fabric out of the *residual cutoff* calculation. The predictions
    # themselves are upstream OOF values and are NOT retrained here.
    records = []
    for r in data:
        cal = [a for a in data if a['fabric_id'] != r['fabric_id']]
        cal_groups = len({a['fabric_id'] for a in cal})
        if cal_groups < min_calibration_fabrics:
            raise ValueError('Insufficient calibration fabrics')
        global_cutoff = quantile([a['ridge_abs_error'] for a in cal], coverage)
        wash_cal = [a for a in cal if a['wash'] == r['wash']]
        wash_groups = len({a['fabric_id'] for a in wash_cal})
        # Report wash-specific estimates separately, never substitute silently.
        wash_cutoff = quantile([a['ridge_abs_error'] for a in wash_cal], coverage) if wash_groups >= min_wash_fabrics else None
        lower = max(0.0, r['ridge'] - global_cutoff)
        upper = max(lower, r['ridge'] + global_cutoff)
        records.append({**r, 'global_band_half_width': global_cutoff,
                        'global_band_lower': lower, 'global_band_upper': upper,
                        'global_band_contains_observed': lower <= r['observed'] <= upper,
                        'wash_band_half_width_exploratory': wash_cutoff,
                        'wash_calibration_fabrics': wash_groups})

    def band_info(sub: list[dict]) -> dict:
        return {'n': len(sub), 'distinct_fabrics': len({r['fabric_id'] for r in sub}),
                'empirical_global_band_coverage_fraction': sum(x['global_band_contains_observed'] for x in sub) / len(sub),
                'median_global_band_half_width_mg_per_kg': quantile([x['global_band_half_width'] for x in sub], .5),
                'ridge_mae_mg_per_kg': sum(x['ridge_abs_error'] for x in sub) / len(sub),
                'underpredicted_fraction': sum(x['observed'] > x['ridge'] for x in sub) / len(sub)}

    categories = {
        'below_100': [x for x in records if x['observed'] < 100],
        '100_to_below_400': [x for x in records if 100 <= x['observed'] < 400],
        'at_least_400': [x for x in records if x['observed'] >= 400],
    }
    group_report = {k: band_info(v) if v else {'n': 0} for k, v in categories.items()}
    wash_report = {str(w): band_info([x for x in records if x['wash'] == w]) for w in range(1, 6)}

    by_fabric = defaultdict(list)
    for x in records:
        by_fabric[x['fabric_id']].append(x)
    fabric_coverage = [dict(fabric_id=k, **band_info(v)) for k, v in by_fabric.items()]
    failures = sorted(fabric_coverage, key=lambda x: (x['empirical_global_band_coverage_fraction'], -x['ridge_mae_mg_per_kg']))[:10]
    high = categories['at_least_400']
    report = {
        'status': 'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'check': 'EXPLORATORY_RESIDUAL_BAND_DIAGNOSTIC_NOT_CONFORMAL',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'input_rows': len(data), 'distinct_fabrics': len(all_ids),
        'model': 'v0.17 Ridge + description keywords; existing fabric-grouped OOF predictions',
        'nominal_residual_quantile': coverage,
        'method': 'For each fabric, take residual quantile from other fabrics; evaluate on existing OOF predictions. No refitting.',
        'overall': dict(**summarize(data), **{'global_band': band_info(records)}),
        'by_wash': wash_report,
        'by_observed_release_level_posthoc_only': group_report,
        'high_release_failure': {
            'threshold_mg_per_kg': 400, 'observations': len(high),
            'underpredicted_count': sum(x['observed'] > x['ridge'] for x in high),
            'out_of_band_count': sum(not x['global_band_contains_observed'] for x in high),
            'critical_note': 'Threshold uses observed target; cannot be used at inference time.'
        },
        'worst_fabrics_by_empirical_band_coverage': failures,
        'warnings': [
            'These bands are DESCRIPTIVE diagnostics, NOT validated 90% prediction intervals.',
            'Upstream OOF predictions were produced from overlapping fitted folds; residual cutoffs are not an independent calibration set.',
            'Multiple washes per fabric are correlated and do not count as independent calibration specimens.',
            'Coverage measured on observed-target subgroups is a diagnostic, not an inference-time applicability test.',
            'A 90% residual quantile does not imply guaranteed 90% future coverage.',
            'No external study, deployment artifact, calibration guarantee, or new-fabric reliability score is produced.',
            'Review experimental protocols and missing early washes before extending beyond the source study.'
        ],
    }
    return report, records


def run(csv_path: Path, audit_path: Path, output_json: Path, output_csv: Path, q: float) -> dict:
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status') != 'STRUCTURAL_AUDIT_PASS':
        raise ValueError('Source alignment audit has not passed; refusing diagnostics')
    rows = read_predictions(csv_path)
    if len(rows) != audit.get('matched_source_cells') or len({r['fabric_id'] for r in rows}) != audit.get('csv_fabric_count'):
        raise ValueError('OOF rows or fabric counts do not match structural audit')
    report, detail = assess(rows, q, min_calibration_fabrics=20, min_wash_fabrics=15)
    report['source_alignment_status'] = audit['status']
    report['source_workbook_sha256'] = audit.get('source_file_sha256')
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    fields = ['fabric_id', 'wash', 'observed', 'ridge', 'rf', 'ridge_abs_error', 'rf_abs_error',
              'global_band_half_width', 'global_band_lower', 'global_band_upper',
              'global_band_contains_observed', 'wash_band_half_width_exploratory', 'wash_calibration_fabrics']
    with output_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: r.get(key) for key in fields} for r in detail)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--oof', type=Path, default=Path('data/vassilenko_surface_comparison_oof.csv'))
    p.add_argument('--audit', type=Path, default=Path('data/vassilenko_source_alignment.json'))
    p.add_argument('--report', type=Path, default=Path('data/vassilenko_reliability.json'))
    p.add_argument('--details', type=Path, default=Path('data/vassilenko_reliability_by_observation.csv'))
    p.add_argument('--quantile', type=float, default=.90)
    a = p.parse_args()
    if not 0.5 <= a.quantile < 1:
        p.error('--quantile must be between 0.5 and 1 (exclusive)')
    result = run(a.oof, a.audit, a.report, a.details, a.quantile)
    display = {'status': result['status'], 'source_alignment_status': result['source_alignment_status'],
               'rows': result['input_rows'], 'distinct_fabrics': result['distinct_fabrics'],
               'global_band': result['overall']['global_band'],
               'high_release_failure': result['high_release_failure']}
    print(json.dumps(display, indent=2))
    print(f'Saved: {a.report} and {a.details}')


if __name__ == '__main__':
    main()
