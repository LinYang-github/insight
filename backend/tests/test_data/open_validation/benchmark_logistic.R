# benchmark_logistic.R
# Insight Platform - Open Validation Pack
# Goal: Verify Logistic Regression Coefficients

# 1. Load Data
df <- read.csv("../benchmark_logistic.csv")

# 2. Fit GLM (Logistic)
model <- glm(grade ~ gpa + tuce + psi, data = df, family = binomial(link = "logit"))

# 3. Output Results
print(summary(model))
print("Coefficients:")
print(coef(model))
print("ConfInt:")
print(confint.default(model))
