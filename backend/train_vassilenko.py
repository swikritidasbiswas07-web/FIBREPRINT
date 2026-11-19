"""Run study-specific grouped validation on original experimental wash records.

NOT a deployment model. Does not assume unavailable wash temperature or water ratios.
Run from backend:
  .venv\\Scripts\\python.exe train_vassilenko.py --csv data/vassilenko_extracted_washes.csv
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

CATEGORICAL = ['fabric_type','yarn_type','construction','mechanical_finishing','mechanical_presence']
NUMERIC = ['density_gsm','wash_number','polyester_pct','cotton_pct','nylon_pct',
           'elastane_pct','polyurethane_pct','spandex_pct','polyamide_pct','wool_pct']
FEATURES = CATEGORICAL + NUMERIC
REQUIRED = ['fabric_id','study_id','source_doi','record_status','release_mg_per_kg'] + FEATURES


def train(csv_file:Path, report_file:Path):
    data=pd.read_csv(csv_file, keep_default_na=False)
    absent=[c for c in REQUIRED if c not in data.columns]
    if absent: raise ValueError(f'Missing columns: {absent}')
    if not data['record_status'].eq('EXTRACTED_UNVERIFIED').all():
        raise ValueError('Input must be the unmodified extracted research CSV; inspect record statuses.')
    if data['study_id'].nunique()!=1 or data['study_id'].iat[0]!='vassilenko_2021':
        raise ValueError('This trainer is for the 2021 Vassilenko workbook only.')
    if data['source_doi'].nunique()!=1 or data['source_doi'].iat[0]!='10.1371/journal.pone.0250346':
        raise ValueError('Source DOI mismatch.')
    if data['fabric_id'].nunique()<10: raise ValueError('Need at least 10 distinct fabrics.')
    y=pd.to_numeric(data['release_mg_per_kg'], errors='coerce')
    if y.isna().any() or (y<0).any(): raise ValueError('Invalid measured mg/kg target values.')
    X=data[FEATURES].copy()
    for c in CATEGORICAL: X[c]=X[c].astype(str).str.strip().replace({'':'unreported'})
    for c in NUMERIC: X[c]=pd.to_numeric(X[c],errors='coerce')
    if X['wash_number'].isna().any() or not X['wash_number'].between(1,5).all():
        raise ValueError('Wash numbers must be 1 through 5.')
    prep=ColumnTransformer([
        ('categorical',Pipeline([('imputer', SimpleImputer(strategy='most_frequent')),
                                 ('encoder', OneHotEncoder(handle_unknown='ignore'))]),CATEGORICAL),
        ('numeric',SimpleImputer(strategy='median'),NUMERIC)
    ])
    cv=GroupKFold(n_splits=5)
    rows=[]
    out_of_fold_pred=np.full(len(data),np.nan)
    out_of_fold_baseline=np.full(len(data),np.nan)
    groups=data['fabric_id'].astype(str).to_numpy()
    for fold, (train_idx,test_idx) in enumerate(cv.split(X,y,groups=groups),start=1):
        assert not set(groups[train_idx]) & set(groups[test_idx])
        reg=Pipeline([('preprocess',prep),('model',RandomForestRegressor(
            n_estimators=250,min_samples_leaf=2,random_state=42,n_jobs=-1))])
        reg.fit(X.iloc[train_idx],np.log1p(y.iloc[train_idx]))
        preds=np.maximum(0,np.expm1(reg.predict(X.iloc[test_idx])))
        base=DummyRegressor(strategy='median').fit(X.iloc[train_idx],y.iloc[train_idx])
        bp=base.predict(X.iloc[test_idx])
        out_of_fold_pred[test_idx]=preds
        out_of_fold_baseline[test_idx]=bp
        rows.append({'fold':fold,
                     'training_fabrics':int(len(set(groups[train_idx]))),
                     'held_out_fabrics':int(len(set(groups[test_idx]))),
                     'held_out_observations':int(len(test_idx)),
                     'model_mae_mg_per_kg':float(mean_absolute_error(y.iloc[test_idx],preds)),
                     'baseline_mae_mg_per_kg':float(mean_absolute_error(y.iloc[test_idx],bp))})
    assert np.isfinite(out_of_fold_pred).all()
    result={
        'study':'Vassilenko et al. (2021)',
        'doi':'10.1371/journal.pone.0250346',
        'data_status':'EXTRACTED_UNVERIFIED',
        'model_status':'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'target':'measured fibre release mass, mg/kg fabric per wash',
        'feature_columns':FEATURES,
        'excluded_unrecorded_parameters':['temperature_c','water_fabric_ratio'],
        'rows':int(len(data)), 'distinct_fabrics':int(data['fabric_id'].nunique()),
        'grouping':'5-fold GroupKFold by fabric_id — all wash cycles from one fabric stay together',
        'metrics':{'model_mae_mg_per_kg':float(mean_absolute_error(y,out_of_fold_pred)),
                   'baseline_mae_mg_per_kg':float(mean_absolute_error(y,out_of_fold_baseline)),
                   'model_rmse_mg_per_kg':float(np.sqrt(mean_squared_error(y,out_of_fold_pred))),
                   'model_r2':float(r2_score(y,out_of_fold_pred))},
        'folds':rows,
        'warning':'One-study, fabric-held-out exploration only; method and source records require manual review. Do not expose these estimates as product predictions.'
    }
    report_file.parent.mkdir(parents=True,exist_ok=True)
    report_file.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,required=True)
    p.add_argument('--report',type=Path,default=Path('data/vassilenko_research_metrics.json'))
    a=p.parse_args()
    report=train(a.csv,a.report)
    print(json.dumps({'status':report['model_status'],'data_status':report['data_status'],
                      'rows':report['rows'],'distinct_fabrics':report['distinct_fabrics'],
                      'metrics':report['metrics']},indent=2))
    print('Saved research-only report:',a.report)
