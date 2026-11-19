"""Evidence-gated inference for FIBREPRINT.

Only a locally trained, independently validated artifact marked DEPLOYABLE can
produce an emission prediction. No defaults, paper statistics or synthetic
training values are substituted for missing observations.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import joblib

ARTIFACT_DEFAULT = Path(__file__).resolve().parents[1] / 'data' / 'fibreprint_model.joblib'


def artifact_path() -> Path:
    return Path(os.environ.get('FIBREPRINT_MODEL_PATH', str(ARTIFACT_DEFAULT))).expanduser()


@lru_cache(maxsize=4)
def _load_at(path: str, mtime_ns: int):
    # joblib uses pickle; ONLY load artifacts produced and stored locally by
    # the trusted training script. Never accept model uploads from users.
    return joblib.load(path)


def load_artifact():
    path = artifact_path()
    if not path.is_file():
        return None
    return _load_at(str(path), path.stat().st_mtime_ns)


def model_status() -> dict:
    try:
        artifact = load_artifact()
    except Exception:
        return {'status': 'MODEL_ERROR', 'trained': False,
                'message': 'The locally stored model could not be loaded. Re-train or inspect the backend logs.'}
    if artifact is None:
        return {'status': 'NOT_TRAINED', 'trained': False,
                'message': 'No trained model is installed. Supply curated observations and run train_model.py.'}
    meta = artifact['metadata']
    return {'status': meta['status'], 'trained': True, 'message': meta['message'],
            'metrics': meta['metrics'], 'data_scope': meta['data_scope'],
            'target': meta['target'], 'model_name': meta['model_name']}


def evaluate_model(*, fibre_type, construction, temperature_c, water_fabric_ratio, wash_number,
                   measurement_method=None):
    status = model_status()
    base = {'prediction': None, 'prediction_unit': 'mg/kg fabric',
            'prediction_status': status['status'], 'model_info': status,
            'message': status['message']}
    if status['status'] != 'DEPLOYABLE':
        return base
    artifact = load_artifact()
    meta = artifact['metadata']
    if water_fabric_ratio is None or wash_number is None or temperature_c is None:
        base['prediction_status'] = 'MISSING_MODEL_INPUT'
        base['message'] = 'A wash mass, water volume, temperature and wash count are required.'
        return base
    if not measurement_method:
        base['prediction_status'] = 'METHOD_UNCONFIRMED'
        base['message'] = 'Confirm the measurement protocol used in the trained dataset.'
        return base
    if measurement_method != meta['measurement_method']:
        base['prediction_status'] = 'PROTOCOL_MISMATCH'
        base['message'] = 'The requested measurement method differs from the trained protocol.'
        return base

    inputs = {'fibre_type': fibre_type.lower(), 'construction': construction.lower(),
              'temperature_c': float(temperature_c), 'water_fabric_ratio': float(water_fabric_ratio),
              'wash_number': int(wash_number)}
    for name in ('fibre_type', 'construction'):
        if inputs[name] not in meta['categories'][name]:
            base['prediction_status'] = 'OUTSIDE_TRAINING_DOMAIN'
            base['message'] = f'{name} was not represented in the training data.'
            return base
    for name in ('temperature_c', 'water_fabric_ratio', 'wash_number'):
        lo, hi = meta['ranges'][name]
        if not lo <= inputs[name] <= hi:
            base['prediction_status'] = 'OUTSIDE_TRAINING_DOMAIN'
            base['message'] = f'{name} falls outside the range of training observations ({lo:g}–{hi:g}).'
            return base

    import pandas as pd
    import numpy as np
    frame = pd.DataFrame([inputs])
    predicted_log = float(artifact['estimator'].predict(frame)[0])
    prediction = float(np.expm1(predicted_log))
    prediction = max(0.0, prediction)
    # Calibration is an empirical, held-out absolute error bound in mg/kg.
    # It is not a guaranteed interval for every fabric or laboratory.
    radius = float(meta['calibration_abs_error_mg_per_kg'])
    return {
        **base, 'prediction': round(prediction, 3), 'prediction_status': 'MODEL_ESTIMATE',
        'interval': [round(max(0.0, prediction-radius), 3), round(prediction+radius, 3)],
        'interval_label': 'Empirical calibration error band, not a guaranteed 95% prediction interval',
        'message': 'Validated-domain estimate. Applies only to the dataset measurement protocol and recorded data scope.',
    }
