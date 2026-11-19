import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

@pytest.fixture(autouse=True)
def temp_db(tmp_path,monkeypatch):
    monkeypatch.setenv('FIBREPRINT_DB_PATH', str(tmp_path/'test.sqlite3'))

def auth_headers():
    result=client.post('/api/auth/register',json={
        'name':'Test Researcher','email':'researcher@example.org','password':'testing-a-secure-passphrase'})
    assert result.status_code==201,result.text
    return {'Authorization':'Bearer '+result.json()['access_token']}

def test_health():
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['status']=='ok'

def test_registration_login_session_logout():
    headers=auth_headers()
    assert client.get('/api/auth/me',headers=headers).json()['email']=='researcher@example.org'
    assert client.post('/api/auth/login',json={'email':'researcher@example.org','password':'wrong-password'}).status_code==401
    logged=client.post('/api/auth/login',json={'email':'researcher@example.org','password':'testing-a-secure-passphrase'})
    assert logged.status_code==200
    assert client.post('/api/auth/register',json={'name':'Another','email':'researcher@example.org','password':'any-long-password'}).status_code==409
    assert client.post('/api/auth/logout',headers=headers).status_code==200
    assert client.get('/api/auth/me',headers=headers).status_code==401

def test_protection():
    assert client.post('/api/evaluate',json={'fabric':{},'wash':{}}).status_code==401
    assert client.post('/api/validate-csv',json={'csv_text':'a,b\n1,2'}).status_code==401

def test_no_fabricated_prediction():
    headers=auth_headers()
    r=client.post('/api/evaluate',json={'fabric':{'name':'Sample','primary_fibre':'polyester','construction':'knit'},'wash':{'temperature_c':30,'duration_min':45,'cycle':'delicate'}},headers=headers)
    assert r.status_code==200
    assert r.json()['prediction'] is None and r.json()['prediction_status']=='NOT_VALIDATED'

def test_validate_csv_schema():
    headers=auth_headers()
    r=client.post('/api/validate-csv',json={'csv_text':'study_id,fabric_id\nexample,one'},headers=headers)
    assert r.status_code==200
    assert not r.json()['valid'] and 'release_mg_per_kg' in r.json()['missing_columns']
