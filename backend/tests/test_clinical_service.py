import pytest
import pandas as pd
import numpy as np
from app.services.preprocessing_service import PreprocessingService

class TestClinicalService:
    """
    Tests for Phase 26 Clinical features: eGFR, Staging, Slope.
    Implemented in PreprocessingService.
    """
    
    def test_derive_egfr_ckdepi2021(self):
        # Case: Female, Age 50, Scr 1.0 mg/dL
        # k=0.7, a=-0.241, sex_factor=1.012
        # eGFR = 142 * min(1/0.7, 1)^-0.241 * max(1/0.7, 1)^-1.2 * 0.9938^50 * 1.012
        # scratch calc:
        # min(1.428, 1) = 1
        # max(1.428, 1) = 1.428
        # 142 * 1 * (1.428^-1.2) * (0.9938^50) * 1.012
        # 1.428^-1.2 = 0.654
        # 0.9938^50 = 0.733
        # 142 * 0.654 * 0.733 * 1.012 approx 68.8
        
        df = pd.DataFrame({
            'Scr': [1.0, 0.7, 2.0],
            'Age': [50, 40, 60],
            'Sex': ['F', 'M', 'Female']
        })
        
        params = {'scr': 'Scr', 'age': 'Age', 'sex': 'Sex'}
        res = PreprocessingService.derive_variable(df, 'egfr_ckdepi2021', params)
        
        assert 'eGFR_CKDEPI_2021' in res.columns
        vals = res['eGFR_CKDEPI_2021']
        assert not vals.isnull().any()
        
        # approximate check
        # Row 0: ~69
        assert 60 < vals[0] < 80 
        
    def test_derive_ckd_staging(self):
        df = pd.DataFrame({
            'eGFR': [100, 50, 10],   # G1, G3a, G5
            'ACR':  [10, 100, 500]   # A1, A2, A3
        })
        
        params = {'egfr': 'eGFR', 'acr': 'ACR'}
        res = PreprocessingService.derive_ckd_staging(df, params)
        
        assert 'CKD_G_Stage' in res.columns
        assert 'CKD_A_Stage' in res.columns
        assert 'CKD_Risk_Level' in res.columns
        
        # Row 0: G1, A1 -> Low Risk
        assert res.iloc[0]['CKD_G_Stage'] == 'G1'
        assert res.iloc[0]['CKD_A_Stage'] == 'A1'
        assert res.iloc[0]['CKD_Risk_Level'] == 'Low Risk'
        
        # Row 2: G5, A3 -> Very High Risk
        assert res.iloc[2]['CKD_G_Stage'] == 'G5' 
        assert res.iloc[2]['CKD_Risk_Level'] == 'Very High Risk'

    def test_calculate_slope(self):
        # Patient A: (0, 10), (1, 12), (2, 14) -> Slope = 2
        # Patient B: (0, 100) -> NaN (only 1 point)
        df = pd.DataFrame({
            'ID': ['A', 'A', 'A', 'B'],
            'Time': [0, 1, 2, 0],
            'Value': [10, 12, 14, 100]
        })
        
        res = PreprocessingService.calculate_slope(df, 'ID', 'Time', 'Value')
        
        assert len(res) == 2 # A and B
        
        row_a = res[res['ID'] == 'A'].iloc[0]
        assert abs(row_a['Slope'] - 2.0) < 0.001
        assert row_a['N_Points'] == 3
        
        row_b = res[res['ID'] == 'B'].iloc[0]
        assert pd.isna(row_b['Slope'])
        assert row_b['N_Points'] == 1

    def test_melt_to_long(self):
        df = pd.DataFrame({
            'ID': [1, 2],
            'T0': [10, 20],
            'T1': [11, 21]
        })
        
        # Map: T0->0, T1->12
        mapping = {'T0': 0, 'T1': 12}
        
        res = PreprocessingService.melt_to_long(df, 'ID', mapping, 'eGFR')
        
        assert len(res) == 4
        assert 'Time' in res.columns
        assert 'eGFR' in res.columns
        
        # Check ID 1
        sub = res[res['ID'] == 1]
        assert len(sub) == 2
        assert 10 in sub['eGFR'].values

    def test_egfr_2009_race_factor(self):
        """
        Verify that 2009 formula correctly applies race factor (1.159 for Black/African American).
        Formula: 141 * min(Scr/k, 1)^a * max(Scr/k, 1)^-1.209 * 0.993^Age * 1.018 [if Female] * 1.159 [if Black]
        """
        # Case: Black Male, Age 50, Scr 1.0
        # k=0.9, a=-0.411, Sex=1, Black=1.159
        # min(1.11, 1) = 1
        # max(1.11, 1) = 1.11
        # 141 * (1.11^-1.209) * (0.993^50) * 1.159
        # 1.11^-1.209 = 0.881
        # 0.993^50 = 0.704
        # 141 * 0.881 * 0.704 * 1.159 approx 101.3
        
        df = pd.DataFrame({
            'Scr': [1.0],
            'Age': [50],
            'Sex': ['M'],
            'Race': ['Black']
        })
        
        params = {'scr': 'Scr', 'age': 'Age', 'sex': 'Sex', 'race': 'Race'}
        # Note: derive_variable implementation for 2009 needs to support 'race' parameter mapping
        # Assuming implementation supports it or we check default behavior if not
        
        # Check if 'egfr_ckdepi' (default usually 2009 or specified) supports race.
        # Let's assume 'egfr_ckdepi' is 2009.
        res = PreprocessingService.derive_variable(df, 'egfr_ckdepi2009', params)
        
        assert 'eGFR_CKDEPI_2009' in res.columns
        val = res.iloc[0]['eGFR_CKDEPI_2009']
        
        # If logic correct, ~101. If race ignored, ~87.
        # This test ensures race is processed if passed.
        # If the current implementation doesn't support Race, this test might fail or need adjustment.
        # Based on task requirement, we are VERIFYING it.
        # If it fails, we know we need to fix implementation.
        assert val > 95 # Expect > 95 if factor applied

