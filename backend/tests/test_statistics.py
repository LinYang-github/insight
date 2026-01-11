
import pytest
import pandas as pd
import numpy as np
import io
import os
from app import create_app, db
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset
from app.services.statistics_service import StatisticsService

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
    # Register and login
    client.post('/api/auth/register', json={'username': 'test', 'email': 'test@example.com', 'password': 'password'})
    resp = client.post('/api/auth/login', json={'username': 'test', 'password': 'password'})
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def sample_dataset(app, auth_header, client):
    # Create project
    p_resp = client.post('/api/projects/', json={'name': 'Stats Project', 'description': 'desc'}, headers=auth_header)
    project_id = p_resp.get_json()['id']
    
    # Create dummy csv
    df = pd.DataFrame({
        'age': [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
        'group': ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'],
        'gender': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F', 'M', 'F']
    })
    
    # Mock file save
    # Actually let's use the real API flow but we need to mock file upload? 
    # Or just insert into DB and manually save file.
    
    filename = 'test_stats_data.csv'
    filepath = os.path.join(app.root_path, '../data', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    
    dataset = Dataset(name=filename, filepath=filepath, project_id=project_id)
    db.session.add(dataset)
    db.session.commit()
    
    return dataset

def test_table1_generation_logic():
    df = pd.DataFrame({
        'age': [20, 22, 19, 21, 60, 62, 59, 61],
        'group': ['Young', 'Young', 'Young', 'Young', 'Old', 'Old', 'Old', 'Old'],
        'sex': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F']
    })
    
    # Test Numeric T-test (Should be significant)
    res = StatisticsService.generate_table_one(df, 'group', ['age'])['table_data']
    age_row = res[0]
    assert age_row['variable'] == 'age'
    assert 'Young' in age_row['groups']
    assert 'Old' in age_row['groups']
    p_val_str = age_row['p_value']
    if p_val_str == '<0.001':
        assert True
    else:
        assert float(p_val_str) < 0.05
    # Updated to Welch's due to recent Phase 2 change
    assert age_row['test'] == "Welch's T-test" 

    # Test Categorical (Chi-square) - Should be non-significant (perfectly balanced)
    res_dict = StatisticsService.generate_table_one(df, 'group', ['sex'])
    res = res_dict['table_data']
    sex_row = res[0]
    assert sex_row['variable'] == 'sex'
    # p-value might be 1.0
    assert sex_row['p_value'] != 'N/A'
    # With small sample (N=10) and expected < 5, code now switches to Fisher
    assert sex_row['test'] == 'Fisher Exact Test'

def test_table1_api_endpoint(client, auth_header, sample_dataset):
    ds_id = sample_dataset.id
    
    data = {
        'dataset_id': ds_id,
        'group_by': 'group',
        'variables': ['age', 'gender']
    }
    
    resp = client.post('/api/statistics/table1', json=data, headers=auth_header)
    assert resp.status_code == 200
    json_data = resp.get_json()['table1']
    
    assert len(json_data) == 2
    age_row = next(r for r in json_data if r['variable'] == 'age')
    assert age_row['p_value'] != 'N/A'

def test_km_plot(client, auth_header, sample_dataset):
    df = pd.DataFrame({
        'time': [10, 20, 30, 40, 50, 60],
        'event': [1, 1, 0, 1, 0, 1]
    })
    
    # Service Test
    res = StatisticsService.generate_km_data(df, 'time', 'event')
    assert 'plot_data' in res
    assert len(res['plot_data']) == 1
    assert res['plot_data'][0]['name'] == 'Overall'
    
    # Test with Group
    df['group'] = ['A', 'A', 'A', 'B', 'B', 'B']
    res = StatisticsService.generate_km_data(df, 'time', 'event', 'group')
    assert len(res['plot_data']) == 2 # A and B
    assert res['p_value'] != 'N/A'

def test_psm(client, auth_header, sample_dataset):
    # Create simple dataset where treated has different age dist
    df = pd.DataFrame({
        'treatment': [1]*10 + [0]*20,
        'age': [50]*10 + [30]*10 + [50]*10
    })
    # Treated (1): all 50. Control (0): half 30, half 50.
    # PSM should pick the control subjects with age 50.
    
    # Save this file to system to be loaded by service
    # We must overwrite the sample_dataset file or create new one.
    # To keep simple, let's just test service logic directly with DF, 
    # but also test API flow with dummy covariates.
    
    # Service Logic Test
    res = StatisticsService.perform_psm(df, 'treatment', ['age'])
    
    assert res['n_treated'] == 10
    assert res['n_matched'] == 20 # 1:1 match -> 10 + 10
    
    # Check balance
    # Before: Treated mean=50, Control mean=40. SMD > 0.
    # After: Treated mean=50, Control matched mean=50. SMD=0.
    

    balance = res['balance'][0]
    assert balance['variable'] == 'age'
    assert balance['smd_pre'] > 0
    assert balance['smd_post'] < balance['smd_pre']
    assert balance['smd_post'] < 0.1 # Should be perfect 0 actually

def test_fisher_exact_small_sample():
    # Construct small sample size where Chi-square would be invalid (Expected < 5)
    # Group A: 3 Yes, 0 No
    # Group B: 1 Yes, 4 No
    # Total N = 8.
    df = pd.DataFrame({
        'group': ['A']*3 + ['B']*5,
        'outcome': ['Yes']*3 + ['Yes', 'No', 'No', 'No', 'No']
    })
    
    res = StatisticsService.generate_table_one(df, 'group', ['outcome'])['table_data']
    row = res[0]
    
    # Should automatically choose Fisher Exact
    assert row['variable'] == 'outcome'
    assert row['test'] == 'Fisher Exact Test'
    
def test_km_monotonicity_and_logrank():
    # 1. Monotonicity
    # Create simple data with events
    df = pd.DataFrame({
        'time': [1, 2, 3, 4, 5],
        'event': [0, 1, 0, 1, 0]
    })
    res = StatisticsService.generate_km_data(df, 'time', 'event')
    plot_data = res['plot_data'][0]
    probs = plot_data['probs']
    
    # Verify probability never increases (monotonic non-increasing)
    for i in range(len(probs)-1):
        assert probs[i] >= probs[i+1], f"KM probability increased at index {i}"
        
    assert min(probs) >= 0
    assert max(probs) <= 1
    
    # 2. Log-rank Significance
    # Group A: Die early (t=1, 2)
    # Group B: Die late (t=100, 101)
    df_sig = pd.DataFrame({
        'time':   [1, 1, 2, 2, 100, 100, 101, 101],
        'event':  [1, 1, 1, 1, 1,   1,   1,   1],
        'group':  ['A']*4 + ['B']*4
    })
    
    res_sig = StatisticsService.generate_km_data(df_sig, 'time', 'event', 'group')
    
    p_val_str = res_sig['p_value']
    # Parsable float?
    assert p_val_str != 'N/A'
    p_val = float(p_val_str.replace('<', '')) # Handle <0.001
    
    # Should be significant
    assert p_val < 0.05



    
def test_metadata_injection():
    """
    Verify that the result contains _meta with decision logic.
    """
    # 1. Welch T-test Case (Unequal Variance)
    # Group A: small variance (all 10)
    # Group B: huge variance (0, 100)
    df = pd.DataFrame({
        'val': [10, 10, 10, 10, 10, 0, 100, 0, 100, 50],
        'group': ['A']*5 + ['B']*5
    })
    
    res = StatisticsService.generate_table_one(df, 'group', ['val'])['table_data']
    row = res[0]
    
    assert '_meta' in row
    assert row['_meta']['test_name'] == "Welch's T-test"
    # Updated reason string
    assert "采用 Welch's T-test" in row['_meta']['selection_reason']
    
    # 2. ANOVA Case (>2 groups)
    df2 = pd.DataFrame({
        'val': [1, 2, 3, 1, 2, 3, 1, 2, 3],
        'group': ['A']*3 + ['B']*3 + ['C']*3
    })
    res2 = StatisticsService.generate_table_one(df2, 'group', ['val'])['table_data']
    row2 = res2[0]
    
    assert row2['test'] == 'ANOVA'
    assert row2['_meta']['test_name'] == 'ANOVA'
    assert "多组比较" in row2['_meta']['selection_reason']
