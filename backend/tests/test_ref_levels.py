import pytest
import pandas as pd
import numpy as np
from app.services.data_service import DataService

def test_preprocess_for_matrix_ref_levels():
    """
    Test that preprocess_for_matrix respects ref_levels.
    """
    # Create dataset: 100 rows
    # Sex: Male, Female. 
    # By default (alphabetical), Female is first -> Reference. Male is kept.
    # We want to force 'Male' as reference.
    df = pd.DataFrame({
        'Sex': ['Male', 'Female'] * 50,
        'Y': np.random.randn(100)
    })
    
    features = ['Sex']
    
    # 1. Default Behavior (Alphabetical Ref)
    # Female < Male -> Female is ref. Column should be Sex_Male.
    df_enc_1, feats_1 = DataService.preprocess_for_matrix(df, features)
    assert 'Sex_Male' in df_enc_1.columns
    assert 'Sex_Female' not in df_enc_1.columns
    assert 'Sex_Male' in feats_1
    
    # 2. Custom Ref Behavior (Male as Ref)
    # Ref=Male -> Male is dropped. Column should be Sex_Female.
    ref_levels = {'Sex': 'Male'}
    df_enc_2, feats_2 = DataService.preprocess_for_matrix(df, features, ref_levels=ref_levels)
    assert 'Sex_Female' in df_enc_2.columns
    assert 'Sex_Male' not in df_enc_2.columns
    assert 'Sex_Female' in feats_2

def test_preprocess_ignores_invalid_ref():
    """
    If ref_level is not in categories, it should be ignored (fallback to default).
    """
    df = pd.DataFrame({
        'Sex': ['Male', 'Female'] * 50
    })
    features = ['Sex']
    ref_levels = {'Sex': 'Alien'}
    
    df_enc, feats = DataService.preprocess_for_matrix(df, features, ref_levels=ref_levels)
    # Should fall back to alphabetical (Female ref, Sex_Male kept)
    assert 'Sex_Male' in df_enc.columns

def test_preprocess_numeric_as_categorical_ref():
    """
    Test treating integer column as categorical via ref_levels.
    Grade: 1, 2, 3.
    """
    df = pd.DataFrame({
        'Grade': [1, 2, 3] * 10
    })
    features = ['Grade']
    
    # If we pass ref_levels for 'Grade', it should be treated as categorical.
    # Let Ref=2.
    # Dummies: Grade_1, Grade_3. (2 dropped)
    ref_levels = {'Grade': 2}
    
    df_enc, feats = DataService.preprocess_for_matrix(df, features, ref_levels=ref_levels)
    
    assert 'Grade_1' in df_enc.columns
    assert 'Grade_3' in df_enc.columns
    assert 'Grade_2' not in df_enc.columns
    # Check simple one row
    # Row with Grade=2 -> Grade_1=0, Grade_3=0
    row_grade_2 = df_enc.iloc[1] # [1, 2, 3, 1, 2... @ index 1 is 2
    assert row_grade_2['Grade_1'] == 0
    assert row_grade_2['Grade_3'] == 0
