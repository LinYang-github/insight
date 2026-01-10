import pytest
import io
import json

@pytest.fixture
def auth_headers(client):
    """Register and Login to get token"""
    # 1. Register
    client.post("/api/auth/register", json={
        "username": "long_tester",
        "email": "long@test.com",
        "password": "password123"
    })
    # 2. Login
    resp = client.post("/api/auth/login", json={
        "username": "long_tester",
        "password": "password123"
    })
    token = resp.get_json()['token']
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def longitudinal_data(client, auth_headers):
    """Create Project and Upload Longitudinal CSV"""
    resp = client.post("/api/projects/", headers=auth_headers, json={
        "name": "Longitudinal Project",
        "description": "LMM Test"
    })
    project_id = resp.get_json()['id']
    
    # Create Longitudinal Data: 10 subjects, 5 visits each
    csv_content = "id,time,outcome,group\n"
    for pid in range(1, 11):
        # Two groups: 1-5 Group A, 6-10 Group B
        grp = "A" if pid <= 5 else "B"
        slope = 1.0 if grp == "A" else -0.5
        intercept = 10
        for t in range(5):
            val = intercept + slope * t
            csv_content += f"{pid},{t},{val},{grp}\n"
            
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'long_data.csv')
    }
    resp = client.post(f"/api/data/upload/{project_id}", headers=auth_headers, data=data, content_type='multipart/form-data')
    return resp.get_json()['dataset_id']

def test_lmm_endpoint(client, auth_headers, longitudinal_data):
    payload = {
        "dataset_id": longitudinal_data,
        "id_col": "id",
        "time_col": "time",
        "outcome_col": "outcome",
        "fixed_effects": ["group"]
    }
    resp = client.post("/api/longitudinal/lmm", headers=auth_headers, json=payload)
    assert resp.status_code == 200, f"LMM failed: {resp.get_json()}"
    data = resp.get_json()
    results = data['results']
    assert 'summary' in results
    assert 'random_effects' in results
    assert 'methodology' in results
    assert len(results['summary']) > 0

def test_clustering_endpoint(client, auth_headers, longitudinal_data):
    payload = {
        "dataset_id": longitudinal_data,
        "id_col": "id",
        "time_col": "time",
        "outcome_col": "outcome",
        "n_clusters": 2
    }
    resp = client.post("/api/longitudinal/clustering", headers=auth_headers, json=payload)
    assert resp.status_code == 200, f"Clustering failed: {resp.get_json()}"
    data = resp.get_json()
    results = data['results']
    assert 'clusters' in results
    assert 'centroids' in results
    assert 'methodology' in results
    assert len(results['centroids']) == 2

def test_variability_endpoint(client, auth_headers, longitudinal_data):
    payload = {
        "dataset_id": longitudinal_data,
        "id_col": "id",
        "outcome_col": "outcome"
    }
    resp = client.post("/api/longitudinal/variability", headers=auth_headers, json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    results = data['results']
    assert 'variability_data' in results
    assert 'methodology' in results
    assert len(results['variability_data']) == 10
