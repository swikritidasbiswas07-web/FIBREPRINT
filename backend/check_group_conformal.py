"""FIBREPRINT v0.21: exploratory, fabric-group split-conformal evaluation.

Run from backend:
  .venv\\Scripts\\python.exe check_group_conformal.py --csv data/vassilenko_extracted_washes.csv --audit data/vassilenko_source_alignment.json

No deployment artifact, no guaranteed interval, no external validation.
The same source study informed earlier model selection, so these repetitions
are a diagnostic of in-study reliability, NOT independent confirmation.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CAT = ['fabric_type','yarn_type','construction','mechanical_finishing','mechanical_presence']
NUM = ['density_gsm','wash_number','polyester_pct','cotton_pct','nylon_pct','elastane_pct',
       'polyurethane_pct','spandex_pct','polyamide_pct','wool_pct']
KEYWORDS = {
    'explicit_raised_surface': r'\b(?:velour|pile|shaggy|brushed|fuzzy|napped|sanded|raised)\b',
    'fleece_term': r'\bfleece\b',
    'jersey_term': r'\bjersey\b',
    'woven_or_plaid_term': r'\b(?:woven|plaid|denim|twill)\b',
}


def load_data(csv_path: Path, audit_path: Path):
    if not audit_path.is_file():
        raise ValueError(f'Missing audit file: {audit_path}. Run v0.19 source audit first.')
    audit=json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status')!='STRUCTURAL_AUDIT_PASS' or audit.get('mismatches'):
        raise ValueError('Source alignment audit is missing a clean STRUCTURAL_AUDIT_PASS')
    data=pd.read_csv(csv_path,keep_default_na=False)
    required=set(CAT+NUM+['fabric_id','description','release_mg_per_kg','study_id','source_doi','record_status'])
    missing=sorted(required-set(data.columns))
    if missing: raise ValueError(f'CSV is missing columns: {missing}')
    if data['fabric_id'].nunique()<30: raise ValueError('Need at least 30 distinct fabric groups for these splits')
    if len(data)!=int(audit.get('csv_rows',-1)) or data['fabric_id'].nunique()!=int(audit.get('csv_fabric_count',-1)):
        raise ValueError('CSV row/fabric counts no longer match the audited dataset; rerun source audit')
    if data.duplicated(['fabric_id','wash_number']).any():
        raise ValueError('Duplicate fabric/wash combination')
    if not data['study_id'].eq('vassilenko_2021').all() or not data['source_doi'].eq('10.1371/journal.pone.0250346').all():
        raise ValueError('Unexpected study metadata')
    if not data['record_status'].eq('EXTRACTED_UNVERIFIED').all():
        raise ValueError('Unexpected record status')
    y=pd.to_numeric(data['release_mg_per_kg'],errors='raise').to_numpy(dtype=float)
    if not np.isfinite(y).all() or (y<0).any():raise ValueError('Invalid release mass target')
    x=data[CAT+NUM].copy()
    for c in CAT:x[c]=x[c].fillna('').astype(str).str.strip().replace({'':'unreported'})
    for c in NUM:x[c]=pd.to_numeric(x[c],errors='coerce')
    if not x['wash_number'].between(1,5).all(): raise ValueError('Wash number must be between 1 and 5')
    for name,pattern in KEYWORDS.items():
        x[name]=data['description'].fillna('').astype(str).str.contains(pattern,flags=re.I,regex=True).astype(int)
    return data,x,y,data['fabric_id'].astype(str).to_numpy(),audit


def make_pipeline():
    num=NUM+list(KEYWORDS)
    preprocess=ColumnTransformer([
        ('categorical',Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),
                                 ('ohe',OneHotEncoder(handle_unknown='ignore'))]),CAT),
        ('numeric',Pipeline([('imputer',SimpleImputer(strategy='median')),
                            ('scaler',StandardScaler())]),num)
    ])
    return Pipeline([('preprocess',preprocess),('ridge',Ridge(alpha=10.0))])


def split_groups(unique_groups, rng):
    """Independent fabric lists; target values never used to select groups."""
    groups=np.array(unique_groups,dtype=str)
    shuffled=rng.permutation(groups)
    # for 37 groups: 19 train, 10 calibration, 8 test
    n_test=max(6,int(round(len(groups)*.22)))
    n_cal=max(10,int(round(len(groups)*.27)))
    n_train=len(groups)-n_test-n_cal
    if n_train<10:raise ValueError('Insufficient training fabric groups')
    return (shuffled[:n_train],shuffled[n_train:n_train+n_cal],shuffled[n_train+n_cal:])


def conformal_radius(calibration_max_residuals, alpha):
    """Finite-sample group-level split-conformal rank, one max residual per fabric.

    This is an exploratory group-max construction. No formal coverage guarantee
    is claimed due to post-hoc model selection and one-source data.
    """
    a=np.sort(np.asarray(calibration_max_residuals,dtype=float))
    k=int(math.ceil((len(a)+1)*(1-alpha)))
    if k>len(a):return float('inf'),k
    return float(a[k-1]),k


def applicability_flags(x, tr_idx, eval_idx):
    """Pre-outcome flags only; does not use release measurements."""
    train=x.iloc[tr_idx]
    eval_x=x.iloc[eval_idx]
    flagged=[]
    for _,r in eval_x.iterrows():
        reasons=[]
        for cat in CAT:
            if r[cat] not in set(train[cat]):reasons.append('unseen_category:'+cat)
        for num in ['density_gsm']:
            vals=train[num].dropna().to_numpy(float)
            if len(vals) and np.isfinite(r[num]) and (r[num]<np.min(vals) or r[num]>np.max(vals)):
                reasons.append('outside_training_range:'+num)
        flagged.append(reasons)
    return flagged


def run(csv_path, audit_path, output_report, output_details, repeats=20, alpha=.10, seed=2026):
    if not 2<=repeats<=100:raise ValueError('Repetitions must be between 2 and 100')
    if not .05<=alpha<=.3:raise ValueError('alpha must be between .05 and .30')
    data,x,y,groups,audit=load_data(csv_path,audit_path)
    unique=np.unique(groups)
    rng=np.random.default_rng(seed)
    columns=CAT+NUM+list(KEYWORDS)
    summaries=[]
    observations=[]
    for repetition in range(1,repeats+1):
        tr_groups,cal_groups,te_groups=split_groups(unique,rng)
        tr=np.flatnonzero(np.isin(groups,tr_groups))
        cal=np.flatnonzero(np.isin(groups,cal_groups))
        te=np.flatnonzero(np.isin(groups,te_groups))
        assert not(set(groups[tr])&set(groups[cal]) or set(groups[tr])&set(groups[te]) or set(groups[cal])&set(groups[te]))
        model=make_pipeline()
        model.fit(x.iloc[tr][columns],np.log1p(y[tr]))
        cal_prediction=np.maximum(0,np.expm1(model.predict(x.iloc[cal][columns])))
        cal_abs=np.abs(y[cal]-cal_prediction)
        cal_per_fabric=pd.DataFrame({'fabric_id':groups[cal],'err':cal_abs}).groupby('fabric_id')['err'].max()
        q,rank=conformal_radius(cal_per_fabric.to_numpy(),alpha)
        p=np.maximum(0,np.expm1(model.predict(x.iloc[te][columns])))
        lower=np.maximum(0,p-q)
        upper=p+q
        inside=(y[te]>=lower)&(y[te]<=upper)
        flags=applicability_flags(x,tr,te)
        high=y[te]>=400  # analysis ONLY. Cannot be an inference-time risk flag.
        fabric_coverage=[]
        for fabric in te_groups:
            mask=groups[te]==fabric
            fabric_coverage.append(bool(inside[mask].all()))
        summaries.append({
            'repeat':repetition,'n_train_fabrics':len(tr_groups),'n_calibration_fabrics':len(cal_groups),
            'n_test_fabrics':len(te_groups),'n_test_rows':len(te),
            'conformal_rank':rank,'band_half_width_mg_per_kg':q,
            'test_mae_mg_per_kg':float(np.mean(np.abs(y[te]-p))),
            'test_observation_coverage':float(np.mean(inside)),
            'test_fabric_simultaneous_coverage':float(np.mean(fabric_coverage)),
            'n_high_release_rows':int(high.sum()),
            'high_release_coverage_descriptive_only':float(np.mean(inside[high])) if high.any() else None,
            'n_applicability_flagged_rows':sum(bool(f) for f in flags),
        })
        for j,row_idx in enumerate(te):
            observations.append({
                'repeat':repetition,'fabric_id':groups[row_idx], 'wash_number':int(x.iloc[row_idx]['wash_number']),
                'measured_mg_per_kg':float(y[row_idx]),'predicted_mg_per_kg':float(p[j]),
                'lower_mg_per_kg':float(lower[j]),'upper_mg_per_kg':float(upper[j]),
                'inside_band':bool(inside[j]),
                'high_release_observed_posthoc':bool(high[j]),
                'applicability_flag_preoutcome':bool(flags[j]),
                'applicability_reasons':'|'.join(flags[j]),
            })
    out=pd.DataFrame(observations)
    widths=np.array([r['band_half_width_mg_per_kg'] for r in summaries])
    report={
        'status':'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'analysis':'EXPLORATORY_FABRIC_GROUP_SPLIT_CONFORMAL_NOT_EXTERNALLY_VALIDATED',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'source_alignment_status':audit['status'],
        'source_file_sha256':audit.get('source_file_sha256'),
        'source_dataset':str(csv_path),'distinct_fabrics':int(len(unique)),'observations':int(len(data)),
        'protocol':{
            'repetitions':repeats,'random_seed':seed,'nominal_alpha':alpha,
            'partition':'unique fabric groups into train / calibration / test (no shared fabrics)',
            'calibration_score':'maximum absolute error across recorded washes within each calibration fabric',
            'calibration_quantile':'ceil((number of calibration fabrics + 1) * (1-alpha)) order statistic',
            'model':'Ridge(alpha=10), log1p target, text keyword proxies fixed from earlier exploration',
            'risk_flags':'unseen categorical labels or GSM outside the current training range; no target information used',
        },
        'summary':{
            'n_repetitions':repeats,
            'median_band_half_width_mg_per_kg':float(np.median(widths)),
            'median_test_observation_coverage_across_repetitions':float(np.median([s['test_observation_coverage'] for s in summaries])),
            'median_test_fabric_simultaneous_coverage_across_repetitions':float(np.median([s['test_fabric_simultaneous_coverage'] for s in summaries])),
            'median_test_mae_mg_per_kg':float(np.median([s['test_mae_mg_per_kg'] for s in summaries])),
            'median_high_release_coverage_on_splits_with_high_release':float(np.median([s['high_release_coverage_descriptive_only'] for s in summaries if s['high_release_coverage_descriptive_only'] is not None])) if any(s['high_release_coverage_descriptive_only'] is not None for s in summaries) else None,
            'n_splits_without_high_release':sum(s['n_high_release_rows']==0 for s in summaries),
            'pooled_descriptive_test_observation_coverage':float(out['inside_band'].mean()),
            'pooled_descriptive_high_release_coverage':float(out.loc[out['high_release_observed_posthoc'],'inside_band'].mean()) if out['high_release_observed_posthoc'].any() else None,
            'pooled_applicability_flag_fraction':float(out['applicability_flag_preoutcome'].mean()),
        },
        'splits':summaries,
        'limitations':[
            'This study was previously used to select features and model type; repeated splits do not supply independent confirmation.',
            'Repeated test splits reuse specimens. Do not treat observations or repetitions as independent evidence.',
            'Group-max calibration controls an exploratory simultaneous-per-fabric score, not a validated individual-sample confidence claim.',
            'Finite-sample conformal coverage relies on exchangeability of new fabric groups; sampling conditions are not established here.',
            'Observed high-release labels use the target and are post-hoc diagnostics only.',
            'Description keywords are not measured physical morphology.',
            'A wide band may have high coverage yet little practical usefulness.',
            'Missing early wash values and experimental methods require source-protocol review.',
            'No model artifact is saved or approved for public predictions.',
        ]
    }
    output_report.parent.mkdir(parents=True,exist_ok=True)
    output_details.parent.mkdir(parents=True,exist_ok=True)
    output_report.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    out.to_csv(output_details,index=False)
    return report


def main():
    parser=argparse.ArgumentParser(description='FIBREPRINT grouped split-conformal research diagnostics')
    parser.add_argument('--csv',type=Path,default=Path('data/vassilenko_extracted_washes.csv'))
    parser.add_argument('--audit',type=Path,default=Path('data/vassilenko_source_alignment.json'))
    parser.add_argument('--report',type=Path,default=Path('data/vassilenko_group_conformal.json'))
    parser.add_argument('--predictions',type=Path,default=Path('data/vassilenko_group_conformal_predictions.csv'))
    parser.add_argument('--repeats',type=int,default=20)
    parser.add_argument('--alpha',type=float,default=.10)
    parser.add_argument('--seed',type=int,default=2026)
    a=parser.parse_args()
    result=run(a.csv,a.audit,a.report,a.predictions,a.repeats,a.alpha,a.seed)
    print(json.dumps({'status':result['status'],'protocol':result['protocol'],'summary':result['summary']},indent=2))
    print('Saved:',a.report,'and',a.predictions)

if __name__=='__main__':main()
