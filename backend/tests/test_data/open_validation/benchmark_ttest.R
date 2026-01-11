# benchmark_ttest.R
# Insight Platform - Open Validation Pack
# Goal: Verify Independent Samples T-Test (Welch's)

# 1. Load Data
df <- read.csv("../benchmark_ttest.csv")

# 2. Run T-Test
# Note: R defaults to var.equal = FALSE (Welch's t-test)
res <- t.test(len ~ supp, data = df)

# 3. Output Results
print(res)
print("P-value:")
print(res$p.value)

# 4. Check Normality (Shapiro-Wilk)
print("Shapiro-Wilk Test for Normality:")
groups <- unique(df$supp)
for (g in groups) {
  cat(paste("Group:", g, "\n"))
  sub_data <- df$len[df$supp == g]
  print(shapiro.test(sub_data))
}
