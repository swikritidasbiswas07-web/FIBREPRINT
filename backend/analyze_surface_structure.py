"""FIBREPRINT v0.17: post-hoc diagnostics and exploratory surface-text feature ablation.

Scientific status: RESEARCH_ONLY_NOT_DEPLOYABLE. This analysis does NOT turn
free-text descriptions into microscope-verified morphology measurements.

Run from backend:
 .venv\\Scripts\\python.exe analyze_surface_structure.py --csv data/vassilenko_extracted_washes.csv --oof data/vassilenko_oof_predictions.csv

An --oof-only run computes honest existing-prediction diagnostics but DOES NOT
train any new models or test whether morphology improves prediction.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

STUDY = 'vassilenko_2021'
DOI = '10.1371/journal.pone.0250346'
BASE_CAT = ['fabric_type','yarn_type','construction','mechanical_finishing','mechanical_presence']
BASE_NUM = ['density_gsm','wash_number','polyester_pct','cotton_pct','nylon_pct','elastane_pct','polyurethane_pct','spandex_pct','polyamide_pct','wool_pct']

# These tags are unvalidated TEXT-ONLY indicators, not a material assay.
# Explicit precedence avoids assigning all fleece to 'raised_pile' automatically.
RULES = [
    ('explicit_raised_surface', r'\b(velour|pile|shaggy|brushed|fuzzy|napped|sanded|raised)\b'),
    ('fleece_term', r'\bfleece\b'),
    ('jersey_term', r'\bjersey\b'),
    ('woven_or_plaid_term', r'\b(woven|plaid|denim|twill)\b'),
]

def text_tags(text):
    s = str(text).casefold()
    return {name:int(bool(re.search(pattern,s))) for name,pattern in RULES}

def json_num(x):
    x=float(x)
    return x if np.isfinite(x) else None

def diagnostics(oof: pd.DataFrame):
    required={'fabric_id','description','wash_number','fold','measured_mg_per_kg','predicted_mg_per_kg','median_baseline_mg_per_kg'}
    missing=sorted(required-set(oof.columns))
    if missing: raise ValueError(f'Missing held-out prediction fields: {missing}')
    if not oof['fabric_id'].is_unique:
        # fabric_id must repeat across washes, so check pairs instead.
        if oof.duplicated(['fabric_id','wash_number']).any():
            raise ValueError('Duplicate fabric/wash in OOF predictions.')
    z=oof.copy()
    for c in ['measured_mg_per_kg','predicted_mg_per_kg','median_baseline_mg_per_kg']:
        z[c]=pd.to_numeric(z[c],errors='raise')
        if not np.isfinite(z[c]).all() or (z[c]<0).any(): raise ValueError(f'Invalid values in {c}')
    z['absolute_error_mg_per_kg']=(z['measured_mg_per_kg']-z['predicted_mg_per_kg']).abs()
    z['baseline_absolute_error_mg_per_kg']=(z['measured_mg_per_kg']-z['median_baseline_mg_per_kg']).abs()
    z['squared_error']=(z['measured_mg_per_kg']-z['predicted_mg_per_kg'])**2
    z['signed_error']=z['measured_mg_per_kg']-z['predicted_mg_per_kg']
    for key in ['explicit_raised_surface','fleece_term','jersey_term','woven_or_plaid_term']:
        z[key]=z['description'].map(lambda text:text_tags(text)[key])
    def summarize(g):
        return {'observations':int(len(g)), 'fabrics':int(g['fabric_id'].nunique()),
                'model_mae_mg_per_kg':json_num(g['absolute_error_mg_per_kg'].mean()),
                'baseline_mae_mg_per_kg':json_num(g['baseline_absolute_error_mg_per_kg'].mean()),
                'mean_signed_error_mg_per_kg':json_num(g['signed_error'].mean()),
                'underprediction_fraction':json_num((g['signed_error']>0).mean())}
    high=z['measured_mg_per_kg']>=400
    total_sq=z['squared_error'].sum()
    fabric_error=z.groupby('fabric_id',sort=False)['squared_error'].sum().sort_values(ascending=False)
    top2=fabric_error.head(2)
    by_text={}
    for tag,_ in RULES:
        by_text[tag]={
            'tagged':summarize(z.loc[z[tag]==1]),
            'untagged':summarize(z.loc[z[tag]==0]),
            'note':'Rule-based label extracted from free text; not scientifically verified morphology.'
        }
    by_wash={str(int(k)):summarize(g) for k,g in z.groupby('wash_number')}
    by_level={
        'below_100_mg_per_kg':summarize(z.loc[z['measured_mg_per_kg']<100]),
        '100_to_below_400_mg_per_kg':summarize(z.loc[(z['measured_mg_per_kg']>=100)&(~high)]),
        '400_or_more_mg_per_kg':summarize(z.loc[high])
    }
    return {
        'status':'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'data_status':'EXTRACTED_UNVERIFIED',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'oof_rows':int(len(z)),
        'distinct_fabrics':int(z['fabric_id'].nunique()),
        'overall':summarize(z),
        'high_release_400_plus':summarize(z.loc[high]),
        'high_release_all_underpredicted':bool((z.loc[high,'signed_error']>0).all()) if high.any() else None,
        'top_two_error_fabrics': [{'fabric_id':str(fid),'squared_error_share_pct':json_num(100*sq/total_sq) if total_sq else None} for fid,sq in top2.items()],
        'top_two_combined_squared_error_share_pct':json_num(100*top2.sum()/total_sq) if total_sq else None,
        'by_release_level_descriptive_only':by_level,
        'by_wash':by_wash,
        'by_description_keyword_proxy':by_text,
        'sensitivity_no_refit':{
            'all_fabrics':summarize(z),
            'excluding_two_worst_error_fabrics':summarize(z.loc[~z['fabric_id'].isin(top2.index)]),
            'warning':'This is a descriptive exclusion on existing OOF predictions. It is NOT retraining, not unbiased model selection, and not evidence that difficult fabrics can be omitted.'
        },
        'warnings':[
            'Source workbook extraction is not manually verified.',
            'All thresholds, text-based groups and extreme-fabric rankings are post-hoc exploratory.',
            'Error bands use measured outcomes, so are analysis-only, never inference-time gating.',
            'Description keywords are proxies, not validated pile height or fibre morphology measurements.',
            'Repeated washes from the same fabric are correlated; observation counts are not independent specimens.',
        ]
    }

def compare_features(data:pd.DataFrame):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    needed={'fabric_id','study_id','source_doi','record_status','description','release_mg_per_kg',*BASE_CAT,*BASE_NUM}
    missing=sorted(needed-set(data.columns))
    if missing: raise ValueError(f'Missing data columns: {missing}')
    if len(data)<20 or data['fabric_id'].nunique()<10: raise ValueError('Need >=20 observations and >=10 fabrics')
    if not data['study_id'].eq(STUDY).all() or not data['source_doi'].eq(DOI).all(): raise ValueError('Unexpected research source')
    if not data['record_status'].eq('EXTRACTED_UNVERIFIED').all(): raise ValueError('This script expects v0.15 extracted records')
    if data.duplicated(['fabric_id','wash_number']).any(): raise ValueError('Duplicate fabric/wash records')
    y=pd.to_numeric(data['release_mg_per_kg'],errors='raise').to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y<0).any(): raise ValueError('Invalid targets')
    x=data[BASE_CAT+BASE_NUM].copy()
    for c in BASE_CAT: x[c]=x[c].fillna('').astype(str).str.strip().replace({'':'unreported'})
    for c in BASE_NUM: x[c]=pd.to_numeric(x[c],errors='coerce')
    if x['wash_number'].isna().any() or not x['wash_number'].between(1,5).all():raise ValueError('Invalid wash number')
    tags=data['description'].fillna('').map(text_tags)
    for tag,_ in RULES: x[tag]=tags.map(lambda v:v[tag])
    groups=data['fabric_id'].astype(str).to_numpy()
    split=list(GroupKFold(n_splits=5).split(x,y,groups))
    trials={
        'rf_original_features':('forest',BASE_CAT,BASE_NUM),
        'rf_plus_description_keywords':('forest',BASE_CAT,BASE_NUM+[t for t,_ in RULES]),
        'ridge_original_features':('ridge',BASE_CAT,BASE_NUM),
        'ridge_plus_description_keywords':('ridge',BASE_CAT,BASE_NUM+[t for t,_ in RULES])
    }
    pred_detail=pd.DataFrame({'fabric_id':groups,'wash_number':x['wash_number'].astype(int),'measured_mg_per_kg':y})
    metrics={}
    for name,(kind,cats,nums) in trials.items():
        predictions=np.full(len(data),np.nan)
        fold_metrics=[]
        for fold,(tr,te) in enumerate(split,start=1):
            if set(groups[tr]) & set(groups[te]):raise AssertionError('Group leakage')
            transformers=[('categorical',Pipeline([
                ('imputer',SimpleImputer(strategy='most_frequent')),
                ('encoder',OneHotEncoder(handle_unknown='ignore'))]),cats)]
            if kind=='ridge':
                transformers.append(('numeric',Pipeline([
                    ('imputer',SimpleImputer(strategy='median')),
                    ('scale',StandardScaler())]),nums))
                estimator=Ridge(alpha=10.0)
            else:
                transformers.append(('numeric',SimpleImputer(strategy='median'),nums))
                estimator=RandomForestRegressor(n_estimators=250,min_samples_leaf=2,random_state=42,n_jobs=-1)
            reg=Pipeline([('preprocess',ColumnTransformer(transformers)),('model',estimator)])
            reg.fit(x.iloc[tr][cats+nums],np.log1p(y[tr]))
            p=np.maximum(0,np.expm1(reg.predict(x.iloc[te][cats+nums])))
            predictions[te]=p
            fold_metrics.append({'fold':fold,'n':int(len(te)),'mae_mg_per_kg':json_num(mean_absolute_error(y[te],p))})
        metrics[name]={
            'mae_mg_per_kg':json_num(mean_absolute_error(y,predictions)),
            'rmse_mg_per_kg':json_num(np.sqrt(mean_squared_error(y,predictions))),
            'r2':json_num(r2_score(y,predictions)),
            'folds':fold_metrics
        }
        pred_detail[name+'_prediction']=predictions
    base=metrics['rf_original_features']['mae_mg_per_kg']
    augmented=metrics['rf_plus_description_keywords']['mae_mg_per_kg']
    return {'evaluation':'Fixed 5-fold GroupKFold by fabric ID; same holdouts across all models; no parameter tuning',
            'keyword_features':[n for n,_ in RULES],
            'keyword_definitions':'Transparent regular-expression matches on specimen descriptions only; no direct morphological measurement',
            'models':metrics,
            'rf_keyword_mae_delta_vs_original_mg_per_kg':json_num(augmented-base),
            'interpretation':'A smaller MAE is not sufficient to conclude that real pile morphology causes fibre release. Single-study, post-hoc exploratory comparison.',
            'warnings':['Hypothesis developed after inspecting earlier OOF errors; differences are exploratory, not a preregistered independent test.',
                        'Description terms may proxy sample identity or correlate with unmeasured confounders.',
                        'No hyperparameter search or deployment thresholds established.']},pred_detail

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--oof',type=Path,default=Path('data/vassilenko_oof_predictions.csv'))
    p.add_argument('--csv',type=Path,default=None,help='Optional source-extracted CSV; needed for the ablation experiment')
    p.add_argument('--report',type=Path,default=Path('data/vassilenko_surface_analysis.json'))
    p.add_argument('--comparison-csv',type=Path,default=Path('data/vassilenko_surface_comparison_oof.csv'))
    args=p.parse_args()
    if not args.oof.is_file():raise SystemExit(f'Missing OOF file: {args.oof}. First run diagnose_vassilenko.py.')
    current_oof=pd.read_csv(args.oof,keep_default_na=False)
    report=diagnostics(current_oof)
    if args.csv is not None:
        if not args.csv.is_file():raise SystemExit(f'Missing source data CSV: {args.csv}')
        source=pd.read_csv(args.csv,keep_default_na=False)
        if len(source)!=len(current_oof) or set(zip(source.fabric_id,source.wash_number.astype(int)))!=set(zip(current_oof.fabric_id,current_oof.wash_number.astype(int))):
            raise ValueError('Extracted source and OOF records are not the same fabric/wash set.')
        trial,predictions=compare_features(source)
        report['exploratory_feature_ablation']=trial
        args.comparison_csv.parent.mkdir(parents=True,exist_ok=True)
        predictions.to_csv(args.comparison_csv,index=False)
    else:
        report['exploratory_feature_ablation']={'status':'NOT_RUN','reason':'Provide --csv with source-extracted wash records to compare models'}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    result={'status':report['status'], 'rows':report['oof_rows'], 'top_two_error_share_pct':report['top_two_combined_squared_error_share_pct'],
            'high_release':report['high_release_400_plus'],
            'feature_ablation':report['exploratory_feature_ablation'].get('status','COMPLETED')}
    if args.csv is not None:
        result['model_comparison_mae']={k:v['mae_mg_per_kg'] for k,v in trial['models'].items()}
    print(json.dumps(result,indent=2))
    print('Saved:',args.report)
    if args.csv is not None:print('Saved:',args.comparison_csv)

if __name__=='__main__':main()
