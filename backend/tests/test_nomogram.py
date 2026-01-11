import pytest
import pandas as pd
import numpy as np
from app.utils.nomogram_generator import NomogramGenerator

class MockCoxModel:
    def __init__(self, params_dict, baseline_surv_df):
        self.params_ = pd.Series(params_dict)
        self.baseline_survival_ = baseline_surv_df
        # Mock summary if needed
        self.summary = pd.DataFrame({'coef': self.params_})

@pytest.fixture
def simple_data():
    # 100 samples
    return pd.DataFrame({
        'Age': np.linspace(20, 80, 100), # Range 60
        'Sex': ['Male', 'Female'] * 50,
        'Event': [1]*100,
        'Time': [10]*100
    })

def test_scaling_logic(simple_data):
    """
    Test 1: Check if Points are scaled correctly relative to Max Effect.
    Age Range: 60. Coef: 0.1 -> Effect: 6.0
    Sex: Male(1) vs Female(0). Coef: 3.0 -> Effect: 3.0
    
    Max Effect is Age (6.0).
    Age should range 0-100.
    Sex should range 0-50.
    """
    df = simple_data
    features = ['Age', 'Sex']
    
    # Mock Model
    # Dummies: Sex_Male (Female ref)
    params = {
        'Age': 0.1,
        'Sex_Male': 3.0
    }
    
    # Baseline Survival
    bs = pd.DataFrame([0.9], index=[12], columns=['baseline_survival'])
    
    model = MockCoxModel(params, bs)
    
    spec = NomogramGenerator.generate_spec(model, df, features, [12])
    
    assert spec is not None
    axes = spec['axes']
    
    # Find Age Axis
    age_axis = next(a for a in axes if a['name'] == 'Age')
    assert age_axis['type'] == 'continuous'
    pts_min = age_axis['points'][str(age_axis['min'])]
    pts_max = age_axis['points'][str(age_axis['max'])]
    
    # Check Age Points (should be 100 range)
    # Assuming coef 0.1 > 0, Min->0, Max->100
    assert pts_min == 0
    assert abs(pts_max - 100.0) < 0.001
    
    # Find Sex Axis
    sex_axis = next(a for a in axes if a['name'] == 'Sex')
    assert sex_axis['type'] == 'categorical'
    
    # Check Levels
    male = next(l for l in sex_axis['levels'] if l['label'] == 'Male')
    female = next(l for l in sex_axis['levels'] if l['label'] == 'Female')
    
    # Female (Ref) should be 0 (since coef defined as 3.0 relative to it, and 3.0 > 0)
    # Actually, min_coef = 0 (Female), max_coef = 3 (Male).
    # Effect Range = 3.
    # Points per unit = 100 / 6 = 16.666
    # Male Points = (3 - 0) * 16.666 = 50.
    
    assert female['points'] == 0
    assert abs(male['points'] - 50.0) < 0.001

def test_categorical_grouping(simple_data):
    """
    Test 2: Ensure dummy variables are correctly grouped into one axis.
    """
    df = pd.DataFrame({
        'Grade': ['I', 'II', 'III'] * 10
    })
    features = ['Grade']
    
    # Dummies: Grade_II, Grade_III (Grade_I is Ref)
    params = {
        'Grade_II': 0.5,
        'Grade_III': 1.0
    }
    bs = pd.DataFrame([0.9], index=[12], columns=['baseline_survival'])
    model = MockCoxModel(params, bs)
    
    spec = NomogramGenerator.generate_spec(model, df, features, [12])
    
    grade_axis = spec['axes'][0]
    assert grade_axis['name'] == 'Grade'
    assert len(grade_axis['levels']) == 3
    
    labels = set([l['label'] for l in grade_axis['levels']])
    assert labels == {'I', 'II', 'III'}
    
    # Check linearity
    # I (0) -> 0 pts
    # II (0.5) -> 50 pts
    # III (1.0) -> 100 pts
    # (Since this is the only variable, Max Effect is 1.0)
    
    l1 = next(l for l in grade_axis['levels'] if l['label'] == 'I')
    l2 = next(l for l in grade_axis['levels'] if l['label'] == 'II')
    l3 = next(l for l in grade_axis['levels'] if l['label'] == 'III')
    
    assert l1['points'] == 0
    assert abs(l2['points'] - 50.0) < 0.001
    assert abs(l3['points'] - 100.0) < 0.001

def test_negative_coef(simple_data):
    """
    Test 3: Handling negative coefficients.
    Age Coef: -0.1. Range 60. Effect = 6.0.
    Max should be 0 points, Min should be 100 points.
    """
    df = simple_data
    features = ['Age']
    params = {'Age': -0.1}
    bs = pd.DataFrame([0.9], index=[12], columns=['baseline_survival'])
    model = MockCoxModel(params, bs)
    
    spec = NomogramGenerator.generate_spec(model, df, features, [12])
    age = spec['axes'][0]
    
    pts_min = age['points'][str(age['min'])] # 20
    pts_max = age['points'][str(age['max'])] # 80
    
    # At min age (20), risk is HIGHER (since coef -0.1).
    # Wait, exp(-0.1 * 20) vs exp(-0.1 * 80).
    # exp(-2) > exp(-8).
    # Risk (Hazard) is higher at lower age? No.
    # HR = exp(beta * x).
    # if beta < 0, larger x -> smaller HR -> Lower Risk.
    # So larger x should have LESS points?
    # Nomogram Points usually correlate with Risk/LP.
    # Higher Points = Higher Risk (Lower Survival).
    
    # So if Coef < 0:
    # Max Value (80) -> Lowest Risk contribution -> 0 Points.
    # Min Value (20) -> Highest Risk contribution -> Max Points.
    
    assert abs(pts_min - 100.0) < 0.001
    assert pts_max == 0

def test_total_points_mapping():
    """
    Test 4: Verify Total Points and Formula Params.
    """
    df = pd.DataFrame({'X': [0, 10]})
    features = ['X']
    params = {'X': 1.0} # Range 10. Effect 10.
    bs = pd.DataFrame([0.5], index=[12], columns=['baseline_survival']) # S0(12)=0.5
    model = MockCoxModel(params, bs)
    
    spec = NomogramGenerator.generate_spec(model, df, features, [12])
    
    # Max Effect = 10. Points per unit = 100/10 = 10.
    assert spec['formula_params']['points_per_unit'] == 10.0
    
    # Min Contrib = Min(0*1, 10*1) = 0.
    assert spec['formula_params']['constant_offset'] == 0.0
    
    # Total Points Max = 100 (Single var).
    assert spec['total_points']['max'] == 100
    
    # Survival Scale
    # Check Ticks
    scale = spec['survival_scales'][0]
    assert scale['time'] == 12
    
    # Check a specific point
    # If Total Points = 50.
    # LP = 50/10 + 0 = 5.
    # S(t) = 0.5 ^ exp(5).
    # exp(5) ~ 148.
    # 0.5 ^ 148 ~ 0.
    
    # If Total Points = 0.
    # LP = 0.
    # S(t) = 0.5 ^ 1 = 0.5.
    
    tick_0 = next(t for t in scale['ticks'] if t['points'] == 0)
    assert abs(tick_0['survival'] - 0.5) < 0.001
