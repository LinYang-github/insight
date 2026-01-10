# Insight 平台统计方法学白皮书 (Statistical Methodology Whitepaper)

**版本**: v1.1 (Refined)  
**发布日期**: 2026-01-10  
**核心原则**: 透明 (Transparent), 严谨 (Rigorous), 可复现 (Reproducible)

---

## 1. 概述 (Introduction)
Insight 平台致力于通过“白盒化”设计，消除医学研究中统计分析的“黑盒”现象。本白皮书详细披露了平台后端所采用的数学模型、决策算法及其在医学科研场景下的适用标准，旨在为研究结论的可靠性提供理论支柱。

---

## 2. 核心计算环境 (Computational Infrastructure)
平台基于高度稳定的 Python 科学计算栈构建，确保了计算结果的权威性与一致性：

| 模块 | 底层引擎 | 核心算法用途 |
| :--- | :--- | :--- |
| **基础统计** | `SciPy v1.11+` | 比较均值 (T-tests)、率 (Chi2/Fisher) 及方差齐性 |
| **生存分析** | `Lifelines v0.27+` | KM 曲线、Log-rank 检验、Cox 比例风险模型 (Efron) |
| **回归建模** | `Statsmodels v0.14+` | OLS 线性回归、Logistic 回归 (Fisher Scoring) |
| **倾向性匹配** | `Scikit-learn v1.3+` | 基于 Ball Tree 的最近邻搜索 (k-NN) |

---

## 3. 自动化统计决策树 (Automated Decision Flow)
Insight 针对常见的基线特征分析 (Table 1)，内置了动态算法选择逻辑。

### 3.1 连续型变量 (Continuous Variables)
系统依据样本分布及方差属性进行分流：

1.  **正态性假设**: 默认遵循中心极限定理 (CLT)。对大样本 ($N \ge 30$) 采用参数检验。
2.  **方差齐性校验 (Equality of Variances)**:
    - 算法: **Levene's Test** ($W$ 统计量)。相对于 Barlett 检验，Levene 对非正态数据的鲁棒性更强。
    - 决策:
        - 若 $P \ge 0.05$: 采用 **Student's t-test**。假设数据方差相等，自由度 $df = n_1 + n_2 - 2$。
        - 若 $P < 0.05$: 采用 **Welch's t-test** (Satterthwaite 近似)。不假设方差相等，通过校正自由度来修正 I 类错误率。

### 3.2 分类/等级变量 (Categorical Variables)
比较各组间的百分比/率：

1.  **卡方检验 (Pearson’s $\chi^2$ Test)**: 默认用于大样本。
2.  **Fisher 精确检验 (Fisher's Exact Test)**:
    - **自动触发条件 (Cochran's Rule)**: 
        - 对于 2x2 列表，若存在单元格的期望频数 (Expected Count) $< 5$。
        - 理由: 在小样本或分布极不均衡时，卡方统计量的连续性近似失效，Fisher 精确概率能提供更准确的 P 值。

---

## 4. 观察性研究: 倾向性评分匹配 (PSM)
为了模拟随机对照试验 (RCT) 效果，Insight 提供了一套标准化的 PSM 工作流。

### 4.1 评分估计 (Propensity Score Estimation)
- **模型**: 二元 Logistic 回归。
- **目标变量 ($Y$)**: 组别标识 ($1$=处理组, $0$=对照组)。
- **线性预测因子**: 用户选定的协变量 (Covariates)。

### 4.2 匹配策略 (Matching Scenarios)
- **核心算法**: 1:1 最近邻匹配 (Nearest Neighbor Matching)。
- **操作方式**: 无放回 (Without Replacement)。一旦某一对样本匹配成功，该对照组样本将不再参与后续匹配。
- **平衡性评估**: 采用**标准化均数差 (SMD)** 衡量。
  $$SMD = \frac{|\bar{X}_{treated} - \bar{X}_{control}|}{\sqrt{(s^2_{treated} + s^2_{control}) / 2}}$$
  - **医学标准**: $SMD < 0.1$ 被视为临床均衡的理想状态。

---

## 5. 回归模型与假设检验 (Regression Framework)

### 5.1 Cox 比例风险模型 (Cox Proportional Hazards)
- **结处理 (Tie Handling)**: 默认采用 **Efron 近似**。相比较简单的 Breslow 方法，Efron 在同一时间点发生多个终点事件时表现更优。
- **结果输出**: 提供风险比 (Hazard Ratio, HR) 及其偏似然估计的 95% 置信区间。

### 5.2 多重共线性诊断 (Collinearity Diagnostics)
为防止虚假模型，系统自动计算 **方差膨胀因子 (VIF)**：
- $VIF_i = \frac{1}{1 - R_i^2}$。
- 若 $VIF > 5$，系统将发出黄色警告；若出现奇异矩阵 (Singular Matrix)，将强制终止计算并定位共线变量。

---

## 6. 缺失值处理策略 (Handling Missing Data)
Insight 秉持严谨的科学态度，默认对建模变量采用 **Listwise Deletion (成列删除)**：
- 任何包含空缺值的样本（行）将不进入统计模型。
- **理由**: 确保了模型结果的一致性。系统会提示缺失值造成的样本量损失比例。

---

## 7. “白盒”元数据结构 (Transparency Metadata)
每个统计接口均返回 `_meta` 字段，其结构如下（供技术复现参考）：
```json
"_meta": {
  "algorithm": "Welch's T-test",
  "reason": "Levene's test failed (P<0.05), assuming unequal variances.",
  "vif_check": "Passed",
  "checks": [
    { "type": "sample_size", "status": "ok", "n": 240 }
  ]
}
```

---

## 8. 正确引用 (Citation)
发表文章时，请在方法学部分引用如下段落：

> "Statistical procedures were performed using Insight Platform (v1.1, lin-yang/insight). Continuous variables were analyzed using Student’s or Welch’s t-test following variance homogeneity assessment by Levene’s test. Categorical variables were evaluated via Pearson’s chi-square or Fisher’s exact test according to Cochran's rule. For observational analysis, 1:1 Propensity Score Matching was applied without replacement. Cox regression utilized Efron’s method for tie handling. Confidence intervals were calculated at the 95% level, with P < 0.05 indicating statistical significance."

---

*技术顾问与科学委员会 (Scientific Board): lin-yang/insight*
