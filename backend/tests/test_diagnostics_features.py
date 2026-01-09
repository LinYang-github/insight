
import pytest
import pandas as pd
import numpy as np
from app.services.modeling_service import ModelingService
from sklearn.datasets import make_classification, make_regression

@pytest.fixture
def linear_df():
    X, y = make_regression(n_samples=100, n_features=3, noise=0.1, random_state=42)
    df = pd.DataFrame(X, columns=['f0', 'f1', 'f2'])
    df['target'] = y
    return df

@pytest.fixture
def logistic_df():
    # Fix: n_informative + n_redundant + n_repeated < n_features
    # n_features=3. n_informative=2 (default), n_redundant=0.
    X, y = make_classification(n_samples=100, n_features=3, n_informative=2, n_redundant=0, random_state=42)
    df = pd.DataFrame(X, columns=['f0', 'f1', 'f2'])
    df['target'] = y
    return df

@pytest.fixture
def survival_df():
    df = pd.DataFrame({
        'time': np.random.randint(1, 100, 100),
        'event': np.random.randint(0, 2, 100),
        'age': np.random.normal(60, 10, 100),
        'treatment': np.random.randint(0, 2, 100)
    })
    return df

def test_linear_diagnostics_vif(linear_df):
    results = ModelingService.run_model(
        linear_df,
        'linear',
        'target',
        ['f0', 'f1', 'f2']
    )
    
    assert 'summary' in results
    # Check VIF presence in a feature row (skip constant)
    f0_row = next(r for r in results['summary'] if r['variable'] == 'f0')
    assert f0_row['vif'] != '-'
    # SInce data is independent, VIF should be low (~1)
    assert float(f0_row['vif']) < 5.0

def test_logistic_diagnostics_vif(logistic_df):
    results = ModelingService.run_model(
        logistic_df,
        'logistic',
        'target',
        ['f0', 'f1', 'f2']
    )
    
    assert 'summary' in results
    f0_row = next(r for r in results['summary'] if r['variable'] == 'f0')
    assert f0_row['vif'] != '-'

def test_cox_diagnostics_ph(survival_df):
    target_dict = {'time': 'time', 'event': 'event'}
    results = ModelingService.run_model(
        survival_df,
        'cox',
        target_dict,
        ['age', 'treatment']
    )
    
    assert 'summary' in results
    first_row = results['summary'][0]
    assert 'ph_test_p' in first_row
    # Check if it's a number or '-' (might be '-' if test failed or singular)
    # With random data it should succeed.
    val = first_row['ph_test_p']
    assert val != '-'
    # Check it parses as float
    assert float(val) >= 0.0
