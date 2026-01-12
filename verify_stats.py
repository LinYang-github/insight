import pandas as pd
import numpy as np
from app.services.statistics_service import StatisticsService
from app.services.advanced_modeling_service import AdvancedModelingService
from app.services.preprocessing_service import PreprocessingService
from lifelines import CoxPHFitter

def verify_table_one():
    print("=== Verifying Table 1 Logic ===")
    
    # 1. Normal Distribution Data
    np.random.seed(42)
    n = 100
    df_normal = pd.DataFrame({
        'Group': np.random.choice(['A', 'B'], n),
        'Age': np.random.normal(60, 10, n), # Normal
        'Cost': np.random.lognormal(8, 1, n) # Non-Normal (Right Skewed)
    })
    
    # Test Normal Variable
    print("\n--- Testing Normal Variable (Age) ---")
    res_normal = StatisticsService.generate_table_one(df_normal, 'Group', ['Age'])
    row_normal = res_normal['table_data'][0]
    print(f"Variable: {row_normal['variable']}")
    print(f"Normality Detected: {row_normal['is_normal']}")
    print(f"Test Used: {row_normal['test']}")
    print(f"Desc Overall: {row_normal['overall']['desc']}")
    
    # Expect: is_normal=True, Welch's T-test, Mean ± SD
    if row_normal['is_normal'] and ("Welch" in row_normal['test'] or "Student" in row_normal['test']) and "±" in row_normal['overall']['desc']:
        print("✅ Normal Logic PASS")
    else:
        print("❌ Normal Logic FAIL")

    # Test Non-Normal Variable
    print("\n--- Testing Non-Normal Variable (Cost) ---")
    res_non_normal = StatisticsService.generate_table_one(df_normal, 'Group', ['Cost'])
    row_non = res_non_normal['table_data'][0]
    print(f"Variable: {row_non['variable']}")
    print(f"Normality Detected: {row_non['is_normal']}")
    print(f"Test Used: {row_non['test']}")
    print(f"Desc Overall: {row_non['overall']['desc']}")
    
    # Expect: is_normal=False, Mann-Whitney U, Median [IQR]
    if not row_non['is_normal'] and "Mann-Whitney" in row_non['test'] and "[" in row_non['overall']['desc']:
        print("✅ Non-Normal Logic PASS")
    else:
        print("❌ Non-Normal Logic FAIL")

def verify_cox_ph():
    print("\n=== Verifying Cox PH Assumption ===")
    
    n = 200
    df = pd.DataFrame({
        'T': np.random.exponential(10, n),
        'E': np.random.binomial(1, 0.7, n),
        'Var1': np.random.normal(0, 1, n)
    })
    
    # Fit
    cph = CoxPHFitter()
    cph.fit(df, 'T', 'E')
    
    # Check
    res = AdvancedModelingService.check_ph_assumption(cph, df)
    
    if res:
        print("✅ PH Test Executed")
        print(f"Is Violated: {res['is_violated']}")
        print(f"P Value: {res['p_value']}")
    else:
        print("❌ PH Test Failed to Execute")

def verify_mice():
    print("\n=== Verifying MICE Imputation ===")
    
    df = pd.DataFrame({
        'A': [1.0, 2.0, np.nan, 4.0, 5.0] * 20, # Numeric with missing
        'B': [10, 20, 30, 40, 50] * 20,         # Numeric complete (predictor)
        'C': ['X', 'Y', 'X', 'Y', 'X'] * 20     # Categorical (should be ignored by MICE logic or skipped)
    })
    
    strategies = {'A': 'mice'}
    
    try:
        df_imputed = PreprocessingService.impute_data(df, strategies)
        missing_after = df_imputed['A'].isnull().sum()
        print(f"Missing Before: {df['A'].isnull().sum()}")
        print(f"Missing After: {missing_after}")
        
        if missing_after == 0:
             print("✅ MICE Imputation PASS")
        else:
             print("❌ MICE Imputation FAIL (Still missing)")
    except Exception as e:
        print(f"❌ MICE Crashed: {e}")

def verify_psm_caliper():
    print("\n=== Verifying PSM Caliper ===")
    
    # Create distinct groups
    # Group 1: High scores
    # Group 0: Low scores
    # Caliper should prevent matching distinct ones.
    
    n = 100
    df = pd.DataFrame({
        'Treat': [1]*50 + [0]*50,
        'Score': np.concatenate([np.random.normal(10, 1, 50), np.random.normal(0, 1, 50)])
    })
    
    # Strict Caliper
    print("Testing Strict Caliper (Should fail or return few)...")
    try:
        # Caliper 0.1 on Logit scale? No, distance is absolute difference in PS (0-1).
        # PS will be very different.
        res = StatisticsService.perform_psm(df, 'Treat', ['Score'], caliper=0.01)
        print(f"Matched Pairs: {res['n_matched_pairs']}")
    except ValueError as e:
        print(f"✅ Strict Caliper Correctly Raised Error/Empty: {e}")
    except Exception as e:
        print(f"❌ Strict Caliper Crashed: {e}")
        
    # Loose Caliper
    print("Testing Loose Caliper...")
    try:
        # Create overlapping
        df2 = pd.DataFrame({
            'Treat': np.random.binomial(1, 0.5, 200),
            'Cov': np.random.normal(0, 1, 200)
        })
        res = StatisticsService.perform_psm(df2, 'Treat', ['Cov'], caliper=0.2)
        print(f"Matched (Loose): {res['n_matched_pairs']}")
        print("✅ Loose Caliper PASS")
    except Exception as e:
         print(f"❌ Loose Caliper Crashed: {e}")

if __name__ == '__main__':
    try:
        verify_table_one()
        verify_cox_ph()
        verify_mice()
        verify_psm_caliper()
    except Exception as e:
        print(f"Verification Crashed: {e}")
        import traceback
        traceback.print_exc()
