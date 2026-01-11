import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import proportional_hazard_test

# 1. Load Data
df = pd.read_csv("../benchmark_cox.csv")

# 2. Fit Cox Model
cph = CoxPHFitter()
cph.fit(df, duration_col='week', event_col='arrest')

# 3. Output Results
print(cph.summary)

# 4. Check Assumption
print("PH Assumption Check:")
results = proportional_hazard_test(cph, df, time_transform='rank')
print(results.print_summary())
