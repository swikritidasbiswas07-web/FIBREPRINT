"""FIBREPRINT v0.22: descriptive, pre-outcome applicability diagnostics.

This script ONLY reads existing held-out predictions from v0.21. It does not
fit a warning rule, optimize abstention cutoffs, retrain, or serve a model.
Repeated test appearances of the same fabrics are not independent.

Run from FIBREPRINT/backend:
  .venv\\Scripts\\python.exe analyze_applicability.py \\
    --predictions data/vassilenko_group_conformal_predictions.csv \\
    --audit data/vassilenko_source_alignment.json
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

COLUMNS = {
    'repeat','fabric_id','wash_number','measured_mg_per_kg',
    'predicted_mg_per_kg','lower_mg_per_kg','upper_mg_per_kg',
    'inside_band','high_release_observed_posthoc',
    'applicability_flag_preoutcome','applicability_reasons'
}


def parse_boolean(values, name):
    value = values.astype(str).str.strip().str.lower()
    ok = value.isin(['true','false','1','0'])
    if not ok.all():
        raise ValueError(f'Unexpected boolean values in {name}: {value[~ok].unique().tolist()}')
    return value.isin(['true','1'])


def safe_float(x):
    return float(x) if x is not None and np.isfinite(x) else None


def describe(d):
    if len(d)==0:
        return {'rows':0,'distinct_fabrics':0,'mae_mg_per_kg':None,
                'interval_coverage':None,'fabric_simultaneous_coverage':None,
                'high_release_observed_rows':0,'high_release_coverage_posthoc':None,
                'high_release_recall_of_warning_posthoc':None}
    high=d['high_release_observed_posthoc']
    group_coverage=d.groupby(['repeat','fabric_id'],sort=False)['inside_band'].all()
    return {
        'rows':int(len(d)),
        'distinct_fabrics':int(d['fabric_id'].nunique()),
        'mae_mg_per_kg':safe_float(np.abs(d['measured_mg_per_kg']-d['predicted_mg_per_kg']).mean()),
        'interval_coverage':safe_float(d['inside_band'].mean()),
        'fabric_simultaneous_coverage':safe_float(group_coverage.mean()),
        'high_release_observed_rows':int(high.sum()),
        'high_release_coverage_posthoc':safe_float(d.loc[high,'inside_band'].mean()) if high.any() else None,
    }


def analyse(predictions_path:Path,audit_path:Path,report_path:Path,rows_path:Path):
    audit=json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status')!='STRUCTURAL_AUDIT_PASS' or audit.get('mismatches'):
        raise ValueError('A clean v0.19 STRUCTURAL_AUDIT_PASS is required')
    d=pd.read_csv(predictions_path,keep_default_na=False)
    absent=COLUMNS-set(d.columns)
    if absent:raise ValueError('Missing prediction columns: '+', '.join(sorted(absent)))
    if len(d)==0:raise ValueError('No prediction rows')
    for col in ['inside_band','high_release_observed_posthoc','applicability_flag_preoutcome']:
        d[col]=parse_boolean(d[col],col)
    for col in ['measured_mg_per_kg','predicted_mg_per_kg','lower_mg_per_kg','upper_mg_per_kg','wash_number','repeat']:
        d[col]=pd.to_numeric(d[col],errors='raise')
    vals=d[['measured_mg_per_kg','predicted_mg_per_kg','lower_mg_per_kg','upper_mg_per_kg']].to_numpy(float)
    if not np.isfinite(vals).all():raise ValueError('Non-finite numeric values')
    if (vals<0).any() or (d['lower_mg_per_kg']>d['upper_mg_per_kg']).any():
        raise ValueError('Invalid nonnegative prediction interval')
    if d.duplicated(['repeat','fabric_id','wash_number']).any():
        raise ValueError('Duplicate repeat/fabric/wash prediction rows')
    if not d['wash_number'].isin([1,2,3,4,5]).all():raise ValueError('Invalid wash number')
    # Validate pre-existing flags and observable risk definitions; never use the measured target to flag.
    has_reasons=d['applicability_reasons'].astype(str).str.strip().ne('')
    if not np.array_equal(has_reasons.to_numpy(),d['applicability_flag_preoutcome'].to_numpy()):
        raise ValueError('Pre-outcome flag disagrees with recorded applicability reasons')
    check=(d['measured_mg_per_kg']>=d['lower_mg_per_kg']) & (d['measured_mg_per_kg']<=d['upper_mg_per_kg'])
    if not np.array_equal(check.to_numpy(),d['inside_band'].to_numpy()):
        raise ValueError('Coverage flags disagree with the stored bounds')
    high=d['measured_mg_per_kg']>=400
    if not np.array_equal(high.to_numpy(),d['high_release_observed_posthoc'].to_numpy()):
        raise ValueError('Post-hoc high-release flags disagree with measured target')

    d['absolute_error_mg_per_kg']=(d['measured_mg_per_kg']-d['predicted_mg_per_kg']).abs()
    d['interval_miss']=~d['inside_band']
    d['warning_preoutcome']=d['applicability_flag_preoutcome']
    d['decision']='ABSTAIN_UNFAMILIAR'  # fixed rule from v0.21, no cutoff fitted
    d.loc[~d['warning_preoutcome'],'decision']='RETAIN_FOR_DIAGNOSTIC'

    overall=describe(d)
    flagged=describe(d.loc[d['warning_preoutcome']])
    retained=describe(d.loc[~d['warning_preoutcome']])
    summary={
        'warning_rate':safe_float(d['warning_preoutcome'].mean()),
        'retained_fraction':safe_float((~d['warning_preoutcome']).mean()),
        'caught_interval_violations_by_warning':int((d['interval_miss']&d['warning_preoutcome']).sum()),
        'total_interval_violations':int(d['interval_miss'].sum()),
        'warning_recall_of_interval_miss':safe_float(d.loc[d['interval_miss'],'warning_preoutcome'].mean()) if d['interval_miss'].any() else None,
        'warning_precision_for_interval_miss':safe_float(d.loc[d['warning_preoutcome'],'interval_miss'].mean()) if d['warning_preoutcome'].any() else None,
        'high_release_warning_recall_posthoc':safe_float(d.loc[high,'warning_preoutcome'].mean()) if high.any() else None,
        'high_release_warning_count_posthoc':int((high&d['warning_preoutcome']).sum()),
        'high_release_observation_appearances_posthoc':int(high.sum()),
        'high_release_unflagged_appearances_posthoc':int((high&~d['warning_preoutcome']).sum()),
    }
    per_split=[]
    for rep,g in d.groupby('repeat',sort=True):
        rec={'repeat':int(rep),'n_test_rows':int(len(g)),'test_fabrics':int(g['fabric_id'].nunique())}
        rec['all']=describe(g)
        rec['retained']=describe(g.loc[~g['warning_preoutcome']])
        rec['flagged']=describe(g.loc[g['warning_preoutcome']])
        rec['warning_fraction']=safe_float(g['warning_preoutcome'].mean())
        rec['high_release_observations_posthoc']=int(g['high_release_observed_posthoc'].sum())
        per_split.append(rec)
    # Collapse to fabric/repeat. A fabric's washes form one evaluation group.
    per_fabric=(d.groupby(['repeat','fabric_id'],sort=True)
        .agg(n_washes=('wash_number','size'),flagged_washes=('warning_preoutcome','sum'),
             any_interval_miss=('interval_miss','any'),all_washes_covered=('inside_band','all'),
             fabric_mae=('absolute_error_mg_per_kg','mean'),
             any_high_release_observed_posthoc=('high_release_observed_posthoc','any'))
        .reset_index())
    per_fabric['flagged_fabric']=per_fabric['flagged_washes']>0
    by_fabric={
        'test_fabric_appearances':int(len(per_fabric)),
        'unique_fabrics_across_repeated_splits':int(per_fabric['fabric_id'].nunique()),
        'warning_rate_fabric_appearances':safe_float(per_fabric['flagged_fabric'].mean()),
        'warning_recall_of_any_interval_miss':safe_float(per_fabric.loc[per_fabric['any_interval_miss'],'flagged_fabric'].mean()) if per_fabric['any_interval_miss'].any() else None,
        'warning_recall_of_any_high_release_posthoc':safe_float(per_fabric.loc[per_fabric['any_high_release_observed_posthoc'],'flagged_fabric'].mean()) if per_fabric['any_high_release_observed_posthoc'].any() else None,
        'mean_fabric_mae_retained':safe_float(per_fabric.loc[~per_fabric['flagged_fabric'],'fabric_mae'].mean()),
        'mean_fabric_mae_flagged':safe_float(per_fabric.loc[per_fabric['flagged_fabric'],'fabric_mae'].mean()),
    }
    by_reason={}
    for reason in ['unseen_category','outside_training_range']:
        mask=d['applicability_reasons'].str.contains(reason,regex=False)
        by_reason[reason]=describe(d.loc[mask])

    result={
        'status':'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'analysis':'POSTHOC_FIXED_FLAG_APPLICABILITY_DIAGNOSTIC',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'audit':'STRUCTURAL_AUDIT_PASS',
        'source_workbook_sha256':audit.get('source_file_sha256'),
        'input_predictions':str(predictions_path),
        'rule':'Use the existing v0.21 pre-outcome flag: abstain for unseen categorical labels or GSM outside training range; no threshold selected from test outcomes.',
        'all':overall,'flagged':flagged,'retained':retained,
        'summary':summary,'fabric_appearance_level':by_fabric,
        'reason_types':by_reason,'per_split':per_split,
        'limitations':[
            'This is a diagnostic of a FIXED pre-existing warning, not an independently validated abstention policy.',
            'Test fabrics recur across 20 splits; pooled rows and fabric appearances are not independent observations.',
            'Even the repeated splits are from the study previously used for model and feature selection.',
            'High-release groups are defined using observed outcomes solely for retrospective evaluation.',
            'No new warning thresholds are fitted; do not interpret retained subset metrics as prospective performance guarantees.',
            'Grouping washes into fabric appearances does not make repeated appearances across splits independent.',
            'Prediction bands may remain too wide for practical use.',
            'This script does not train or deploy a model; future validation requires an independent dataset.'
        ]
    }
    report_path.parent.mkdir(parents=True,exist_ok=True)
    rows_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    per_fabric.to_csv(rows_path,index=False)
    return result


def main():
    p=argparse.ArgumentParser(description='FIBREPRINT v0.22: study-only pre-outcome applicability diagnostics')
    p.add_argument('--predictions',type=Path,default=Path('data/vassilenko_group_conformal_predictions.csv'))
    p.add_argument('--audit',type=Path,default=Path('data/vassilenko_source_alignment.json'))
    p.add_argument('--report',type=Path,default=Path('data/vassilenko_applicability_report.json'))
    p.add_argument('--fabric-report',type=Path,default=Path('data/vassilenko_applicability_by_fabric.csv'))
    a=p.parse_args()
    out=analyse(a.predictions,a.audit,a.report,a.fabric_report)
    print(json.dumps({'status':out['status'],'summary':out['summary'],
                      'fabric_appearance_level':out['fabric_appearance_level']},indent=2))
    print('Saved:',a.report,'and',a.fabric_report)

if __name__=='__main__':main()
