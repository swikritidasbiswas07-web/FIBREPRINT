"""Train FIBREPRINT on real, traceable, compatible experimental wash observations.

Usage: python train_model.py --csv data/curated_observations.csv
NO synthetic demo records are generated. Source documentation and method checks
are mandatory. A trained model does not automatically become deployable.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor

CATEGORICAL = ['fibre_type', 'construction']
NUMERIC = ['temperature_c', 'water_fabric_ratio', 'wash_number']
FEATURES = CATEGORICAL + NUMERIC
REQUIRED = ['study_id', 'fabric_id', 'measurement_method', 'source_doi',
            'release_mg_per_kg'] + FEATURES
ALLOWED_METHODS = {'gravimetric', 'particle_count_converted_with_verified_mass', 'other_documented_mass_method'}


def clean_dataset(filename: Path) -> pd.DataFrame:
    df = pd.read_csv(filename, dtype=str).fillna('')
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError('Missing columns: '+', '.join(missing))
    if len(df) < 30:
        raise ValueError('Need at least 30 real observations before attempting held-out evaluation.')
    df = df[REQUIRED].copy()
    for c in ('study_id', 'fabric_id', 'measurement_method', 'source_doi') + tuple(CATEGORICAL):
        df[c] = df[c].str.strip().str.lower()
        if df[c].eq('').any():
            raise ValueError(f'Empty values in {c}; do not fill scientific metadata by guesswork.')
    if df['measurement_method'].nunique() != 1:
        raise ValueError('Mixed measurement methods. Split observations into protocol-compatible subsets first.')
    method = df['measurement_method'].iat[0]
    if method not in ALLOWED_METHODS:
        raise ValueError(f'Unreviewed measurement method {method!r}. See DATA_PREPARATION.md.')
    for c in NUMERIC + ['release_mg_per_kg']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        if not np.isfinite(df[c]).all():
            raise ValueError(f'{c} contains missing or non-finite values; curate source observations first.')
    if (df['release_mg_per_kg'] < 0).any():
        raise ValueError('Release mass cannot be negative.')
    if (df['water_fabric_ratio'] <= 0).any():
        raise ValueError('Water/fabric ratio must be positive.')
    if ((df['temperature_c'] < 0) | (df['temperature_c'] > 95)).any():
        raise ValueError('Temperature outside 0–95 °C; check units.')
    if (df['wash_number'] < 0).any():
        raise ValueError('Wash number cannot be negative.')
    if df.duplicated(subset=['study_id', 'fabric_id'] + FEATURES).any():
        raise ValueError('Duplicate condition rows found; distinguish independent replicates before training.')
    if df['fabric_id'].nunique() < 5:
        raise ValueError('At least 5 independent fabric identifiers are needed for grouped evaluation.')
    if (df['source_doi'].str.contains('example|placeholder', case=False, regex=True)).any():
        raise ValueError('Replace placeholder DOIs with traceable source identifiers.')
    return df


def split_grouped(df):
    # For multiple studies, reserve entire studies to assess cross-study transfer.
    # A single study can establish only fabric-held-out, within-study performance.
    group_by = 'study_id' if df['study_id'].nunique() >= 5 else 'fabric_id'
    groups = df[group_by].astype(str).to_numpy()
    if pd.Series(groups).nunique() < 5:
        raise ValueError('Need at least 5 independent groups for train/calibration/test partition.')
    s1 = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=31)
    traincal_idx, test_idx = next(s1.split(df, groups=groups))
    s2 = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=79)
    sub_train, sub_cal = next(s2.split(df.iloc[traincal_idx], groups=groups[traincal_idx]))
    train_idx, cal_idx = traincal_idx[sub_train], traincal_idx[sub_cal]
    partitions = [train_idx, cal_idx, test_idx]
    if min(len(x) for x in partitions) < 3:
        raise ValueError('Not enough observations in one partition; obtain more independent samples.')
    assert all(not set(groups[a]).intersection(groups[b]) for i,a in enumerate(partitions) for b in partitions[i+1:])
    return group_by, partitions


def pipeline():
    prep = ColumnTransformer([
      ('categories', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL),
      ('numeric', 'passthrough', NUMERIC),
    ], remainder='drop')
    reg = RandomForestRegressor(n_estimators=250, min_samples_leaf=2,
                                 max_features=0.8, random_state=41, n_jobs=-1)
    return Pipeline([('preprocess', prep), ('regressor', reg)])


def train(csv_path: Path, output_path: Path, summary_path: Path) -> dict:
    df = clean_dataset(csv_path)
    group_by, (train_idx, cal_idx, test_idx) = split_grouped(df)
    x_train, x_cal, x_test = (df.iloc[idx][FEATURES] for idx in (train_idx, cal_idx, test_idx))
    y_train, y_cal, y_test = (df.iloc[idx]['release_mg_per_kg'].to_numpy() for idx in (train_idx, cal_idx, test_idx))
    model = pipeline()
    model.fit(x_train, np.log1p(y_train))
    cal_pred = np.maximum(0, np.expm1(model.predict(x_cal)))
    test_pred = np.maximum(0, np.expm1(model.predict(x_test)))
    baseline = DummyRegressor(strategy='median').fit(x_train, y_train)
    baseline_pred = baseline.predict(x_test)
    # The percentile is descriptive. Held-out test coverage checks its behaviour.
    calibration_error = float(np.quantile(np.abs(cal_pred - y_cal), 0.95))
    metrics = {
      'test_mae_mg_per_kg': float(mean_absolute_error(y_test, test_pred)),
      'test_rmse_mg_per_kg': float(np.sqrt(mean_squared_error(y_test, test_pred))),
      'test_r2': float(r2_score(y_test, test_pred)) if len(test_idx)>1 else None,
      'baseline_test_mae_mg_per_kg': float(mean_absolute_error(y_test, baseline_pred)),
      'test_error_band_coverage': float(np.mean(np.abs(y_test-test_pred) <= calibration_error)),
      'train_n':len(train_idx), 'calibration_n':len(cal_idx), 'test_n':len(test_idx),
      'split_by':group_by,
    }
    study_count = int(df['study_id'].nunique())
    # Review gate: fewer than 5 studies leaves cross-study transfer untested.
    # Even when metrics pass, author approval is required before deployment.
    eligible_for_review = (
      group_by == 'study_id' and study_count >= 5 and
      len(test_idx) >= 10 and len(cal_idx) >= 10 and
      metrics['test_mae_mg_per_kg'] < metrics['baseline_test_mae_mg_per_kg'] and
      metrics['test_error_band_coverage'] >= .80
    )
    scope = {'rows':int(len(df)), 'unique_studies':study_count,
             'unique_fabrics':int(df['fabric_id'].nunique()),
             'split_unit':group_by, 'source_dois':sorted(df['source_doi'].unique().tolist())}
    metadata = {
      'status':'REVIEW_REQUIRED' if eligible_for_review else 'RESEARCH_ONLY',
      'message': ('Held-out metrics meet initial review thresholds; manual scientific review is still required.'
                  if eligible_for_review else
                  'A real model was trained, but cross-study/generalisation or performance requirements are not met. Numerical predictions remain disabled.'),
      'trained_at_utc':datetime.now(timezone.utc).isoformat(),
      'target':'microfibre release mass (mg/kg fabric)',
      'model_name':'random forest log1p regression, grouped held-out evaluation',
      'measurement_method':df['measurement_method'].iat[0],
      'metrics':metrics, 'data_scope':scope,
      'categories':{c:sorted(df[c].unique().tolist()) for c in CATEGORICAL},
      'ranges':{c:[float(df[c].min()), float(df[c].max())] for c in NUMERIC},
      'calibration_abs_error_mg_per_kg':calibration_error,
      'approval_required':True,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'estimator':model, 'metadata':metadata}, output_path)
    summary_path.write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding='utf-8')
    return metadata


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Train and independently evaluate a FIBREPRINT research model')
    parser.add_argument('--csv',type=Path,required=True,help='Curated real observations CSV')
    parser.add_argument('--output',type=Path,default=Path('data/fibreprint_model.joblib'))
    parser.add_argument('--report',type=Path,default=Path('data/model_report.json'))
    args=parser.parse_args()
    result=train(args.csv,args.output,args.report)
    print(json.dumps({'status':result['status'], 'metrics':result['metrics'],
                      'data_scope':result['data_scope']},indent=2))
