import pandas as pd
import numpy as np
import sys
import os

# Mock paths so we can import app modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.utils.nomogram_generator import NomogramGenerator

class MockCox:
    def __init__(self):
        # Age (Cont), Sex_Male (Cat), Race_Black (Cat)
        # Age: Range 20-80. Coef 0.05.
        # Sex_Male: 1 vs 0. Coef 0.5.
        # Race_Black: 1 vs 0. Coef -0.3.
        
        self.params_ = pd.Series({
            'Age': 0.05,
            'Sex_Male': 0.5,
            'Race_Black': -0.3
        })
        self.summary = pd.DataFrame() # Not used by current generator except maybe checks
        
        # Mock Baseline Survival
        # Times: 10, 20, 30...
        # S0(t) = exp(-0.01 * t)
        times = [10, 20, 30, 40, 50, 60]
        survs = [np.exp(-0.01 * t) for t in times]
        self.baseline_survival_ = pd.DataFrame(survs, index=times, columns=['baseline_survival'])

def test_nomogram_generator():
    print("Testing NomogramGenerator...")
    
    # 1. Create Mock Data (Original DF)
    df = pd.DataFrame({
        'Age': np.random.randint(20, 80, 100),
        'Sex': np.random.choice(['Female', 'Male'], 100),
        'Race': np.random.choice(['White', 'Black'], 100),
        'Time': np.random.randint(10, 60, 100),
        'Event': np.random.randint(0, 2, 100)
    })
    
    features = ['Age', 'Sex', 'Race']
    
    cph = MockCox()
    
    # 2. Generate Spec
    spec = NomogramGenerator.generate_spec(cph, df, features, [12, 36, 60])
    
    # 3. Validation
    if not spec:
        print("FAILED: Spec is None")
        return

    axes = spec['axes']
    print(f"Axes found: {[a['name'] for a in axes]}")
    
    # Validate Age (Continuous)
    age = next(a for a in axes if a['name'] == 'Age')
    print(f"Age Axis: Min={age['min']}, Max={age['max']}")
    # Coef 0.05. Range 60. Effect = 3. 
    # Sex Coef 0.5. Range 1. Effect = 0.5.
    # Age should be main axis? 3 vs 0.5 vs 0.3. Yes Age is max.
    # So Age should have scale 0-100.
    
    # Validate Points scaling
    # Age Min (20) -> Point?
    # Coef > 0, so Min should be 0 points?
    # Wait, generator logic:
    # contributions = [min*coef, max*coef]. 
    # points_at_min = 0 (if normalized locally).
    # Let's check spec['points']
    pts_min = age['points'][str(age['min'])]
    pts_max = age['points'][str(age['max'])]
    print(f"Age Points: {age['min']}->{pts_min}, {age['max']}->{pts_max}")
    
    if abs(pts_max - 100) < 1:
        print("SUCCESS: Age scaled to ~100 points")
    else:
        print(f"WARNING: Age max points is {pts_max}")

    # Validate Sex (Categorical)
    sex = next(a for a in axes if a['name'] == 'Sex')
    print(f"Sex Axis: Levels={[l['label'] for l in sex['levels']]}")
    # Female (Ref) should be 0 points?
    # Male (Coef 0.5).
    # Age Effect 3.0 -> 100 pts.
    # Sex Effect 0.5 -> ~16.6 pts.
    male_pts = next(l['points'] for l in sex['levels'] if l['label'] == 'Male')
    print(f"Male Points: {male_pts}")
    
    if 15 < male_pts < 18:
        print("SUCCESS: Sex scaled correctly relative to Age")
    else:
        print("WARNING: Sex points scaling likely off")

    # Validate Survival Scales
    print(f"Survival Scales for times: {[s['time'] for s in spec['survival_scales']]}")
    
    print("Test Complete.")

if __name__ == "__main__":
    test_nomogram_generator()
