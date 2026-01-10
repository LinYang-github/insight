
import pytest
import pandas as pd
import numpy as np
from app.services.statistics_service import StatisticsService

def test_recommend_cox():
    df = pd.DataFrame({
        'Time': [10, 20, 30, 40],
        'Status': [1, 0, 1, 0],
        'Age': [50, 60, 70, 80],
        'ID': ['A1', 'A2', 'A3', 'A4']
    })
    rec = StatisticsService.recommend_modeling_strategy(df)
    
    assert rec['model_type'] == 'cox'
    assert rec['target']['time'] == 'Time'
    assert rec['target']['event'] == 'Status'
    assert 'Age' in rec['features']
    assert 'ID' not in rec['features']

def test_recommend_logistic():
    df = pd.DataFrame({
        'Outcome': [1, 0, 1, 0],
        'BMI': [22.5, 30.1, 25.0, 28.3],
        'Gender': ['M', 'F', 'M', 'F']
    })
    rec = StatisticsService.recommend_modeling_strategy(df)
    
    assert rec['model_type'] == 'logistic'
    assert rec['target'] == 'Outcome'
    assert 'BMI' in rec['features']
    assert 'Gender' in rec['features']

def test_recommend_linear():
    df = pd.DataFrame({
        'SBP': [120, 130, 140, 110], # Continuous
        'Age': [50, 60, 70, 40],
        'Treatment': [0, 1, 0, 1]
    })
    # SBP is target? Only if it matches keyword? 
    # Current keywords: 'outcome', 'target', 'y'. 'SBP' is not a keyword.
    # Logic in service: searches for keywords first.
    # So let's rename SBP to 'Outcome_Value'
    df = df.rename(columns={'SBP': 'Outcome_Value'})
    
    rec = StatisticsService.recommend_modeling_strategy(df)
    
    # Depending on order of checks. Time check first (fails), then Event/Target check.
    # Outcome_Value has 4 unique values -> >2 -> Continuous check.
    
    assert rec['model_type'] == 'linear'
    assert rec['target'] == 'Outcome_Value'

def test_recommend_fallback():
    df = pd.DataFrame({
        'VarA': [1, 2, 3],
        'VarB': [4, 5, 6]
    })
    # No keywords
    rec = StatisticsService.recommend_modeling_strategy(df)
    
    # Reason fallback logic -> Logistic default usually
    # But reason should say "failed to identify"
    assert "未能自动识别" in rec['reason']
