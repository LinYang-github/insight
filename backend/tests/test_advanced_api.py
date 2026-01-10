import pytest
import io
import json
import pandas as pd
from app.models.dataset import Dataset

@pytest.fixture
def auth_headers(client):
    """Register and Login to get token"""
    # 1. Register
    client.post("/api/auth/register", json={
        "username": "api_tester",
        "email": "api@test.com",
        "password": "password123"
    })
    # 2. Login
    resp = client.post("/api/auth/login", json={
        "username": "api_tester",
        "password": "password123"
    })
    token = resp.get_json()['token']
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def project_with_data(client, auth_headers):
    """Create Project and Upload Dummy CSV"""
    # 1. Create Project
    resp = client.post("/api/projects/", headers=auth_headers, json={
        "name": "Advanced API Project",
        "description": "Integration Test"
    })
    project_id = resp.get_json()['id']
    
    # 2. Upload File
    # Create dummy data suitable for survival/logistic
    # Age, Sex, Exposure, Duration, Event
    csv_content = "age,sex,exposure,duration,event\n"
    import random
    random.seed(42)
    # Generate 100 rows for better stability
    csv_content = "age,sex,exposure,duration,event\n"
    for i in range(100):
        age = random.randint(30, 80)
        sex = "M" if random.random() > 0.5 else "F"
        exposure = random.uniform(0, 100)
        # Duration correlates with exposure
        duration = 10 + 0.5 * exposure + random.normalvariate(0, 5)
        if duration < 1: duration = 1
        # Event correlates with Age
        # Logit(p) = -5 + 0.1*age
        p_event = 1 / (1 + 2.718**-(-5 + 0.08*age))
        event = 1 if random.random() < p_event else 0
        
        csv_content += f"{age},{sex},{exposure:.2f},{duration:.2f},{event}\n"
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'study_data.csv')
    }
    resp = client.post(f"/api/data/upload/{project_id}", headers=auth_headers, data=data, content_type='multipart/form-data')
    dataset_id = resp.get_json()['dataset_id']
    return dataset_id

def test_rcs_endpoint(client, auth_headers, project_with_data):
    """Test /advanced/rcs endpoint"""
    payload = {
        "dataset_id": project_with_data,
        "target": "event",
        "event_col": None,
        "exposure": "exposure",
        "covariates": ["age"],
        "model_type": "logistic",
        "knots": 3
    }
    resp = client.post("/api/advanced/rcs", headers=auth_headers, json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'plot_data' in data
    assert 'methodology' in data
    assert len(data['plot_data']) == 100

def test_subgroup_endpoint(client, auth_headers, project_with_data):
    """Test /advanced/subgroup endpoint"""
    payload = {
        "dataset_id": project_with_data,
        "target": "duration",
        "event_col": "event",
        "exposure": "exposure",
        "subgroups": ["sex"], # Categorical 'sex' in csv
        "covariates": ["age"],
        "model_type": "cox"
    }
    resp = client.post("/api/advanced/subgroup", headers=auth_headers, json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'forest_data' in data
    assert 'methodology' in data
    assert len(data['forest_data']) == 1 # One subgroup variable 'sex'

def test_nomogram_endpoint(client, auth_headers, project_with_data):
    """Test /advanced/nomogram endpoint"""
    payload = {
        "dataset_id": project_with_data,
        "target": "event",
        "event_col": None,
        "model_type": "logistic",
        "predictors": ["age", "exposure"]
    }
    resp = client.post("/api/advanced/nomogram", headers=auth_headers, json=payload)
    assert resp.status_code == 200, f"Nomogram failed: {resp.get_json()}"
    data = resp.get_json()
    assert 'variables' in data
    assert 'variables' in data
    assert 'risk_table' in data
    assert 'methodology' in data
    assert len(data['risk_table']) > 0

def test_missing_dataset_404(client, auth_headers):
    """Test invalid dataset ID"""
    payload = {
        "dataset_id": 99999,
        "target": "event"
    }
    resp = client.post("/api/advanced/rcs", headers=auth_headers, json=payload)
    assert resp.status_code == 404

def test_rcs_invalid_params(client, auth_headers, project_with_data):
    """Test RCS with invalid knots"""
    payload = {
        "dataset_id": project_with_data,
        "target": "event",
        "exposure": "exposure",
        "knots": 1 # Invalid
    }
    resp = client.post("/api/advanced/rcs", headers=auth_headers, json=payload)
    assert resp.status_code != 200

def test_nomogram_missing_params(client, auth_headers, project_with_data):
    """Test Nomogram without predictors"""
    payload = {
        "dataset_id": project_with_data,
        "target": "event"
    }
    resp = client.post("/api/advanced/nomogram", headers=auth_headers, json=payload)
    assert resp.status_code == 400
