
import pytest
import pandas as pd
import numpy as np
from app.services.advanced_modeling_service import AdvancedModelingService

def test_rcs_cox_ci():
    """
    Verify that fit_rcs returns confidence intervals for Cox models.
    """
    np.random.seed(42)
    n = 1000
    # Exposure X: Uniform [0, 10]
    x = np.random.uniform(0, 10, n)
    # Hazard: Non-linear effect (U-shape centered at 5)
    # log_h = (x - 5)^2 / 10
    log_h_true = (x - 5)**2 / 10
    
    # Simulate Survival Time
    # T ~ Exp(lambda(x))
    # lambda(x) = baseline * exp(log_h)
    baseline_hazard = 0.1
    lambdas = baseline_hazard * np.exp(log_h_true)
    t = np.random.exponential(1 / lambdas)
    
    # Censoring: 10% censored
    c = np.random.exponential(10, n)
    obs_t = np.minimum(t, c)
    event = (t <= c).astype(int)
    
    df = pd.DataFrame({
        'time': obs_t,
        'event': event,
        'BMI': x, # Exposure
        'Age': np.random.normal(50, 10, n) # Covariate
    })
    
    print(f"Data generated: N={n}, Events={event.sum()}")

    print("Running RCS Cox...")
    # fit_rcs(df, target, event_col, exposure, covariates, model_type='cox', knots=3)
    results = AdvancedModelingService.fit_rcs(
        df, 'time', 'event', 'BMI', ['Age'], model_type='cox', knots=3
    )
    
    plot_data = results['plot_data']
    
    # Check if 'lower' and 'upper' exist and are not equal to 'y' (which happens if filled with mean or default)
    # The current implementation returns 'y' in place of CI if not calculated? 
    # Or strict check: keys must exist.
    
    first_pt = plot_data[0]
    print("First Point:", first_pt)
    
    assert 'lower' in first_pt, "CI Lower bound missing"
    assert 'upper' in first_pt, "CI Upper bound missing"
    
    # Check width
    # If not implemented, they might be equal to y or None
    # If standard error is 0 (impossible), then lower=upper.
    if first_pt['lower'] == first_pt['y'] and first_pt['upper'] == first_pt['y']:
        print("FAIL: CI width is zero (Not Implemented).")
        # Find a point where estimated HR is not 1 (ref)
        # Ref is median. At extrema it should be wide.
        non_ref_pts = [p for p in plot_data if abs(p['y'] - 1.0) > 0.1]
        if non_ref_pts:
            pt = non_ref_pts[0]
            if pt['lower'] == pt['y']:
                 pytest.fail("CI not implemented (lower == estimate)")
    
    print("Verification Passed: Cox RCS has Confidence Intervals.")

if __name__ == "__main__":
    test_rcs_cox_ci()
