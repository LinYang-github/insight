import pytest
import pandas as pd
import numpy as np
from app.services.modeling_service import ModelingService

class TestModelingServiceDiagnostics:
    def test_singular_matrix_diagnosis(self):
        """
        Verify that informative error message is raised for singular matrix.
        """
        # Create perfectly collinear data
        # x2 = 2 * x1
        df = pd.DataFrame({
            'y': np.random.normal(0, 1, 100),
            'x1': np.random.normal(0, 1, 100)
        })
        df['x2'] = df['x1'] * 2
        
        # Linear Regression
        try:
            ModelingService.run_model(df, 'linear', 'y', ['x1', 'x2'])
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            msg = str(e)
            print(f"\nCaught Message: {msg}")
            assert "模型计算失败" in msg
            assert "x1 & x2" in msg or "x2 & x1" in msg
            assert "r=1.00" in msg

    def test_constant_variable_interception(self):
        """
        Verify constant variable check (Integrity) still works first.
        """
        df = pd.DataFrame({
            'y': np.random.normal(0, 1, 100),
            'x1': [1] * 100, # Constant
            'x2': np.random.normal(0, 1, 100)
        })
        
        with pytest.raises(ValueError) as exc:
             ModelingService.run_model(df, 'linear', 'y', ['x1', 'x2'])
        
        assert "是常数" in str(exc.value)
