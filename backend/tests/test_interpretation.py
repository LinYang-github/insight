import pytest
from app.services.modeling_service import ModelingService

def test_generate_interpretation_cox():
    summary = [
        {'variable': 'Age', 'p_value': 0.001, 'hr': 1.5},
        {'variable': 'Sex', 'p_value': 0.2, 'hr': 0.8}
    ]
    interp = ModelingService._generate_interpretation('cox', summary)
    
    assert interp['level'] == 'danger'
    assert interp['params']['var'] == 'Age'
    assert interp['params']['hr'] == 1.5
    assert interp['params']['direction'] == '增加'

def test_generate_interpretation_logistic():
    summary = [
        {'variable': 'Treatment', 'p_value': 0.04, 'or': 0.5},
        {'variable': 'Age', 'p_value': 0.1, 'or': 1.1}
    ]
    interp = ModelingService._generate_interpretation('logistic', summary)
    
    assert interp['level'] == 'success'
    assert interp['params']['var'] == 'Treatment'
    assert interp['params']['or_val'] == 0.5
    assert interp['params']['direction'] == '降低'

def test_generate_interpretation_none():
    summary = [
        {'variable': 'Age', 'p_value': 0.5, 'hr': 1.0}
    ]
    interp = ModelingService._generate_interpretation('cox', summary)
    
    assert interp['level'] == 'info'
    assert "未发现" in interp['text_template']

def test_generate_table1_interpretation():
    from app.services.statistics_service import StatisticsService
    
    # Sig
    interp = StatisticsService._generate_table1_interpretation('Age', 0.01, 'T-test')
    assert interp['level'] == 'danger'
    assert '分布差异显著' in interp['text_template']
    
    # Non-sig
    interp = StatisticsService._generate_table1_interpretation('Sex', 0.5, 'Chi2')
    assert interp['level'] == 'success'
    assert '分布均衡' in interp['text_template']

def test_generate_km_interpretation():
    from app.services.statistics_service import StatisticsService
    
    # Sig
    interp = StatisticsService._generate_km_interpretation(0.001)
    assert interp['level'] == 'danger'
    assert '显著差异' in interp['text_template']
    
    # Non-sig
    interp = StatisticsService._generate_km_interpretation(0.25)
    assert interp['level'] == 'info'
    assert '无显著差异' in interp['text_template']
