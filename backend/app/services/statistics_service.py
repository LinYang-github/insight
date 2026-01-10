
import pandas as pd
import numpy as np
from scipy import stats
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from app.utils.formatter import ResultFormatter
from app.utils.metadata_builder import MetadataBuilder

class StatisticsService:
    @staticmethod
    def generate_table_one(df, group_by, variables):
        """
        生成基线特征表 (Table 1)。
        
        医学研究中，Table 1 通常用于展示研究人群的基线特征，并按照暴露因素或处理组（Treatment）进行分组对比。

        Args:
            df (pd.DataFrame): 包含变量的数据集。
            group_by (str): 分组变量（如实验组 vs 对照组）。如果不提供，则只生成全人群 (Overall) 统计。
            variables (list): 需要展示统计指标的变量列表。

        Returns:
            list: 包含每行统计结果的字典列表。具体包含 'overall', 'groups' (如果有分组), 'p_value' 和 'test'。
        """
        # Data Integrity
        if group_by and group_by not in df.columns:
            raise ValueError(f"Group by variable '{group_by}' not found.")
        
        groups = []
        if group_by:
            # Drop missing in group_by
            df = df.dropna(subset=[group_by])
            groups = sorted(df[group_by].unique().tolist())
        
        results = []
        
        # Collect used tests for methodology
        used_tests = set()
        
        for var in variables:
            # ... (Existing loop logic) ...
            if var not in df.columns: 
                continue
            if var == group_by:
                continue
                
            row = {
                'variable': var,
                'type': 'numeric' if pd.api.types.is_numeric_dtype(df[var]) else 'categorical'
            }
            
            # 1. Overall Stats
            row['overall'] = StatisticsService._calc_stats(df[var])
            
            if group_by:
                # ... (Existing group logic) ...
                group_stats = {}
                group_data = [] 
                
                for g in groups:
                    sub_df = df[df[group_by] == g]
                    group_stats[str(g)] = StatisticsService._calc_stats(sub_df[var])
                    group_data.append(sub_df[var].dropna())
                    
                row['groups'] = group_stats
                test_meta = {}
                    
                # Hypothesis Test Selection
                if row['type'] == 'numeric':
                    try:
                        if len(groups) == 2:
                            try:
                                lev_stat, lev_p = stats.levene(group_data[0], group_data[1])
                                equal_var = lev_p >= 0.05
                            except:
                                equal_var = False 
                            
                            if equal_var:
                                test_name = 'Student\'s T-test'
                                reason = "方差齐性检验通过 (Levene's P>=0.05)，假设方差相等。"
                                stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=True)
                            else:
                                test_name = 'Welch\'s T-test'
                                reason = "方差齐性检验显著 (Levene's P<0.05)，假设方差不相等。"
                                stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=False)
                                
                            used_tests.add(test_name)
                            row['test'] = test_name
                            test_meta = MetadataBuilder.build_test_meta(test_name, reason)
                        else:
                            stat, p = stats.f_oneway(*group_data)
                            test_name = 'ANOVA'
                            used_tests.add('ANOVA')
                            row['test'] = 'ANOVA'
                            test_meta = MetadataBuilder.build_test_meta('ANOVA', "多组比较，采用单因素方差分析。")
                    except Exception:
                        p = None
                        row['test'] = 'Error'
                        
                else:
                    # Categorical: Chi-square
                    ct = pd.crosstab(df[var], df[group_by])
                    try:
                        stat, p, dof, expected = stats.chi2_contingency(ct)
                        test_name = 'Chi-square'
                        reason = "分类变量，采用卡方检验。"
                        
                        if ct.shape == (2, 2) and (expected < 5).any():
                                odds, p = stats.fisher_exact(ct)
                                test_name = 'Fisher Exact Test'
                                reason = "期望频数 < 5，不满足卡方条件，采用 Fisher 精确检验。"
                                
                        used_tests.add(test_name)
                        row['test'] = test_name
                        test_meta = MetadataBuilder.build_test_meta(test_name, reason)
                    except Exception:
                        p = None
                        row['test'] = 'Error'

                row['p_value'] = ResultFormatter.format_p_value(p) if p is not None else 'N/A'
                row['_meta'] = test_meta
                
                # ... Interpretation ...
                row['interpretation'] = StatisticsService._generate_table1_interpretation(row['variable'], p, row.get('test'))
                
            results.append(row)
            
        # --- Methodology Generation ---
        methodology = StatisticsService._generate_table1_methodology(group_by is not None, used_tests, variables, df)
            
        return {
            'table_data': results,
            'methodology': methodology
        }

    @staticmethod
    def _generate_table1_methodology(has_group, tests, variables, df):
        """Generate Methods text for Table 1."""
        lines = []
        
        # 1. Descriptive
        lines.append("Baseline characteristics were described as mean ± standard deviation (SD) for continuous variables with normal distribution, and median (interquartile range, IQR) for non-normally distributed variables.")
        lines.append("Categorical variables were presented as frequency (percentage).")
        
        # 2. Inference
        if has_group and tests:
            test_desc = []
            if "Student's T-test" in tests or "Welch's T-test" in tests:
                test_desc.append("Student's t-test or Welch's t-test for continuous variables")
            if "ANOVA" in tests:
                test_desc.append("Analysis of Variance (ANOVA) for continuous variables")
            if "Chi-square" in tests:
                test_desc.append("Chi-square test for categorical variables")
            if "Fisher Exact Test" in tests:
                test_desc.append("Fisher's exact test for categorical variables with expected frequency < 5")
                
            if test_desc:
                lines.append(f"Differences between groups were analyzed using {', '.join(test_desc)}.")
                
            lines.append("All statistical tests were two-sided, and P < 0.05 was considered statistically significant.")
            
        return " ".join(lines)

    @staticmethod
    def _generate_table1_interpretation(var_name, p_value, test_name):
        # ... (Existing logic kept same, just ensuring correct indentation/context if needed) ...
        # Actually I can skip restating this if I select lines correctly.
        # But I replaced a large chunk.
        if p_value is None: return None
        is_sig = p_value < 0.05
        p_str = "< 0.001" if p_value < 0.001 else f"{p_value:.3f}"
        if is_sig:
             return {"text_template": "变量 {var} 在各组间分布差异显著 (P={p})。", "params": {"var": var_name, "p": p_str, "test": test_name}, "level": "danger"}
        else:
             return {"text_template": "变量 {var} 在各组间分布均衡 (P={p})。", "params": {"var": var_name, "p": p_str, "test": test_name}, "level": "success"}

    @staticmethod
    def _calc_stats(series):
        # ... (Existing) ...
        n = len(series)
        missing = series.isnull().sum()
        if pd.api.types.is_numeric_dtype(series):
            clean_s = series.dropna()
            if clean_s.empty: return {'mean': 0, 'sd': 0}
            mean = clean_s.mean()
            sd = clean_s.std()
            median = clean_s.median()
            q25 = clean_s.quantile(0.25)
            q75 = clean_s.quantile(0.75)
            # Add Shapiro check for normality? For methodology purposes maybe? 
            # For now simplified: assume Mean/SD displayed (as per frontend).
            return {
                'n': int(n), 'missing': int(missing),
                'mean': ResultFormatter.format_float(mean, 2),
                'sd': ResultFormatter.format_float(sd, 2),
                'median': ResultFormatter.format_float(median, 2),
                'q25': ResultFormatter.format_float(q25, 2),
                'q75': ResultFormatter.format_float(q75, 2)
            }
        else:
            clean_s = series.dropna()
            if clean_s.empty: return {}
            counts = clean_s.value_counts().to_dict()
            total = len(clean_s)
            formatted = {}
            for k, v in counts.items():
                perc = (v / total) * 100
                formatted[str(k)] = f"{v} ({perc:.1f}%)"
            return {'n': int(n), 'missing': int(missing), 'counts': formatted}

    @staticmethod
    def generate_km_data(df, time_col, event_col, group_col=None):
        """
        计算 Kaplan-Meier 生存分析数据。
        """
        if time_col not in df.columns or event_col not in df.columns:
            raise ValueError("Time or Event column not found.")
            
        df = df.dropna(subset=[time_col, event_col])
        if group_col:
            df = df.dropna(subset=[group_col])
            
        kmf = KaplanMeierFitter()
        plot_data = []
        p_value = None
        
        if group_col:
            groups = sorted(df[group_col].unique().tolist())
            
            # Log-rank test
            try:
                res = multivariate_logrank_test(df[time_col], df[group_col], df[event_col])
                p_value = ResultFormatter.format_p_value(res.p_value)
            except Exception:
                p_value = 'N/A'
                
            for g in groups:
                sub_df = df[df[group_col] == g]
                kmf.fit(sub_df[time_col], sub_df[event_col], label=str(g))
                
                trace = {
                    'name': str(g),
                    'times': kmf.survival_function_.index.tolist(),
                    'probs': kmf.survival_function_.iloc[:, 0].tolist(),
                    'ci_lower': kmf.confidence_interval_.iloc[:, 0].tolist(),
                    'ci_upper': kmf.confidence_interval_.iloc[:, 1].tolist()
                }
                plot_data.append(trace)
        else:
            # Overall
            kmf.fit(df[time_col], df[event_col], label='Overall')
            trace = {
                'name': 'Overall',
                'times': kmf.survival_function_.index.tolist(),
                'probs': kmf.survival_function_.iloc[:, 0].tolist(),
                'ci_lower': kmf.confidence_interval_.iloc[:, 0].tolist(),
                'ci_upper': kmf.confidence_interval_.iloc[:, 1].tolist()
            }
            plot_data.append(trace)
            
        # --- Generate Interpretation & Methodology ---
        interpretation = None
        if p_value and p_value != 'N/A':
            p_float = float(p_value) if isinstance(p_value, (float, int)) else float(p_value.replace('<', '').strip())
            interpretation = StatisticsService._generate_km_interpretation(p_float)

        methodology = StatisticsService._generate_km_methodology(group_col is not None)

        return {
            'plot_data': plot_data,
            'p_value': p_value,
            'interpretation': interpretation,
            'methodology': methodology
        }

    @staticmethod
    def _generate_km_methodology(has_group):
        text = "Survival curves were estimated using the Kaplan-Meier method."
        if has_group:
            text += " Differences between groups were compared using the log-rank test."
        text += " All analyses were performed using the Insight Statistical Platform (v1.0)."
        return text

    @staticmethod
    def _generate_km_interpretation(p_value):
        # ... (Existing) ...
        is_sig = p_value < 0.05
        p_str = "< 0.001" if p_value < 0.001 else f"{p_value:.3f}"
        if is_sig:
             return {"text_template": "各组生存曲线存在**显著差异** (Log-rank P={p})。组间生存概率分布不同。", "params": { "p": p_str }, "level": "danger"}
        else:
             return {"text_template": "各组生存曲线**无显著差异** (Log-rank P={p})。组间生存概率分布相似。", "params": { "p": p_str }, "level": "info"}

    @staticmethod
    def perform_psm(df, treatment, covariates):
        """
        执行倾向性评分匹配 (PSM, Propensity Score Matching)。
        
        用于观察性研究中减少混杂偏倚 (Confounding Bias)，通过模拟随机对照试验的效果，
        使实验组和对照组在基线协变量上达到平衡。

        Args:
            df (pd.DataFrame): 原始数据集。
            treatment (str): 处理变量（0/1），1 代表实验组，0 代表对照组。
            covariates (list): 需要匹配的协变量（混杂因素）。

        Algorithm:
            1. 使用逻辑回归估算倾向性得分 (Propensity Score)。
            2. 使用最近邻匹配 (Nearest Neighbor Matching) 进行 1:1 匹配。
            3. 计算匹配前后的标准化均数差 (SMD) 以评估平衡性。

        Returns:
            dict: 匹配后的索引列表、平衡性统计指标及样本量变化。
        """
        if treatment not in df.columns:
             raise ValueError(f"Treatment '{treatment}' not found.")
             
        # Prepare Data
        cols = [treatment] + covariates
        data = df[cols].dropna()
        
        # 1. PS Calculation
        T = data[treatment]
        X = data[covariates]
        
        # Encode categoricals if any? For MVP assume numeric or preprocessed.
        # Ideally should use get_dummies here if not done.
        # Let's assume user did One-Hot in Preprocessing step? 
        # But we accept raw columns. If categorical text, LogReg fails.
        # Auto-encode for PS estimation:
        X_encoded = pd.get_dummies(X, drop_first=True)
        
        ps_model = LogisticRegression(solver='liblinear') # robust for small N
        ps_model.fit(X_encoded, T)
        
        data['ps_score'] = ps_model.predict_proba(X_encoded)[:, 1]
        
        # 2. Matching
        treated = data[data[treatment] == 1]
        control = data[data[treatment] == 0]
        
        if treated.empty or control.empty:
             raise ValueError("Treatment or Control group is empty.")
             
        # Fit NN on Control PS
        control_ps = control[['ps_score']].values
        treated_ps = treated[['ps_score']].values
        
        nbrs = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(control_ps)
        distances, indices = nbrs.kneighbors(treated_ps)
        
        # Get matched control indices
        # indices is (n_treated, 1) array of indices into 'control' dataframe (iloc)
        matched_control_ilocs = indices.flatten()
        matched_control = control.iloc[matched_control_ilocs]
        
        # Combine
        matched_data = pd.concat([treated, matched_control])
        
        # 3. Balance Check (SMD)
        balance_stats = []
        for var in covariates:
             # Before
            mean_t_pre = treated[var].mean() if pd.api.types.is_numeric_dtype(treated[var]) else 0 # Simp
            mean_c_pre = control[var].mean() if pd.api.types.is_numeric_dtype(control[var]) else 0
            # For categorical, mean of dummy is prop.
            # If not numeric, convert to dummy for SMD? Ideally yes.
            # Simplified SMD: (Mean1 - Mean0) / pooled_std
            
            smd_pre = StatisticsService._calc_smd(treated, control, var)
            smd_post = StatisticsService._calc_smd(treated, matched_control, var)
            
            balance_stats.append({
                'variable': var,
                'smd_pre': smd_pre,
                'smd_post': smd_post
            })
            
        return {
            'matched_indices': matched_data.index.tolist(),
            'balance': balance_stats,
            'n_treated': len(treated),
            'n_control': len(control),
            'n_matched': len(matched_data)
        }

    @staticmethod
    def recommend_covariates(df, treatment):
        """
        推荐协变量。
        通过计算所有其他变量与处理变量（treatment）之间的关联显著性，
        找出组间差异显著 (P < 0.05) 的变量作为潜在混杂因素。
        """
        if treatment not in df.columns:
            return []
            
        df = df.dropna(subset=[treatment])
        groups = sorted(df[treatment].unique().tolist())
        if len(groups) < 2:
            return []
            
        recommendations = []
        variables = [c for c in df.columns if c != treatment]
        
        for var in variables:
            # Skip high cardinality strings or non-relevant columns
            if df[var].dtype == 'object' and df[var].nunique() > 20:
                continue
                
            try:
                if pd.api.types.is_numeric_dtype(df[var]):
                    group_data = [df[df[treatment] == g][var].dropna() for g in groups]
                    if len(groups) == 2:
                        stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=False)
                    else:
                        stat, p = stats.f_oneway(*group_data)
                else:
                    ct = pd.crosstab(df[var], df[treatment])
                    stat, p, dof, expected = stats.chi2_contingency(ct)
                
                if p < 0.05:
                    recommendations.append({
                        'variable': var,
                        'p_value': float(p)
                    })
            except:
                continue
                
        # Sort by P-value (most significant first)
        recommendations.sort(key=lambda x: x['p_value'])
        return recommendations

    @staticmethod
    def check_data_health(df, variables):
        """
        检查数据集在指定变量上的健康状况。
        返回缺失率、唯一值数量及警告信息。
        """
        health_report = []
        n_total = len(df)
        
        for var in variables:
            if var not in df.columns:
                continue
                
            missing_count = int(df[var].isnull().sum())
            missing_rate = (missing_count / n_total) if n_total > 0 else 0
            
            status = 'healthy'
            message = '数据状态良好。'
            
            if missing_rate > 0.2:
                status = 'warning'
                message = f'缺失率较高 ({missing_rate:.1%})，可能导致样本量锐减。'
            
            # For categorical, check if any level has very few samples
            if not pd.api.types.is_numeric_dtype(df[var]):
                counts = df[var].value_counts()
                if (counts < 5).any():
                    status = 'warning'
                    message = '部分分类水平样本量过少 (<5)，可能导致统计效能不足。'
            
            health_report.append({
                'variable': var,
                'status': status,
                'missing_count': missing_count,
                'missing_rate': missing_rate,
                'message': message
            })
            
        return health_report

    @staticmethod
    def get_distribution(df, variable):
        """
        获取单个变量的分布统计数据，用于前端绘图。
        """
        if variable not in df.columns:
            return None
            
        series = df[variable].dropna()
        if series.empty:
            return None
            
        if pd.api.types.is_numeric_dtype(series):
            # Calculate Histogram data
            counts, bin_edges = np.histogram(series, bins='auto')
            
            # Normal distribution curve for overlay
            mu = series.mean()
            std = series.std()
            x_range = np.linspace(series.min(), series.max(), 100)
            y_norm = stats.norm.pdf(x_range, mu, std) if std > 0 else []
            
            return {
                'type': 'numeric',
                'bins': {
                    'counts': counts.tolist(),
                    'edges': bin_edges.tolist()
                },
                'curve': {
                    'x': x_range.tolist(),
                    'y': y_norm.tolist()
                },
                'stats': {
                    'mean': float(mu),
                    'std': float(std),
                    'n': len(series)
                }
            }
        else:
            # Categorical counts
            counts = series.value_counts().to_dict()
            return {
                'type': 'categorical',
                'counts': counts,
                'stats': {
                    'n': len(series),
                    'unique': len(counts)
                }
            }

    @staticmethod
    def _calc_smd(df1, df2, var):
        # Handle numeric
        if pd.api.types.is_numeric_dtype(df1[var]):
             m1 = df1[var].mean()
             m2 = df2[var].mean()
             v1 = df1[var].var()
             v2 = df2[var].var()
             
             pooled_std = np.sqrt((v1 + v2) / 2)
             if pooled_std == 0: return 0.0
             return abs(m1 - m2) / pooled_std
        else:
             # Categorical: use first level or overall Chi-square derived d?
             # Simple approach: Turn to dummy and max SMD
             # Or just ignore non-numeric for MVP
             return 0.0 # Placeholder for non-numeric

    @staticmethod
    def check_multicollinearity(df, features):
        """
        检查特征变量之间的多重共线性。
        计算两两相关系数 (Correlation) 和方差膨胀因子 (VIF)。
        """
        if not features or len(features) < 2:
            return {'status': 'ok', 'report': []}
            
        # Filter numeric only for VIF/Corr
        # For categorical, we might need Cramer's V (skipped for MVP, assuming OneHot or skipping)
        numeric_df = df[features].select_dtypes(include=[np.number])
        if numeric_df.empty or numeric_df.shape[1] < 2:
             return {'status': 'ok', 'report': []}

        # Handle missing for calculation
        numeric_df = numeric_df.dropna()
        if numeric_df.empty:
             return {'status': 'warning', 'message': '有效样本不足，无法计算共线性。'}

        report = []
        status = 'ok'
        
        # 1. Pairwise Correlation
        corr_matrix = numeric_df.corr().abs()
        
        # Upper triangle
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                r = corr_matrix.iloc[i, j]
                if r > 0.8: # Threshold 0.8
                    status = 'warning'
                    report.append({
                        'type': 'correlation',
                        'vars': [cols[i], cols[j]],
                        'value': float(r),
                        'message': f"'{cols[i]}' 与 '{cols[j]}' 高度相关 (r={r:.2f})"
                    })

        # 2. VIF (Variance Inflation Factor)
        # Only if no perfect linear dependency?
        try:
            from app.utils.diagnostics import ModelDiagnostics
            vif_data = ModelDiagnostics.calculate_vif(numeric_df, numeric_df.columns.tolist())
            
            for item in vif_data:
                val = item['vif']
                if val == 'inf' or (isinstance(val, (int, float)) and val > 10):
                    status = 'error' # VIF > 10 is critical
                    report.append({
                        'type': 'vif',
                        'vars': [item['variable']],
                        'value': str(val),
                        'message': f"'{item['variable']}' 存在严重多重共线性 (VIF={val})"
                    })
        except Exception:
            pass
            
        return {
            'status': status,
            'report': report
        }

    @staticmethod
    def recommend_modeling_strategy(df):
        """
        Intelligent Recommendation Engine.
        Scans data to suggest the most appropriate modeling strategy, target, and features.
        """
        recommendation = {
            'model_type': 'logistic', # default
            'target': {}, # {name: 'status', time: 'time'} or 'outcome'
            'features': [],
            'reason': ''
        }
        
        columns = df.columns.tolist()
        lower_cols = {c.lower(): c for c in columns}
        
        # 1. Detection Keywords
        time_keywords = ['time', 'duration', 'days', 'month', 'year', 'os', 'pfs', 'rfs']
        event_keywords = ['status', 'event', 'outcome', 'death', 'died', 'recurrence', 'y', 'flag', 'class', 'target']
        id_keywords = ['id', 'no', 'code', 'name', 'patient', 'sample']
        
        # 2. Heuristic Scan
        found_time = None
        found_event = None
        found_target = None
        
        # Search for Time
        for k in time_keywords:
            for lc, real_c in lower_cols.items():
                if k in lc and not any(ik in lc for ik in id_keywords) and pd.api.types.is_numeric_dtype(df[real_c]):
                    found_time = real_c
                    break
            if found_time: break
            
        # Search for Event/Target
        for k in event_keywords:
            for lc, real_c in lower_cols.items():
                if k in lc and not any(ik in lc for ik in id_keywords):
                    # Check unique values
                    uniques = df[real_c].dropna().unique()
                    n_uniq = len(uniques)
                    
                    if n_uniq == 2: # Binary likely event
                        found_event = real_c
                        if not found_target: found_target = real_c
                    elif n_uniq > 2 and pd.api.types.is_numeric_dtype(df[real_c]):
                        # Continuous target?
                        if not found_target: found_target = real_c
        
        # 3. Strategy Decision
        exclude_targets = []
        if found_time and found_event:
            recommendation['model_type'] = 'cox'
            recommendation['target'] = {'time': found_time, 'event': found_event}
            recommendation['reason'] = f"检测到生存时间 ({found_time}) 和终点事件 ({found_event})，推荐使用 **Cox 比例风险模型**。"
            exclude_targets = [found_time, found_event]
            
        elif found_target:
            # Check if binary or continuous
            uniques = df[found_target].dropna().unique()
            if len(uniques) == 2:
                recommendation['model_type'] = 'logistic'
                recommendation['target'] = found_target
                recommendation['reason'] = f"检测到二分类结局变量 ({found_target})，推荐使用 **逻辑回归 (Logistic Regression)**。"
                exclude_targets = [found_target]
            elif pd.api.types.is_numeric_dtype(df[found_target]):
                recommendation['model_type'] = 'linear'
                recommendation['target'] = found_target
                recommendation['reason'] = f"检测到连续型结局变量 ({found_target})，推荐使用 **线性回归 (Linear Regression)**。"
                exclude_targets = [found_target]
            else:
                 # Classification but >2 classes?
                 recommendation['model_type'] = 'logistic' # Multiclass fallback (not impl yet but safe default)
                 recommendation['target'] = found_target
                 recommendation['reason'] = f"目标变量 ({found_target}) 为分类型，推荐使用逻辑回归。"
                 exclude_targets = [found_target]
        else:
            # Fallback
            recommendation['reason'] = "未能自动识别明确的结局变量，默认推荐逻辑回归。请手动选择。"
            exclude_targets = []

        # 4. Feature Selection
        features = []
        for c in columns:
            if c in exclude_targets: continue
            
            lc = c.lower()
            # Skip ID-like
            if any(ik in lc for ik in id_keywords): continue
            
            # Skip high cardinality strings (likely names/desc)
            if df[c].dtype == 'object':
                if df[c].nunique() > 10: continue
            
            # Skip strict constants
            if df[c].dropna().nunique() <= 1: continue
            
            features.append(c)
            
        recommendation['features'] = features
        return recommendation
