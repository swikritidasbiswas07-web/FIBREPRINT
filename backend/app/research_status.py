"""Read-only, authenticated experimental research status. No model is trained/served here."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from .auth import current_user

router = APIRouter(prefix='/api/research', tags=['research'])
DATA = Path(__file__).resolve().parents[1] / 'data'


def _load(filename):
    path = DATA / filename
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return obj if isinstance(obj, dict) else None
    except (FileNotFoundError, OSError, ValueError):
        return None


def research_snapshot():
    audit = _load('vassilenko_source_alignment.json')
    conformal = _load('vassilenko_group_conformal.json')
    applicability = _load('vassilenko_applicability_report.json')
    external = _load('cross_study_gate_report.json')
    valid_audit = bool(audit and audit.get('status') == 'STRUCTURAL_AUDIT_PASS'
                       and audit.get('matched_source_cells') == audit.get('valid_source_mass_cells') == 155
                       and audit.get('csv_rows') == 155
                       and audit.get('csv_fabric_count') == 37
                       and not audit.get('mismatches'))
    sha = audit.get('source_file_sha256') if valid_audit else None
    def same_source(document):
        return bool(sha and document and document.get('source_file_sha256', document.get('source_workbook_sha256')) == sha)
    conformal_ok = bool(same_source(conformal) and conformal.get('status') == 'RESEARCH_ONLY_NOT_DEPLOYABLE'
                        and conformal.get('analysis') == 'EXPLORATORY_FABRIC_GROUP_SPLIT_CONFORMAL_NOT_EXTERNALLY_VALIDATED'
                        and conformal.get('summary', {}).get('n_repetitions') == 20)
    applicability_ok = bool(same_source(applicability) and applicability.get('status') == 'RESEARCH_ONLY_NOT_DEPLOYABLE'
                             and applicability.get('audit') == 'STRUCTURAL_AUDIT_PASS'
                             and applicability.get('analysis') == 'POSTHOC_FIXED_FLAG_APPLICABILITY_DIAGNOSTIC')
    gate_blocked = bool(external and external.get('status') == 'BLOCKED_EXTERNAL_VALIDATION'
                        and external.get('external_predictions_evaluated') == 0)
    # Missing reports are UNKNOWN, not silently assumed to pass or fail.
    external_status = ('BLOCKED_EXTERNAL_VALIDATION' if gate_blocked else
                       'REPORT_NOT_VERIFIED' if external else 'REPORT_NOT_FOUND')
    summary = applicability.get('summary', {}) if applicability_ok else {}
    missed = None
    caught = None
    total = summary.get('total_interval_violations')
    if isinstance(total, int) and total >= 0:
        # Older v0.22 reports incorrectly called caught failures "missed".
        caught = summary.get('caught_interval_violations_by_warning',
                             summary.get('missed_interval_violations_by_warning'))
        if isinstance(caught, int) and 0 <= caught <= total:
            missed = total - caught
        else:
            caught = None
    return {
        'status': 'RESEARCH_ONLY_NOT_DEPLOYABLE',
        'serving_prediction_enabled': False,
        'source_integrity': {
            'status': 'STRUCTURAL_AUDIT_PASS' if valid_audit else 'NOT_VERIFIED',
            'matched_mass_measurements': 155 if valid_audit else None,
            'source_fabrics': 37 if valid_audit else None,
        },
        'experiments': {
            'group_conformal_status': 'RUN_AND_DOCUMENTED' if conformal_ok else 'NOT_VERIFIED',
            'applicability_status': 'RUN_AND_DOCUMENTED' if applicability_ok else 'NOT_VERIFIED',
            'repetitions': 20 if conformal_ok else None,
            'diagnostic_interval_failures_flagged': caught,
            'diagnostic_interval_failures_unflagged': missed,
            'diagnostic_total_interval_failures': total if caught is not None else None,
        },
        'external_validation': {
            'status': external_status,
            'candidate': external.get('candidate_study') if gate_blocked else None,
            'external_predictions_evaluated': 0 if gate_blocked else None,
            'blockers': external.get('hard_blockers', []) if gate_blocked else [],
        },
        'message': 'Research experiments are documented; no independently validated serving model is installed or approved.',
        'limitations': 'Single-study development, reused specimens across repeats, wide intervals and unverified external transfer.',
    }


@router.get('/status')
def get_research_status(user=Depends(current_user)):
    return research_snapshot()
