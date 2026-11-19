"""FIBREPRINT v0.18 - repeated fabric-grouped holdout robustness checks.

Research-only, single-study EXTRACTED_UNVERIFIED data. No model deployment.
Usage (from backend):
 .venv\\Scripts\\python.exe check_model_robustness.py --csv data/vassilenko_extracted_washes.csv

Uses repeated GroupShuffleSplit with shared test groups for both models. A given
fabric can occur in multiple *different* repetitions; repetitions are correlated,
so the empirical split distribution is not a confidence interval.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

BASE_CAT = ['fabric_type','yarn_type','construction','mechanical_finishing','mechanical_presence']
BASE_NUM = ['density_gsm','wash_number','polyester_pct','cotton_pct','nylon_pct','elastane_pct','polyurethane_pct','spandex_pct','polyamide_pct','wool_pct']
RULES = {
    'explicit_raised_surface': r'\b(?:velour|pile|shaggy|brushed|fuzzy|napped|sanded|raised)\b',
    'fleece_term':r'\bfleece\b',
    'jersey_term':r'\bjersey\b',
    'woven_or_plaid_term':r'\b(?:woven|plaid|denim|twill)\b',
}

def build_data(data):
    needed = set(BASE_CAT+BASE_NUM+['fabric_id','description','release_mg_per_kg','study_id','source_doi','record_status'])
    missing = needed-set(data.columns)
    if missing: raise ValueError(f'Missing expected columns: {sorted(missing)}')
    if not data['study_id'].eq('vassilenko_2021').all(): raise ValueError('Unexpected study_id')
    if not data['source_doi'].eq('10.1371/journal.pone.0250346').all(): raise ValueError('Unexpected source DOI')
    if not data['record_status'].eq('EXTRACTED_UNVERIFIED').all(): raise ValueError('Expected EXTRACTED_UNVERIFIED records')
    if data.duplicated(['fabric_id','wash_number']).any(): raise ValueError('Duplicate fabric/wash rows')
    y = pd.to_numeric(data['release_mg_per_kg'],errors='raise').to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y < 0).any(): raise ValueError('Nonfinite or negative release target')
    if data['fabric_id'].nunique()<15: raise ValueError('Insufficient independent fabric groups')
    x=data[BASE_CAT+BASE_NUM].copy()
    for col in BASE_CAT: x[col]=x[col].fillna('').astype(str).str.strip().replace({'':'unreported'})
    for col in BASE_NUM: x[col]=pd.to_numeric(x[col],errors='coerce')
    if x['wash_number'].isna().any() or not x['wash_number'].between(1,5).all():raise ValueError('Invalid wash number')
    for name,pattern in RULES.items():
        x[name]=data['description'].fillna('').astype(str).str.contains(pattern,flags=re.IGNORECASE,regex=True).astype(int)
    return x,y,data['fabric_id'].astype(str).to_numpy()

def pipeline(kind,seed):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    cats=BASE_CAT
    if kind=='ridge_plus_keywords':
        nums=BASE_NUM+list(RULES)
        model=Ridge(alpha=10.0)
        transformer=Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())])
    else:
        nums=BASE_NUM
        model=RandomForestRegressor(n_estimators=250,min_samples_leaf=2,random_state=42,n_jobs=-1)
        transformer=SimpleImputer(strategy='median')
    pre=ColumnTransformer([
        ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('ohe',OneHotEncoder(handle_unknown='ignore'))]),cats),
        ('numeric',transformer,nums)
    ])
    return Pipeline([('preprocess',pre),('model',model)]),cats+nums

def run(data,repeats=20,test_fraction=.25,seed=2026):
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import mean_absolute_error
    x,y,groups=build_data(data)
    splits=GroupShuffleSplit(n_splits=repeats,test_size=test_fraction,random_state=seed)
    by_split=[]
    fold_errors=[]
    for index,(tr,te) in enumerate(splits.split(x,y,groups),start=1):
        if set(groups[tr]).intersection(groups[te]):raise AssertionError('Fabric-group leakage')
        results={}
        preds={}
        for kind in ('rf_original','ridge_plus_keywords'):
            model,columns=pipeline(kind,seed)
            model.fit(x.iloc[tr][columns],np.log1p(y[tr]))
            p=np.maximum(np.expm1(model.predict(x.iloc[te][columns])),0)
            preds[kind]=p
            results[kind+'_mae']=float(mean_absolute_error(y[te],p))
            results[kind+'_high_release_mae']=float(np.mean(np.abs(y[te][y[te]>=400]-p[y[te]>=400]))) if (y[te]>=400).any() else None
        results['split']=index
        results['n_test_fabrics']=int(len(set(groups[te])))
        results['n_test_rows']=int(len(te))
        results['n_high_release_rows']=int((y[te]>=400).sum())
        results['ridge_minus_rf_mae']=results['ridge_plus_keywords_mae']-results['rf_original_mae']
        results['ridge_better']=bool(results['ridge_minus_rf_mae']<0)
        by_split.append(results)
        for pos,row in enumerate(te):
            fold_errors.append({'split':index,'fabric_id':groups[row],'wash_number':int(x.iloc[row]['wash_number']),
                                'measured_mg_per_kg':float(y[row]),'rf_predicted':float(preds['rf_original'][pos]),
                                'ridge_predicted':float(preds['ridge_plus_keywords'][pos])})
    diffs=np.array([s['ridge_minus_rf_mae'] for s in by_split])
    rf=np.array([s['rf_original_mae'] for s in by_split])
    ridge=np.array([s['ridge_plus_keywords_mae'] for s in by_split])
    out={
      'status':'RESEARCH_ONLY_NOT_DEPLOYABLE','data_status':'EXTRACTED_UNVERIFIED',
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'n_independent_fabrics':int(len(set(groups))),'n_observation_rows':int(len(y)),
      'protocol':{'method':'GroupShuffleSplit','repetitions':repeats,'test_fraction_of_fabrics':test_fraction,'random_seed':seed,
        'same_test_groups_for_both_models':True,'target_transform':'log1p',
        'models':'Original RF vs Ridge + description keyword features; both fixed from v0.17',
        'no_hyperparameter_tuning':True},
      'summary':{
        'ridge_better_splits':int((diffs<0).sum()),'total_splits':repeats,
        'rf_mae_median':float(np.median(rf)),'ridge_plus_keywords_mae_median':float(np.median(ridge)),
        'paired_mae_difference_median_ridge_minus_rf':float(np.median(diffs)),
        'paired_mae_difference_10th_percentile':float(np.percentile(diffs,10)),
        'paired_mae_difference_90th_percentile':float(np.percentile(diffs,90)),
      },
      'splits':by_split,
      'limitations':[
        'One-study exploratory comparison. Source extraction has not been manually audited against original workbook.',
        'Repetitions share fabric groups across different splits; percentiles are descriptive, NOT confidence intervals or statistical significance tests.',
        'Keyword flags are labels parsed from free-text descriptions, not measured surface morphology.',
        'Model and feature choice followed inspection of earlier prediction errors; independent external validation is needed.',
        'High-release subset is defined using the observed target and must not be used as an inference-time filter.',
        'No model artifact is trained for serving and website prediction status stays NOT VALIDATED.'
      ]
    }
    return out,pd.DataFrame(fold_errors)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--csv',type=Path,default=Path('data/vassilenko_extracted_washes.csv'))
    ap.add_argument('--repeats',type=int,default=20)
    ap.add_argument('--test-fraction',type=float,default=.25)
    ap.add_argument('--seed',type=int,default=2026)
    ap.add_argument('--report',type=Path,default=Path('data/vassilenko_robustness.json'))
    ap.add_argument('--predictions',type=Path,default=Path('data/vassilenko_robustness_predictions.csv'))
    args=ap.parse_args()
    if not args.csv.is_file():raise SystemExit(f'Could not find {args.csv}. Run prepare_vassilenko.py first.')
    if not 2<=args.repeats<=100:raise SystemExit('Choose 2..100 repetitions')
    if not .1<=args.test_fraction<=.4:raise SystemExit('Choose test fraction 0.10..0.40')
    result,predictions=run(pd.read_csv(args.csv,keep_default_na=False),args.repeats,args.test_fraction,args.seed)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.predictions.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    predictions.to_csv(args.predictions,index=False)
    print(json.dumps({'status':result['status'],'summary':result['summary']},indent=2))
    print('Saved:',args.report,'and',args.predictions)

if __name__=='__main__': main()
