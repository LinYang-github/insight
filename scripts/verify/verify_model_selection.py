import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

import pandas as pd
import numpy as np
from app.services.model_selection_service import ModelSelectionService

def test_selection():
    # 生成模拟数据
    np.random.seed(42)
    n = 100
    # X1, X2 是真正相关的变量
    X1 = np.random.randn(n)
    X2 = np.random.randn(n)
    # X3, X4 是噪声
    X3 = np.random.randn(n)
    X4 = np.random.randn(n)
    
    # 连续结局 (Linear)
    y_linear = 2*X1 - 3*X2 + 0.5*np.random.randn(n)
    
    # 二分类结局 (Logistic)
    z = X1 - X2 + 0.1*np.random.randn(n)
    y_logistic = (z > 0).astype(int)
    
    df = pd.DataFrame({
        'X1': X1, 'X2': X2, 'X3': X3, 'X4': X4,
        'y_linear': y_linear,
        'y_logistic': y_logistic,
        'time': np.random.exponential(10, n),
        'event': np.random.randint(0, 2, n)
    })
    
    features = ['X1', 'X2', 'X3', 'X4']
    
    print("--- Testing Linear Stepwise ---")
    res = ModelSelectionService.run_stepwise_selection(df, 'y_linear', features, 'linear')
    print(f"Selected: {res['selected_features']}")
    
    print("\n--- Testing Linear LASSO ---")
    res = ModelSelectionService.run_lasso_selection(df, 'y_linear', features, 'linear')
    print(f"Selected: {res['selected_features']}")
    
    print("\n--- Testing Logistic Stepwise ---")
    res = ModelSelectionService.run_stepwise_selection(df, 'y_logistic', features, 'logistic')
    print(f"Selected: {res['selected_features']}")
    
    print("\n--- Testing Cox Stepwise ---")
    target_cox = {'time': 'time', 'event': 'event'}
    res = ModelSelectionService.run_stepwise_selection(df, target_cox, features, 'cox')
    print(f"Selected: {res['selected_features']}")

if __name__ == "__main__":
    # 需要 mock app context 吗？ModelSelectionService 是静态方法，不涉及 DB。
    try:
        test_selection()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")