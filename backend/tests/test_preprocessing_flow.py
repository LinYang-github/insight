
import pytest
import pandas as pd
import os
import io
from app import create_app, db
from app.models.dataset import Dataset

@pytest.fixture
def app():
    app = create_app('app.config.TestConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_header(client):
    client.post('/api/auth/register', json={'username': 'test', 'email': 'test@example.com', 'password': 'password'})
    resp = client.post('/api/auth/login', json={'username': 'test', 'password': 'password'})
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}

def test_preprocessing_and_metadata_flow(app, client, auth_header):
    """
    Test the full flow: Upload -> Health Check (Impute) -> Verify Metadata
    This ensures regressions like 'Invalid Keyword Argument' do not recur.
    """
    # 1. Create Project
    p_resp = client.post('/api/projects/', json={'name': 'Flow Project', 'description': 'desc'}, headers=auth_header)
    assert p_resp.status_code == 201
    project_id = p_resp.get_json()['id']

    # 2. Upload Data (with missing values)
    csv_content = "age,bmi,outcome\n25,22.0,0\n30,,1\n,24.0,0\n" # 3 rows, missing bmi, missing age
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_flow.csv')
    }
    u_resp = client.post(f'/api/data/upload/{project_id}', data=data, content_type='multipart/form-data', headers=auth_header)
    assert u_resp.status_code == 201
    dataset_id = u_resp.get_json()['dataset_id']

    # 3. Call Impute (Smart Fix Logic simulation)
    # Strategy: Mean for Age, Mode for BMI (or whatever)
    strategies = {
        'age': 'mean',
        'bmi': 'mean'
    }
    
    i_resp = client.post('/api/preprocessing/impute', json={
        'dataset_id': dataset_id,
        'strategies': strategies
    }, headers=auth_header)
    
    # ASSERTION 1: API should return 200 (Catches 'filename' keyword error)
    assert i_resp.status_code == 200, f"Impute failed: {i_resp.text}"
    
    new_dataset_id = i_resp.get_json()['new_dataset_id']
    assert new_dataset_id is not None

    # 4. Verify New Dataset Metadata (Catches missing metadata error)
    with app.app_context():
        new_ds = Dataset.query.get(new_dataset_id)
        assert new_ds is not None
        assert '_imputed' in new_ds.name
        
        # Check Metadata
        meta = new_ds.meta_data
        assert meta is not None, "Metadata should be generated for processed dataset"
        assert 'variables' in meta
        
        # Verify imputation happened (optional, checks service logic)
        variables = meta['variables']
        age_var = next(v for v in variables if v['name'] == 'age')
        # In processed file, missing count should be 0 (if logic worked)
        # Note: DataService calculates missing count from file
        assert age_var['missing_count'] == 0, "Age should be imputed"

    print("Test Passed: Imputation API and Metadata Generation are correct.")
