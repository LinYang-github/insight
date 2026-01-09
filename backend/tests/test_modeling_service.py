import pytest
import pandas as pd
import numpy as np
from app.services.modeling_service import ModelingService

class TestModelingService:
    @pytest.fixture
    def regression_df(self):
        np.random.seed(42)
        X = np.random.rand(100, 3)
        y = 2 * X[:, 0] + 0.5 * X[:, 1] + 3 + 0.1 * np.random.randn(100) # y = 2x1 + 0.5x2 + 3 + noise
        df = pd.DataFrame(X, columns=['f1', 'f2', 'f3'])
        df['target'] = y
        return df

    @pytest.fixture
    def classification_df(self):
        np.random.seed(42)
        X = np.random.rand(100, 2)
        # Class 1 if x1 + x2 > 1
        y = (X[:, 0] + X[:, 1] > 1).astype(int)
        df = pd.DataFrame(X, columns=['f1', 'f2'])
        df['target'] = y
        return df

    @pytest.fixture
    def survival_df(self):
        df = pd.DataFrame({
            'T': [5, 10, 15, 20, 25],
            'E': [1, 1, 0, 1, 0],
            'age': [50, 60, 45, 70, 55],
            'marker': [1.2, 3.4, 0.9, 4.1, 2.3]
        })
        return df

    def test_run_linear_regression(self, regression_df):
        res = ModelingService.run_model(
            regression_df, 'linear', 'target', ['f1', 'f2', 'f3']
        )
        assert 'metrics' in res
        assert 'summary' in res
        # Check coefficients mostly
        # Intercept should be approx 3, f1 approx 2
        summary_map = {row['variable']: row['coef'] for row in res['summary']}
        assert abs(summary_map['截距 (Constant)'] - 3.0) < 0.2
        assert abs(summary_map['f1'] - 2.0) < 0.2
        assert 'rsquared' in res['metrics']

    def test_run_logistic_regression(self, classification_df):
        res = ModelingService.run_model(
            classification_df, 'logistic', 'target', ['f1', 'f2']
        )
        assert 'summary' in res
        # Should contain OR
        assert 'or' in res['summary'][0]
        assert 'prsquared' in res['metrics']

    def test_run_cox_ph(self, survival_df):
        res = ModelingService.run_model(
            survival_df, 'cox', {'time': 'T', 'event': 'E'}, ['age', 'marker']
        )
        assert 'summary' in res
        # Should contain HR
        assert 'hr' in res['summary'][0]
        assert 'c_index' in res['metrics']

    def test_run_random_forest_regression(self, regression_df):
        res = ModelingService.run_model(
            regression_df, 'random_forest', 'target', ['f1', 'f2']
        )
        assert res['task'] == 'regression'
        assert 'metrics' in res
        assert 'r2' in res['metrics']
        assert 'importance' in res
        
        # f1 (coeff 2) should be more important than f2 (coeff 0.5)
        imp_map = {row['feature']: row['importance'] for row in res['importance']}
        assert imp_map['f1'] > imp_map['f2']

    def test_run_xgboost_classification(self, classification_df):
        res = ModelingService.run_model(
            classification_df, 'xgboost', 'target', ['f1', 'f2']
        )
        assert res['task'] == 'classification'
        assert 'metrics' in res
        assert 'auc' in res['metrics']
        assert 'plots' in res
        assert 'roc' in res['plots']
        assert 'confusion_matrix' in res['metrics']
