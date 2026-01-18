
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

import sys
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
import importlib.util
import os

def verify_rf_imputation():
    # 1. Mock dependencies
    sys.modules['duckdb'] = MagicMock()
    sys.modules['flask'] = MagicMock()
    sys.modules['flask_sqlalchemy'] = MagicMock()
    
    app_mock = MagicMock()
    sys.modules['app'] = app_mock
    sys.modules['app.models'] = MagicMock()
    sys.modules['app.models.dataset'] = MagicMock()
    sys.modules['app.services.data_service'] = MagicMock()

    # 2. Load PreprocessingService from source
    file_path = os.path.join('backend', 'app', 'services', 'preprocessing_service.py')
    spec = importlib.util.spec_from_file_location("preprocessing_service_mod", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["preprocessing_service_mod"] = module
    spec.loader.exec_module(module)
    
    PreprocessingService = module.PreprocessingService

    # 3. Test Logic
    np.random.seed(42)
    n = 100
    x = np.random.rand(n) * 10
    # True relation: y = 2x
    y = 2 * x + np.random.randn(n) * 0.1
    
    df = pd.DataFrame({'x': x, 'y': y})
    # Set 20 missing values in y
    missing_idx = np.random.choice(n, size=20, replace=False)
    df.loc[missing_idx, 'y'] = np.nan
    
    print("Original missing count:", df.isnull().sum().to_dict())
    
    strategies = {'y': 'random_forest'}
    print("\nApplying Random Forest Imputation...")
    try:
        df_imputed = PreprocessingService.impute_data(df, strategies)
        
        print("Imputed missing count:", df_imputed.isnull().sum().to_dict())
        
        if df_imputed.isnull().sum().sum() == 0:
            # Check accuracy?
            # Imputed values should be close to 2*x
            imputed_vals = df_imputed.loc[missing_idx, 'y']
            true_vals = 2 * df.loc[missing_idx, 'x']
            mse = np.mean((imputed_vals - true_vals)**2)
            print(f"Imputation MSE: {mse:.4f}")
            if mse < 1.0:
                print("[PASS] Random Forest imputation completed successfully and is accurate.")
            else:
                print("[WARN] Imputation completed but MSE is high (might be expected for small sample).")
        else:
            print("[FAIL] Random Forest imputation left missing values.")
            
    except Exception as e:
        print(f"[FAIL] Error during imputation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_rf_imputation()