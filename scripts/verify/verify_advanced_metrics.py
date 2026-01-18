import pandas as pd
import numpy as np
import sys
import os

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))


from app.services.evaluation_service import EvaluationService

class MockModel:
    def predict_survival_function(self, df, times):
        # Return naive survival: 0.8 for everyone
        return pd.DataFrame([[0.8]*len(df)], index=times, columns=df.index)

def test_binary_metrics():
    print("Testing Binary Metrics...")
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.4, 0.35, 0.8])
    # Truth: 0, 0, 1, 1
    # Prob: 0.1, 0.4, 0.35, 0.8
    # Optimal threshold by Youden?
    # Thresholds: 0.1, 0.35, 0.4, 0.8
    # At 0.35: Preds 0, 1, 1, 1. TP=2, TN=1, FP=1, FN=0. Se=1, Sp=0.5. Youden=0.5.
    # At 0.4: Preds 0, 1, 0, 1. TP=1, TN=1, FP=1, FN=1. Se=0.5, Sp=0.5. Youden=0.
    
    # Wait, roc_curve thresholds logic:
    # y_score sorted: 0.8(1), 0.4(0), 0.35(1), 0.1(0)
    
    res = EvaluationService.calculate_binary_metrics_at_threshold(y_true, y_prob)
    print(res)
    
    assert 'sensitivity' in res
    assert 'specificity' in res
    assert 'youden_index' in res
    print("Binary Metrics passed.")

def test_survival_metrics():
    print("Testing Survival Metrics...")
    df = pd.DataFrame({
        'time': [10, 20, 30, 40],
        'event': [1, 0, 1, 0]
    })
    
    model = MockModel()
    
    # T = 15
    # ID 0: T=10, E=1. (Event before 15). Case.
    # ID 1: T=20, E=0. (Censored after 15). Control.
    # ID 2: T=30, E=1. (Event after 15). Control for T=15? No, Control (survived past 15).
    # ID 3: T=40, E=0. (Censored after 15). Control.
    
    # Case: ID 0.
    # Control: ID 1, 2, 3.
    # Mask should keep all.
    
    res = EvaluationService.calculate_survival_metrics_at_t(model, df, 'time', 'event', 15)
    print(res)
    
    assert res['sensitivity'] is not None
    assert res['brier_score'] is not None
    print("Survival Metrics passed.")

def test_nri_idi():
    print("Testing NRI/IDI...")
    y_true = [0, 0, 1, 1]
    # Old Model: Random guess (.5)
    p_old = [0.5, 0.5, 0.5, 0.5]
    # New Model: Perfect
    p_new = [0.1, 0.1, 0.9, 0.9]
    
    # Events (1, 1): Old=0.5, New=0.9. Improvement (Up).
    # NRI_Event = (2 - 0) / 2 = 1.0.
    
    # NonEvents (0, 0): Old=0.5, New=0.1. Improvement (Down).
    # NRI_NonEvent = (2 - 0) / 2 = 1.0.
    
    # Total NRI = 2.0. (Max possible)
    
    # IDI
    # Event Diff = 0.4. Mean = 0.4.
    # NonEvent Diff = -0.4. Mean = -0.4.
    # IDI = 0.4 - (-0.4) = 0.8.
    
    res = EvaluationService.calculate_nri_idi(y_true, p_old, p_new)
    print(res)
    
    assert abs(res['nri'] - 2.0) < 0.001
    assert abs(res['idi'] - 0.8) < 0.001
    print("NRI/IDI passed.")

if __name__ == "__main__":
    test_binary_metrics()
    test_survival_metrics()
    test_nri_idi()
