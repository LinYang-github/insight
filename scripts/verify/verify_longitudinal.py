
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

import sys
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
import importlib.util
import os

def load_service_module():
    # 1. Mock dependencies
    sys.modules['app'] = MagicMock()
    sys.modules['app.utils'] = MagicMock()
    sys.modules['app.utils.formatter'] = MagicMock()
    
    # 2. Load LongitudinalService from source
    file_path = os.path.join('backend', 'app', 'services', 'longitudinal_service.py')
    spec = importlib.util.spec_from_file_location("longitudinal_service_mod", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["longitudinal_service_mod"] = module
    spec.loader.exec_module(module)
    return module.LongitudinalService

def verify_lmm(Service):
    print("\n--- Verifying Linear Mixed Model (LMM) ---")
    np.random.seed(42)
    n_subjects = 50
    n_visits = 5
    
    ids = []
    times = []
    outcomes = []
    
    # True Params: Intercept=10, Time_Slope=2.0
    # Random Intercept ~ N(0, 1), Random Slope ~ N(0, 0.5)
    for i in range(n_subjects):
        r_int = np.random.randn() * 1.0
        r_slope = np.random.randn() * 0.5
        
        for t in range(n_visits):
            y = (10 + r_int) + (2.0 + r_slope) * t + np.random.randn() * 0.5
            ids.append(i)
            times.append(t)
            outcomes.append(y)
            
    df = pd.DataFrame({'id': ids, 'time': times, 'outcome': outcomes})
    
    try:
        res = Service.fit_lmm(df, 'id', 'time', 'outcome', fixed_effects=[])
        
        # Check Fixed Effects
        fe = {row['variable']: row['coef'] for row in res['summary']}
        print(f"Fixed Effects: Intercept={fe['Intercept']:.2f}, Time={fe['time']:.2f}")
        
        if 9.0 < fe['Intercept'] < 11.0 and 1.5 < fe['time'] < 2.5:
             print("[PASS] LMM Fixed Effects are accurate.")
        else:
             print("[WARN] LMM Fixed Effects might be off.")
             
        # Check Random Effects structure
        if len(res['random_effects']) == n_subjects:
            print("[PASS] Random Effects count matches subjects.")
        else:
            print("[FAIL] Random Effects count mismatch.")
            
    except Exception as e:
        print(f"[FAIL] LMM Fitting failed: {e}")
        import traceback
        traceback.print_exc()

def verify_clustering(Service):
    print("\n--- Verifying Trajectory Clustering ---")
    np.random.seed(42)
    # Cluster 1: Slope +2 (Increasing)
    # Cluster 2: Slope -2 (Decreasing)
    
    data = []
    # 20 subjects in Cluster 1
    for i in range(20):
        for t in range(5):
             y = 10 + 2*t + np.random.randn()*0.2
             data.append({'id': f"A_{i}", 'time': t, 'outcome': y})
             
    # 20 subjects in Cluster 2
    for i in range(20):
        for t in range(5):
             y = 20 - 2*t + np.random.randn()*0.2
             data.append({'id': f"B_{i}", 'time': t, 'outcome': y})
             
    df = pd.DataFrame(data)
    
    try:
        res = Service.cluster_trajectories(df, 'id', 'time', 'outcome', n_clusters=2)
        
        centroids = sorted(res['centroids'], key=lambda x: x['slope'])
        print("Centroids:", centroids)
         
        low_slope = centroids[0]['slope']
        high_slope = centroids[1]['slope']
         
        print(f"Cluster Slopes: {low_slope:.2f} vs {high_slope:.2f}")
         
        if low_slope < -1.5 and high_slope > 1.5:
              print("[PASS] Clustering successfully separated increasing and decreasing trends.")
        else:
              print("[FAIL] Clustering failed to separate trends.")
              
    except Exception as e:
        print(f"[FAIL] Clustering failed: {e}")

if __name__ == "__main__":
    try:
        Service = load_service_module()
        verify_lmm(Service)
        verify_clustering(Service)
    except Exception as e:
        print(f"Setup failed: {e}")
