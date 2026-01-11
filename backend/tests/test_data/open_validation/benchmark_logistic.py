import pandas as pd
import statsmodels.formula.api as smf

# 1. Load Data
df = pd.read_csv("../benchmark_logistic.csv")

# 2. Fit Logistic Regression
model = smf.logit("grade ~ gpa + tuce + psi", data=df).fit()

# 3. Output Results
print(model.summary())
print("Coefficients:")
print(model.params)
print("Conf Int:")
print(model.conf_int())
