import pytest
from app.services.modeling_service import ModelingService

def test_generate_interpretation_cox():
    summary = [
        {'variable': 'Age', 'p_value': 0.001, 'hr': 1.5},
        {'variable': 'Sex', 'p_value': 0.2, 'hr': 0.8}
    ]
    interp = ModelingService._generate_interpretation('cox', {'summary': summary})
    
    assert interp['level'] == 'danger'
    assert interp['params']['var'] == 'Age'
    assert interp['params']['hr'] == 1.5
    assert interp['params']['direction'] == '增加'

def test_generate_interpretation_logistic():
    summary = [
        {'variable': 'Treatment', 'p_value': 0.04, 'or': 0.5},
        {'variable': 'Age', 'p_value': 0.1, 'or': 1.1}
    ]
    interp = ModelingService._generate_interpretation('logistic', {'summary': summary})
    
    assert interp['level'] == 'success'
    assert interp['params']['var'] == 'Treatment'
    assert interp['params']['or_val'] == 0.5
    assert interp['params']['direction'] == '降低'

def test_generate_interpretation_none():
    summary = [
        {'variable': 'Age', 'p_value': 0.5, 'hr': 1.0}
    ]
    interp = ModelingService._generate_interpretation('cox', {'summary': summary})
    
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

def test_generate_interpretation_ml():
    # Helper to simulate results dict
    results = {
        'importance': [
            {'feature': 'Age', 'importance': 0.5},
            {'feature': 'BMI', 'importance': 0.3},
            {'feature': 'Sex', 'importance': 0.1}
        ]
    }
    
    # RF
    interp = ModelingService._generate_interpretation('random_forest', results)
    assert interp['level'] == 'info'
    assert "最重要的前 3 个特征" in interp['text_template']
    assert interp['params']['vars'] == "Age, BMI, Sex"
    
    # XGB
    interp = ModelingService._generate_interpretation('xgboost', results)
    assert interp['level'] == 'info'
    assert "最重要的前 3 个特征" in interp['text_template']

def test_generate_methodology_text():
    # 1. Cox
    params = {'ref_levels': {'Sex': 'Female'}}
    text = ModelingService._generate_methodology('cox', params)
    
    assert "Multivariate Cox proportional hazards regression analysis" in text
    assert "Hazard Ratios (HR)" in text
    assert "95% confidence intervals" in text
    assert "Insight Statistical Platform" in text
    assert "Reference groups for categorical variables were set as follows: Female for Sex" in text
    
    # 2. Logistic
    text = ModelingService._generate_methodology('logistic', {})
    assert "Multivariate logistic regression analysis" in text
    assert "Odds Ratios (OR)" in text
    
    # 3. Linear
    text = ModelingService._generate_methodology('linear', {})
    assert "Multivariate linear regression analysis" in text
    assert "Coefficients (Coef)" in text
    
    # 4. ML
    text = ModelingService._generate_methodology('random_forest', {})
    assert "Random Forest machine learning model" in text

