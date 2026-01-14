import pandas as pd
import numpy as np
from lifelines import CoxPHFitter
from app.services.evaluation_service import EvaluationService

def verify_survival_calibration():
    # 模拟生存数据
    n = 300
    np.random.seed(42)
    X = np.random.randn(n, 2)
    # 真正的风险：h(t) = exp(0.5*X1 - 0.8*X2)
    hazard = np.exp(0.5*X[:, 0] - 0.8*X[:, 1])
    time = np.random.exponential(1.0 / (hazard / 10), n) # 缩放随访时间
    event = np.random.randint(0, 2, n)
    
    df = pd.DataFrame({
        'X1': X[:, 0],
        'X2': X[:, 1],
        'time': time,
        'event': event
    })
    
    cph = CoxPHFitter()
    cph.fit(df, duration_col='time', event_col='event')
    
    # 测试多个时间点
    time_points = [10, 30, 60]
    print(f"Max time in data: {df['time'].max():.2f}")
    
    for t in time_points:
        print(f"\n--- Calibration at t={t} ---")
        res = EvaluationService.calculate_survival_calibration(cph, df, 'time', 'event', t)
        print(f"Pred: {[round(x, 3) for x in res['prob_pred']]}")
        print(f"True: {[round(x, 3) for x in res['prob_true']]}")
        
        if len(res['prob_pred']) > 0:
            print("Successfully generated calibration data.")
        else:
            print("Failed or empty calibration data.")

if __name__ == "__main__":
    try:
        verify_survival_calibration()
    except Exception as e:
        import traceback
        traceback.print_exc()
