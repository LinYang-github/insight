
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

import sys
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
import importlib.util
import os

# Mock App Dependencies
sys.modules['app'] = MagicMock()
sys.modules['app.services.data_service'] = MagicMock()
# Mock DataService.preprocess_for_formula to just return df
sys.modules['app.services.data_service'].DataService.preprocess_for_formula = lambda df: df

# Load Service
file_path = os.path.join('backend', 'app', 'services', 'advanced_modeling_service.py')
spec = importlib.util.spec_from_file_location("advanced_modeling_service_mod", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["advanced_modeling_service_mod"] = module
spec.loader.exec_module(module)
AdvancedModelingService = module.AdvancedModelingService

def verify_subgroup_analysis():
    print("\n--- Verifying Subgroup Analysis ---")
    np.random.seed(42)
    n = 200
    
    # Data Generation
    # Subgroup: Gender (Male/Female)
    # Exposure: Age (Continuous) -> Hazard Ratio = 1.05
    # Exposure: Treatment (Binary) -> HR = 0.5
    
    gender = np.random.choice(['Male', 'Female'], n)
    age = np.random.normal(60, 10, n)
    treatment = np.random.choice([0, 1], n) # 0=Placebo, 1=Drug
    
    # Survival Time
    # Base hazard
    # h(t) = h0 * exp(beta*X)
    # Let's verify continuous exposure (Age) first.
    # Effect of Age: 0.05
    # Effect of Gender: 0.2
    # Interaction Age*Gender? Let's assume none first.
    
    lp = 0.05 * age + 0.5 * (gender == 'Male')
    # Outcome
    time = np.random.exponential(100, n) / np.exp(lp)
    event = np.random.choice([0, 1], n, p=[0.2, 0.8])
    
    df = pd.DataFrame({
        'time': time, 'event': event, 
        'Age': age, 'Gender': gender, 
        'Treatment': treatment
    })
    
    print("1. Testing Continuous Exposure (Age)...")
    try:
        res = AdvancedModelingService.perform_subgroup(
            df, 'time', 'event', 'Age', ['Gender'], [], model_type='cox'
        )
        # Check first group
        g1 = res['forest_data'][0]
        print(f"Subgroup Variable: {g1['variable']}")
        for sub in g1['subgroups']:
             print(f"  Level: {sub['level']}, N={sub['n']}, HR={sub.get('est', 'N/A')}")
             
        if g1['subgroups'][0]['est'] is not None:
            print("[PASS] Continuous Exposure works.")
        else:
            print("[FAIL] Continuous Exposure HR not extracted.")
            
    except Exception as e:
        print(f"[FAIL] Continuous Exposure Test Failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n2. Testing Categorical Exposure (Treatment)...")
    try:
        res = AdvancedModelingService.perform_subgroup(
            df, 'time', 'event', 'Treatment', ['Gender'], [], model_type='cox'
        )
        g1 = res['forest_data'][0]
        # Treatment is 0/1. In Cox, coeff is for Treatment.
        # If passed as "Treatment", statsmodels treats as continuous or categorical depending on type.
        # If it's int, likely continuous.
        # What if it's "Drug A" / "Drug B"?
        
        df['TreatmentStr'] = df['Treatment'].map({0: 'Placebo', 1: 'Drug'})
        
        res_cat = AdvancedModelingService.perform_subgroup(
            df, 'time', 'event', 'TreatmentStr', ['Gender'], [], model_type='cox'
        )
        g2 = res_cat['forest_data'][0]
        print(f"Subgroup Variable: {g2['variable']}")
        for sub in g2['subgroups']:
             print(f"  Level: {sub['level']}, HR={sub.get('est', 'N/A')}")
             
        if g2['subgroups'][0]['est'] is not None:
             print("[PASS] Categorical Exposure works.")
        else:
             print("[FAIL] Categorical Exposure HR not extracted (likely due to One-Hot naming mismatch).")

    except Exception as e:
        print(f"[FAIL] Categorical Exposure Test Failed: {e}")

if __name__ == "__main__":
    verify_subgroup_analysis()