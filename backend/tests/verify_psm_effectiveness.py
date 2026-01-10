
import pytest
import pandas as pd
import numpy as np
from app.services.statistics_service import StatisticsService

def test_psm_effectiveness():
    """
    Verify that PSM actually reduces bias (SMD - Standardized Mean Difference).
    Scenario:
    - Confounder 'Age': Older people are more likely to get Treatment (1).
    - We expect 'Age' SMD to be high before matching, and low (<0.1) after matching.
    """
    np.random.seed(42)
    n = 1000
    
    # Generate Confounder: Age
    age = np.random.normal(60, 10, n)
    
    # Generate Treatment: Probability depends on Age (Confounding)
    # Sigmoid function
    z = (age - 60) / 5
    prob_t = 1 / (1 + np.exp(-z))
    treatment = np.random.binomial(1, prob_t)
    
    df = pd.DataFrame({
        'Age': age,
        'Treatment': treatment,
        'Outcome': np.random.normal(0, 1, n) # Irrelevant for matching
    })
    
    # Verify Prematch Imbalance
    treated = df[df['Treatment'] == 1]
    control = df[df['Treatment'] == 0]
    
    smd_pre = StatisticsService._calc_smd(treated, control, 'Age')
    print(f"Pre-match SMD for Age: {smd_pre:.4f}")
    
    # Expect significant imbalance (e.g., > 0.5)
    assert smd_pre > 0.2, "Synthetic data failed to simulate confounding bias."
    
    # Run PSM
    result = StatisticsService.perform_psm(df, treatment='Treatment', covariates=['Age'])
    
    # Verify Postmatch Balance
    balance_stats = result['balance']
    # Find Age stat
    age_stat = next(item for item in balance_stats if item['variable'] == 'Age')
    smd_post = age_stat['smd_post']
    
    print(f"Post-match SMD for Age: {smd_post:.4f}")
    
    # Expect good balance (< 0.1 is standard, < 0.2 acceptable)
    assert smd_post < 0.2, f"PSM failed to balance Covariate Age. Post SMD: {smd_post}"
    
    print("PSM Effectiveness Verified: Bias significantly reduced.")

if __name__ == "__main__":
    test_psm_effectiveness()
