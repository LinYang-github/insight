
import pytest
import pandas as pd
import numpy as np
from app.services.modeling_service import ModelingService
from sklearn.datasets import make_classification

@pytest.fixture
def classification_df():
    X, y = make_classification(n_samples=100, n_features=5, random_state=42)
    df = pd.DataFrame(X, columns=[f'f{i}' for i in range(5)])
    df['target'] = y
    return df

def test_logistic_plots(classification_df):
    results = ModelingService.run_model(
        classification_df, 
        'logistic', 
        'target', 
        ['f0', 'f1', 'f2']
    )
    
    assert 'plots' in results
    plots = results['plots']
    assert 'roc' in plots
    assert 'calibration' in plots
    
    # Check ROC structure
    roc = plots['roc']
    assert len(roc['fpr']) == len(roc['tpr'])
    assert 'auc' in roc
    
    # Check AUC value (should be reasonable for make_classification, > 0.5)
    assert float(results['metrics']['auc']) > 0.5
    
    # Check CV Metrics
    assert 'cv_auc_mean' in results['metrics']
    assert 'cv_auc_std' in results['metrics']
    
    # Check Calibration
    cal = plots['calibration']
    assert len(cal['prob_true']) == len(cal['prob_pred'])

    # Check DCA
    assert 'dca' in plots
    dca = plots['dca']
    assert len(dca['thresholds']) == 99
    assert len(dca['net_benefit_model']) == 99
    assert len(dca['net_benefit_all']) == 99

def test_rf_plots(classification_df):
    results = ModelingService.run_model(
        classification_df, 
        'random_forest', 
        'target', 
        ['f0', 'f1']
    )
    
    assert 'plots' in results
    assert 'roc' in results['plots']
    assert 'calibration' in results['plots']
    assert 'cv_auc_mean' in results['metrics']
