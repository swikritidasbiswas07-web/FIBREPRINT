"""FIBREPRINT: reproducible diagnostics of one-study held-out fabric predictions.

Run from FIBREPRINT/backend after prepare_vassilenko.py:
 .venv\\Scripts\\python.exe diagnose_vassilenko.py --csv data/vassilenko_extracted_washes.csv

Research-only: never deploy predictions to end users from this analysis.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Mirror the v0.15 study-specific trainer's features and parameters exactly.
CATEGORICAL = ['fabric_type', 'yarn_type', 'construction',
               'mechanical_finishing', 'mechanical_presence']
NUMERIC = ['density_gsm', 'wash_number', 'polyester_pct', 'cotton_pct',
           'nylon_pct', 'elastane_pct', 'polyurethane_pct', 'spandex_pct',
           'polyamide_pct', 'wool_pct']
FEATURES = CATEGORICAL + NUMERIC
REQUIRED = ['fabric_id', 'study_id', 'source_doi', 'record_status',
            'release_mg_per_kg', 'wash_number', *FEATURES]


def metric_block(observed, predicted, baseline):
    truth = np.asarray(observed, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    base = np.asarray(baseline, dtype=float)
    mae = float(mean_absolute_error(truth, pred))
    bmae = float(mean_absolute_error(truth, base))
    block = {
        'n': int(len(truth)),
        'model_mae_mg_per_kg': mae,
        'baseline_mae_mg_per_kg': bmae,
        'model_rmse_mg_per_kg': float(np.sqrt(mean_squared_error(truth, pred))),
        'baseline_rmse_mg_per_kg': float(np.sqrt(mean_squared_error(truth, base))),
        'mae_improvement_pct': float(100 * (bmae - mae) / bmae) if bmae > 0 else None,
        'model_better_than_baseline': bool(mae < bmae),
    }
    if len(truth) > 1 and np.var(truth) > 0:
        block['model_r2'] = float(r2_score(truth, pred))
    else:
        block['model_r2'] = None
    return block


def diagnose(csv_file: Path, json_file: Path, predictions_file: Path):
    data = pd.read_csv(csv_file, keep_default_na=False)
    missing = sorted(set(REQUIRED) - set(data.columns))
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    if len(data) == 0:
        raise ValueError('No observations in CSV.')
    if not data['record_status'].eq('EXTRACTED_UNVERIFIED').all():
        raise ValueError('This diagnostic accepts only v0.15 EXTRACTED_UNVERIFIED observations.')
    if data['study_id'].nunique() != 1 or data['study_id'].iat[0] != 'vassilenko_2021':
        raise ValueError('This is only for the Vassilenko 2021 source workbook.')
    if data['source_doi'].nunique() != 1 or data['source_doi'].iat[0] != '10.1371/journal.pone.0250346':
        raise ValueError('Source DOI does not match Vassilenko 2021.')
    if data['fabric_id'].nunique() < 10:
        raise ValueError('Need at least 10 distinct fabrics for the 5-fold grouped evaluation.')
    if data['fabric_id'].astype(str).str.strip().eq('').any():
        raise ValueError('Empty fabric IDs must be resolved before grouped evaluation.')

    y = pd.to_numeric(data['release_mg_per_kg'], errors='coerce')
    if y.isna().any() or (y < 0).any() or not np.isfinite(y).all():
        raise ValueError('Targets must be finite nonnegative measured release mass (mg/kg).')
    X = data[FEATURES].copy()
    for col in CATEGORICAL:
        X[col] = X[col].astype(str).str.strip().replace({'': 'unreported'})
    for col in NUMERIC:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    if X['wash_number'].isna().any() or not X['wash_number'].between(1, 5).all():
        raise ValueError('Wash numbers must be 1–5.')
    if not np.isfinite(X['wash_number']).all():
        raise ValueError('Invalid wash number.')

    groups = data['fabric_id'].astype(str).to_numpy()
    predictions = np.full(len(data), np.nan)
    baselines = np.full(len(data), np.nan)
    fold_ids = np.zeros(len(data), dtype=int)
    folds = []
    for k, (train_idx, test_idx) in enumerate(GroupKFold(n_splits=5).split(X, y, groups), start=1):
        if set(groups[train_idx]) & set(groups[test_idx]):
            raise AssertionError('Fabric ID leaked between training and holdout groups!')
        pre = ColumnTransformer([
            ('categorical', Pipeline([
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('encoder', OneHotEncoder(handle_unknown='ignore'))
            ]), CATEGORICAL),
            ('numeric', SimpleImputer(strategy='median'), NUMERIC)
        ])
        model = Pipeline([
            ('preprocess', pre),
            ('model', RandomForestRegressor(
                n_estimators=250, min_samples_leaf=2, random_state=42, n_jobs=-1))
        ])
        model.fit(X.iloc[train_idx], np.log1p(y.iloc[train_idx]))
        pred = np.maximum(0, np.expm1(model.predict(X.iloc[test_idx])))
        baseline = DummyRegressor(strategy='median').fit(X.iloc[train_idx], y.iloc[train_idx])
        base_pred = baseline.predict(X.iloc[test_idx])
        predictions[test_idx] = pred
        baselines[test_idx] = base_pred
        fold_ids[test_idx] = k
        folds.append({
            'fold': k,
            'training_fabrics': int(len(set(groups[train_idx]))),
            'held_out_fabrics': int(len(set(groups[test_idx]))),
            **metric_block(y.iloc[test_idx], pred, base_pred),
        })
    if not np.isfinite(predictions).all() or not np.isfinite(baselines).all():
        raise AssertionError('Unfilled/invalid out-of-fold predictions.')

    detail = pd.DataFrame({
        'fabric_id': data['fabric_id'].astype(str),
        'source_excel_row': data['source_excel_row'] if 'source_excel_row' in data else '',
        'description': data['description'] if 'description' in data else '',
        'wash_number': X['wash_number'].astype(int),
        'fold': fold_ids,
        'measured_mg_per_kg': y,
        'predicted_mg_per_kg': predictions,
        'median_baseline_mg_per_kg': baselines,
        'absolute_error_mg_per_kg': np.abs(y.to_numpy() - predictions),
        'baseline_absolute_error_mg_per_kg': np.abs(y.to_numpy() - baselines),
        'residual_mg_per_kg': y.to_numpy() - predictions,
    })
    per_wash = {}
    for wash, part in detail.groupby('wash_number', sort=True):
        per_wash[str(int(wash))] = {
            'distinct_fabrics': int(part['fabric_id'].nunique()),
            **metric_block(part['measured_mg_per_kg'], part['predicted_mg_per_kg'],
                           part['median_baseline_mg_per_kg']),
        }
    per_fabric = []
    for fabric, part in detail.groupby('fabric_id', sort=True):
        per_fabric.append({
            'fabric_id': fabric,
            'description': str(part['description'].iloc[0]),
            'wash_numbers': [int(v) for v in sorted(part['wash_number'].unique())],
            'n': int(len(part)),
            'observed_mean_mg_per_kg': float(part['measured_mg_per_kg'].mean()),
            'model_mae_mg_per_kg': float(part['absolute_error_mg_per_kg'].mean()),
            'baseline_mae_mg_per_kg': float(part['baseline_absolute_error_mg_per_kg'].mean()),
        })
    worst_fabrics = sorted(per_fabric, key=lambda f: f['model_mae_mg_per_kg'], reverse=True)[:10]
    worst_records = detail.sort_values('absolute_error_mg_per_kg', ascending=False).head(12).to_dict('records')
    overall = metric_block(y, predictions, baselines)
    obs_by_wash = {str(int(k)): int(v) for k, v in detail['wash_number'].value_counts().sort_index().items()}
    total_possible = int(data['fabric_id'].nunique()) * 5

    report = {
        'study': 'Vassilenko et al. (2021)',
        'doi': '10.1371/journal.pone.0250346',
        'status': 'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'data_status': 'EXTRACTED_UNVERIFIED',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'input_csv': str(csv_file),
        'rows': int(len(data)),
        'distinct_fabrics': int(data['fabric_id'].nunique()),
        'input_features': FEATURES,
        'grouping': 'GroupKFold(5) by fabric_id; repeated washes stay in one fold',
        'model': 'RandomForestRegressor(250 trees, min_samples_leaf=2, random_state=42) on log1p target',
        'baseline': 'Median calculated exclusively from the training folds',
        'overall': overall,
        'by_fold': folds,
        'by_wash': per_wash,
        'wash_coverage': {
            'possible_if_all_fabrics_have_all_5_washes': total_possible,
            'observed': int(len(detail)),
            'unobserved': total_possible - int(len(detail)),
            'observations_by_wash': obs_by_wash,
            'note': 'Unobserved means absent from the extracted MASS columns; cause must be checked against source.'
        },
        'target_distribution_mg_per_kg': {
            'min': float(y.min()), 'median': float(y.median()),
            'p90': float(y.quantile(.90)), 'p95': float(y.quantile(.95)),
            'max': float(y.max())
        },
        'worst_10_fabrics': worst_fabrics,
        'worst_12_observations': worst_records,
        'warnings': [
            'Exploratory within-one-study validation only; not calibrated for general laundry.',
            'Extraction and missingness have not been manually source-verified.',
            'Per-wash subsets and worst-fabric rankings are descriptive; small subsets are unstable.',
            'No invented temperature or water-to-fabric ratio inputs are used.',
            'No uncertainty intervals or deployment calibration are established.',
        ],
    }
    json_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    detail.to_csv(predictions_file, index=False)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Research-only fabric-held-out model diagnostics')
    p.add_argument('--csv', type=Path, default=Path('data/vassilenko_extracted_washes.csv'))
    p.add_argument('--report', type=Path, default=Path('data/vassilenko_diagnostics.json'))
    p.add_argument('--predictions', type=Path, default=Path('data/vassilenko_oof_predictions.csv'))
    args = p.parse_args()
    info = diagnose(args.csv, args.report, args.predictions)
    print(json.dumps({
        'status': info['status'],
        'rows': info['rows'],
        'distinct_fabrics': info['distinct_fabrics'],
        'overall': info['overall'],
        'by_wash': {k: {'n': v['n'], 'model_mae_mg_per_kg': v['model_mae_mg_per_kg']}
                    for k, v in info['by_wash'].items()},
    }, indent=2))
    print('Saved:', args.report, 'and', args.predictions)
