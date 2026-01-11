# benchmark_cox.R
# Insight Platform - Open Validation Pack
# Goal: Verify Cox Proportional Hazards Model

# 1. Load Libraries
if (!require("survival")) install.packages("survival")
library(survival)

# 2. Load Data
df <- read.csv("../benchmark_cox.csv")

# 3. Fit Cox Model
# Using Efron handling for ties (Standard)
model <- coxph(Surv(week, arrest) ~ fin + age + prio, data = df, ties = "efron")

# 4. Output Results
print(summary(model))
print("Coefficients:")
print(coef(model))
print("HR (Exp Coef):")
print(exp(coef(model)))

# 5. Check Assumptions
test.ph <- cox.zph(model)
print("PH Assumption Check:")
print(test.ph)
