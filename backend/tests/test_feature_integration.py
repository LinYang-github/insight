
import pytest
import pandas as pd
import os
import io
from app import create_app, db
from app.models.dataset import Dataset
from app.models.project import Project
from app.services.data_service import DataService

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
    client.post('/api/auth/register', json={'username': 'qa', 'email': 'qa@example.com', 'password': 'password'})
    resp = client.post('/api/auth/login', json={'username': 'qa', 'password': 'password'})
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def sample_project_dataset(client, auth_header):
    # Setup project
    p_resp = client.post('/api/projects/', json={'name': 'QA Project', 'description': 'desc'}, headers=auth_header)
    project_id = p_resp.get_json()['id']
    
    # Upload data
    csv_content = "id,age,gender,outcome\n1,25,Male,0\n2,30,Female,1\n3,,Male,0\n4,40,Female,1\n"
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'qa_data.csv')
    }
    u_resp = client.post(f'/api/data/upload/{project_id}', data=data, content_type='multipart/form-data', headers=auth_header)
    return project_id, u_resp.get_json()['dataset_id']

def test_encoding_api_flow(app, client, auth_header, sample_project_dataset):
    """Verify that Categorical Encoding creates a new dataset with numeric columns."""
    project_id, dataset_id = sample_project_dataset
    
    # Act: Encode 'gender'
    resp = client.post('/api/preprocessing/encode', json={
        'dataset_id': dataset_id,
        'columns': ['gender']
    }, headers=auth_header)
    
    assert resp.status_code == 200
    new_id = resp.get_json()['new_dataset_id']
    
    # Check new dataset columns
    with app.app_context():
        new_ds = db.session.get(Dataset, new_id)
        df = DataService.load_data(new_ds.filepath)
        # 'gender' should be gone, replaced by 'gender_Male' or similar (drop_first=True)
        assert 'gender' not in df.columns
        # gender_Male should exist (since Female is usually first alphabetically and dropped as ref)
        # or depends on pandas. 
        assert any('gender_' in c for c in df.columns)
        assert df.select_dtypes(include=['number']).shape[1] > 0

def test_table1_export_api(client, auth_header, sample_project_dataset):
    """Verify Table 1 CSV export endpoint."""
    _, dataset_id = sample_project_dataset
    
    resp = client.post('/api/statistics/table1/export', json={
        'dataset_id': dataset_id,
        'variables': ['age', 'outcome'],
        'group_by': 'gender'
    }, headers=auth_header)
    
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    # Read content
    csv_str = resp.data.decode('utf-8-sig')
    df = pd.read_csv(io.StringIO(csv_str))
    assert 'Variable' in df.columns
    assert 'Overall' in df.columns
    assert 'Male' in df.columns
    assert 'Female' in df.columns
    assert 'P-value' in df.columns

def test_psm_save_dataset_flow(app, client, auth_header, sample_project_dataset):
    """Verify that PSM allows saving the matched dataset."""
    project_id, dataset_id = sample_project_dataset
    
    # Need better data for PSM (must have variation in treatment)
    # Re-uploading specific PSM data
    csv_content = "treat,age,outcome\n1,50,0\n1,51,1\n1,52,0\n0,30,1\n0,31,0\n0,50,1\n0,51,0\n0,52,1\n"
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'psm_data.csv')}
    u_resp = client.post(f'/api/data/upload/{project_id}', data=data, content_type='multipart/form-data', headers=auth_header)
    psm_ds_id = u_resp.get_json()['dataset_id']

    # Act
    resp = client.post('/api/statistics/psm', json={
        'dataset_id': psm_ds_id,
        'treatment': 'treat',
        'covariates': ['age'],
        'save': True
    }, headers=auth_header)
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'new_dataset_id' in data
    
    new_id = data['new_dataset_id']
    with app.app_context():
        new_ds = Dataset.query.get(new_id)
        assert new_ds.name.endswith('_matched.csv')
        assert new_ds.project_id == project_id
        # Verify metadata was generated
        assert 'variables' in new_ds.meta_data
        assert new_ds.meta_data['row_count'] > 0
