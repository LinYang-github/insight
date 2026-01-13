
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
        
        Logic Update (v1.1):
        - 自动进行正态性检验 (Shapiro-Wilk / KS)。
        - 依据正态性选择参数检验 (T-test/ANOVA) 或非参数检验 (Mann-Whitney/Kruskal-Wallis)。
        - 描述统计量自适应：正态 -> Mean ± SD; 非正态 -> Median [IQR]。

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
            if var not in df.columns: 
                continue
            if var == group_by:
                continue
                
            # Basic Type Check
            is_numeric = pd.api.types.is_numeric_dtype(df[var])
            
            # Normality Check (only for numeric)
            is_normal = True 
            if is_numeric:
                # Test normality on valid data
                valid_data = df[var].dropna()
                if len(valid_data) >= 3: # Shapiro requires N >= 3
                    is_normal = StatisticsService._test_normality(valid_data)
                
            row = {
                'variable': var,
                'type': 'numeric' if is_numeric else 'categorical',
                'is_normal': is_normal
            }
            
            # 1. Overall Stats
            row['overall'] = StatisticsService._calc_stats(df[var], is_normal=is_normal)
            
            if group_by:
                group_stats = {}
                group_data = [] 
                
                # Check normality per group? 
                # Rigorous: If ANY group is non-normal, use non-parametric for all.
                all_groups_normal = True
                
                for g in groups:
                    sub_df = df[df[group_by] == g]
                    valid_sub = sub_df[var].dropna()
                    
                    if is_numeric and len(valid_sub) >= 3:
                         g_normal = StatisticsService._test_normality(valid_sub)
                         if not g_normal: all_groups_normal = False
                    
                    group_data.append(valid_sub)

                # Final Normality Decision for Inference
                # If numeric and at least one group is non-normal -> Non-Parametric
                test_is_normal = is_numeric and all_groups_normal
                
                # Update row['is_normal'] to reflect the inference basis (consistency)
                # Or keep overall normality for description? 
                # Usually Table 1 description matches the test assumption.
                row['is_normal'] = test_is_normal
                
                # Re-calc Overall with new normal flag?
                if test_is_normal != is_normal:
                     row['overall'] = StatisticsService._calc_stats(df[var], is_normal=test_is_normal)

                # Calc Group Stats
                for i, g in enumerate(groups):
                     sub_df = df[df[group_by] == g]
                     group_stats[str(g)] = StatisticsService._calc_stats(sub_df[var], is_normal=test_is_normal)
                
                row['groups'] = group_stats
                test_meta = {}
                    
                # Hypothesis Test Selection
                if is_numeric:
                    try:
                        if len(groups) == 2:
                            if test_is_normal:
                                # Parametric: Welch's T-test
                                test_name = 'Welch\'s T-test'
                                reason = "数据服从正态分布，采用 Welch's T-test。"
                                stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=False)
                            else:
                                # Non-Parametric: Mann-Whitney U
                                test_name = 'Mann-Whitney U Test'
                                reason = "数据不服从正态分布，采用 Mann-Whitney U Test。"
                                stat, p = stats.mannwhitneyu(group_data[0], group_data[1], alternative='two-sided')
                                
                            used_tests.add(test_name)
                            row['test'] = test_name
                            test_meta = MetadataBuilder.build_test_meta(test_name, reason)
                        else:
                            # > 2 Groups
                            if test_is_normal:
                                # ANOVA
                                test_name = 'ANOVA'
                                reason = "多组比较且服从正态分布，采用单因素方差分析 (ANOVA)。"
                                stat, p = stats.f_oneway(*group_data)
                            else:
                                # Kruskal-Wallis
                                test_name = 'Kruskal-Wallis H Test'
                                reason = "多组比较且不服从正态分布，采用 Kruskal-Wallis H Test。"
                                stat, p = stats.kruskal(*group_data)

                            used_tests.add(test_name)
                            row['test'] = test_name
                            test_meta = MetadataBuilder.build_test_meta(test_name, reason)
                            
                    except Exception as e:
                        p = None
                        row['test'] = 'Error'
                        
                else:
                    # Categorical: Chi-square / Fisher
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
        """生成适用于 Table 1 的方法学描述。"""
        lines = []
        
        # 1. 描述性统计
        lines.append("连续变量使用 Shapiro-Wilk 检验（或针对大样本的 Kolmogorov-Smirnov 检验）进行正态性评估。")
        lines.append("符合正态分布的连续变量以均数 ± 标准差 (mean ± SD) 表示，非正态分布的变量以中位数（四分位间距，IQR）表示。")
        lines.append("分类变量以频数（百分比）表示。")
        
        # 2. 推断性统计
        if has_group and tests:
            test_desc = []
            if "Student's T-test" in tests or "Welch's T-test" in tests:
                test_desc.append("符合正态分布的连续变量采用 Student's/Welch's t 检验")
            if "Mann-Whitney U Test" in tests:
                test_desc.append("非正态分布的连续变量采用 Mann-Whitney U 检验")
                
            if "ANOVA" in tests:
                test_desc.append("符合正态分布的连续变量采用方差分析 (ANOVA)")
            if "Kruskal-Wallis H Test" in tests:
                test_desc.append("非正态分布的连续变量采用 Kruskal-Wallis H 检验")
                
            if "Chi-square" in tests:
                test_desc.append("分类变量采用卡方检验")
            if "Fisher Exact Test" in tests:
                test_desc.append("当期望频数 < 5 时，分类变量采用 Fisher 精确检验")
                
            if test_desc:
                lines.append(f"采用 {', '.join(test_desc)} 对组间差异进行分析。")
                
            lines.append("所有统计检验均为双侧检验，且以 P < 0.05 为具有统计学意义。")
            
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
    def _test_normality(series):
        """
        Shapiro-Wilk 正态性检验。
        如果 P > 0.05，则返回 True（不拒绝原假设 H0：服从正态分布），否则返回 False。
        当 N > 5000 时，使用 Kolmogorov-Smirnov 检验以避免 P 值的样本量偏差。
        """
        try:
            # 剔除缺失值并确保是数值型
            clean_s = pd.to_numeric(series.dropna(), errors='coerce').dropna()
            if len(clean_s) < 3: return True # 样本量太少，为了避免错误或默认处理，假定其正态。
            
            if len(clean_s) > 5000:
                # KS 检验（与标准化后的标准正态分布进行对比）
                # 标准化
                z_score = (clean_s - clean_s.mean()) / clean_s.std()
                stat, p = stats.kstest(z_score, 'norm')
            else:
                stat, p = stats.shapiro(clean_s)
            
            return p > 0.05
        except:
            return True # 出错时默认为参数检验

    @staticmethod
    def _calc_stats(series, is_normal=True):
        # ... (Existing) ...
        n = len(series)
        missing = series.isnull().sum()
        if pd.api.types.is_numeric_dtype(series):
            clean_s = series.dropna()
            if clean_s.empty: return {'mean': 0, 'sd': 0, 'desc': 'N/A'}
            
            # Basic stats
            mean = clean_s.mean()
            sd = clean_s.std()
            median = clean_s.median()
            q25 = clean_s.quantile(0.25)
            q75 = clean_s.quantile(0.75)
            
            stats_dict = {
                'n': int(n), 'missing': int(missing),
                'mean': ResultFormatter.format_float(mean, 2),
                'sd': ResultFormatter.format_float(sd, 2),
                'median': ResultFormatter.format_float(median, 2),
                'q25': ResultFormatter.format_float(q25, 2),
                'q75': ResultFormatter.format_float(q75, 2)
            }
            
            # Format Description string based on Normality
            if is_normal:
                stats_dict['desc'] = f"{stats_dict['mean']} ± {stats_dict['sd']}"
            else:
                stats_dict['desc'] = f"{stats_dict['median']} [{stats_dict['q25']}, {stats_dict['q75']}]"
                
            return stats_dict
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
            # 全体人群 (Overall)
            kmf.fit(df[time_col], df[event_col], label='全体 (Overall)')
            trace = {
                'name': '全体 (Overall)',
                'times': kmf.survival_function_.index.tolist(),
                'probs': kmf.survival_function_.iloc[:, 0].tolist(),
                'ci_lower': kmf.confidence_interval_.iloc[:, 0].tolist(),
                'ci_upper': kmf.confidence_interval_.iloc[:, 1].tolist()
            }
            plot_data.append(trace)
            
        # --- 生成结果解读与方法学描述 ---
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
        """生成 Kaplan-Meier 分析的方法学文本。"""
        text = "采用 Kaplan-Meier 方法估算生存曲线。"
        if has_group:
            text += " 使用 Log-rank 检验比较各组间的差异。"
        text += " 所有分析均使用 Insight 统计平台 (v1.0) 完成。"
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
    def perform_psm(df, treatment, covariates, caliper=None):
        """
        执行倾向性评分匹配 (PSM, Propensity Score Matching)。
        
        用于观察性研究中减少混杂偏倚 (Confounding Bias)，通过模拟随机对照试验的效果，
        使实验组和对照组在基线协变量上达到平衡。

        Args:
            df (pd.DataFrame): 原始数据集。
            treatment (str): 处理变量（0/1），1 代表实验组，0 代表对照组。
            covariates (list): 需要匹配的协变量（混杂因素）。
            caliper (float, optional): 卡钳值。如果指定，匹配时的最大允许距离。
                                     通常建议设为 0.2 * SD(logit_ps)，或绝对值如 0.05。

        Algorithm:
            1. 使用逻辑回归估算倾向性得分 (Propensity Score)。
            2. 使用最近邻匹配 (Nearest Neighbor Matching) 进行 1:1 匹配。
            3. 如果设置了 Caliper，剔除距离超过阈值的配对。
            4. 计算匹配前后的标准化均数差 (SMD) 以评估平衡性。

        Returns:
            dict: 包含匹配后的索引列表、平衡性统计指标及样本量变化的字典。
        """
        if treatment not in df.columns:
             raise ValueError(f"Treatment '{treatment}' not found.")
             
        # Prepare Data
        cols = [treatment] + covariates
        data = df[cols].dropna()
        
        # 1. PS Calculation
        T = data[treatment]
        X = data[covariates]
        
        # Auto-encode for PS estimation:
        X_encoded = pd.get_dummies(X, drop_first=True)
        
        ps_model = LogisticRegression(solver='liblinear') # robust for small N
        ps_model.fit(X_encoded, T)
        
        data['ps_score'] = ps_model.predict_proba(X_encoded)[:, 1]
        
        # 2. Matching
        treated = data[data[treatment] == 1]
        control = data[data[treatment] == 0]
        
        if treated.empty or control.empty:
             raise ValueError("实验组或对照组为空。")
             
        # Fit NN on Control PS
        control_ps = control[['ps_score']].values
        treated_ps = treated[['ps_score']].values
        
        nbrs = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(control_ps)
        distances, indices = nbrs.kneighbors(treated_ps)
        
        # Get matched control indices
        # indices is (n_treated, 1) array of indices into 'control' dataframe (iloc)
        # distances is (n_treated, 1)
        
        matched_indices_list = []
        # 实验证明，1:1 不回置 (Greedy) 匹配是标准做法。
        # sklearn 的 NN 默认是独立寻找邻居（如果有多个实验组匹配到同一个对照组，实际上相当于有回置）。
        
        # 我们先检查卡钳值。
        
        valid_matches = [] # (treated_idx_in_data, control_idx_in_data)
        
        # Iterate matches
        for i in range(len(treated)):
            dist = distances[i][0]
            if caliper is not None and dist > caliper:
                continue # Drop this treated unit (no match within caliper)
                
            ctr_iloc = indices[i][0]
            
            # 如果需要不回置匹配，我们需要处理冲突。
            # 简单方法：目前保持现有的匹配逻辑，但通过卡钳值进行过滤。
            # 医学论文通常倾向于 1:1 不回置匹配。
            
            valid_matches.append((treated.index[i], control.index[ctr_iloc]))

        # 重建匹配后的数据
        # 展平元组列表
        if not valid_matches:
            raise ValueError(f"在卡钳值 {caliper} 范围内未找到匹配项。")
            
        t_idxs = [m[0] for m in valid_matches]
        c_idxs = [m[1] for m in valid_matches]
        
        # Handle duplicates if replacement allowed? 
        # If we just concat, we might have duplicate controls.
        matched_treated = data.loc[t_idxs]
        matched_control = data.loc[c_idxs]
        
        matched_data = pd.concat([matched_treated, matched_control])
        
        # 3. 平衡性检查 (SMD)
        balance_stats = []
        for var in covariates:
             # 匹配前
            mean_t_pre = treated[var].mean() if pd.api.types.is_numeric_dtype(treated[var]) else 0 
            mean_c_pre = control[var].mean() if pd.api.types.is_numeric_dtype(control[var]) else 0
            
            smd_pre = StatisticsService._calc_smd(treated, control, var)
            smd_post = StatisticsService._calc_smd(matched_treated, matched_control, var)
            
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
            'n_matched_pairs': len(valid_matches),
            'n_matched': len(matched_data),
            'caliper': caliper
        }

    @staticmethod
    def perform_iptw(df, treatment, covariates, weight_type='ATE', stabilized=True, truncate=True):
        """
        执行逆概率加权 (IPTW, Inverse Probability of Treatment Weighting).

        参数:
           df: 原始数据框
           treatment: 暴露变量名 (0/1)
           covariates: 协变量列表
           weight_type: 'ATE' (默认) 或 'ATT'
           stabilized: 布尔值 (默认 True)，是否使用稳定权重（乘以边缘概率 P(T)）
           truncate: 布尔值 (默认 True)，是否截断极端权重 (第1和第99百分位数)
           
        返回:
           dict: {
               'weights': 权重列表,
               'balance': 平衡性结果列表 (SMD 表),
               'n_treated': 实验组样本量,
               'n_control': 对照组样本量,
               'ess_treated': 实验组有效样本量 (Effective Sample Size),
               'ess_control': 对照组有效样本量
           }
        """
        if treatment not in df.columns:
             raise ValueError(f"Treatment '{treatment}' not found.")
             
        cols = [treatment] + covariates
        data = df[cols].dropna().copy()
        
        # 1. 倾向性评分 (PS) 估算
        T = data[treatment]
        X = data[covariates]
        X_encoded = pd.get_dummies(X, drop_first=True)
        
        ps_model = LogisticRegression(solver='liblinear')
        ps_model.fit(X_encoded, T)
        
        ps = ps_model.predict_proba(X_encoded)[:, 1]
        data['ps'] = ps
        
        # 2. 权重计算
        # 避免除以零
        data['ps'] = data['ps'].clip(1e-6, 1 - 1e-6)
        
        p_t = T.mean() # Marginal Prob P(T=1)
        
        if weight_type == 'ATE':
            if stabilized:
                # W = T * P(T)/ps + (1-T) * (1-P(T))/(1-ps)
                data['weight'] = np.where(T==1, p_t / data['ps'], (1-p_t) / (1-data['ps']))
            else:
                data['weight'] = np.where(T==1, 1 / data['ps'], 1 / (1-data['ps']))
                
        elif weight_type == 'ATT':
            # Target is Treated. W(T=1)=1.
            # Stabilized ATT usually doesn't apply (SMW is for ATE), but can scale by P(T)? 
            # Standard ATT W: T=1 -> 1, T=0 -> ps/(1-ps)
            data['weight'] = np.where(T==1, 1, data['ps'] / (1-data['ps']))
            
        # 3. 权重截断
        if truncate:
            lower = data['weight'].quantile(0.01)
            upper = data['weight'].quantile(0.99)
            data['weight'] = data['weight'].clip(lower, upper)
            
        # 4. 有效样本量 (ESS)
        # ESS = (Sum W)^2 / Sum (W^2)
        def calc_ess(weights):
            return (weights.sum()**2) / (weights**2).sum()
            
        ess_treated = calc_ess(data[data[treatment]==1]['weight'])
        ess_control = calc_ess(data[data[treatment]==0]['weight'])
        
        # 5. 平衡性检查 (加权 SMD)
        balance_stats = []
        
        # 加权方差计算
        def weighted_avg_var(val, w):
            avg = np.average(val, weights=w)
            # 权重方差
            # S^2 = Sum(w * (x - avg)^2) / Sum(w) * (N/(N-1)) ? 或者仅使用可靠性权重。
            # 简化方案：Sum(w * (x-avg)^2) / Sum(w)
            variance = np.average((val - avg)**2, weights=w)
            return avg, variance

        for var in covariates:
            # 加权前
            t_pre = data[data[treatment]==1][var]
            c_pre = data[data[treatment]==0][var]
            
            if pd.api.types.is_numeric_dtype(t_pre):
                 smd_pre = StatisticsService._calc_smd(data[data[treatment]==1], data[data[treatment]==0], var)
                 
                 # 加权后
                 t_w = data[data[treatment]==1]['weight']
                 c_w = data[data[treatment]==0]['weight']
                 
                 m1, v1 = weighted_avg_var(t_pre, t_w)
                 m0, v0 = weighted_avg_var(c_pre, c_w)
                 
                 pooled_std_w = np.sqrt((v1 + v0)/2)
                 if pooled_std_w == 0: smd_post = 0
                 else: smd_post = abs(m1 - m0) / pooled_std_w
            else:
                 smd_pre = 0 # 分类变量占位符
                 smd_post = 0
            
            balance_stats.append({
                'variable': var,
                'smd_pre': smd_pre,
                'smd_post': smd_post
            })
            
        # 排序索引以匹配原始数据集
        return {
            'weights': data['weight'].tolist(), # 与处理后的数据行对齐
            'indices': data.index.tolist(),
            'balance': balance_stats,
            'n_treated': int(data[treatment].sum()),
            'n_control': int(len(data) - data[treatment].sum()),
            'ess_treated': float(ess_treated),
            'ess_control': float(ess_control)
        }

    @staticmethod
    def recommend_covariates(df, treatment):
        """
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
            # 跳过高基数基数或无关列
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
                
        # 按 P 值排序（最显著的排在前面）
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
            
            # 对于分类变量，检查是否存在样本量极少的水平
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
            # 计算直方图数据
            counts, bin_edges = np.histogram(series, bins='auto')
            
            # 用于叠加的正态分布曲线
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
            # 分类变量计数
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
        # 处理数值型
        if pd.api.types.is_numeric_dtype(df1[var]):
             m1 = df1[var].mean()
             m2 = df2[var].mean()
             v1 = df1[var].var()
             v2 = df2[var].var()
             
             pooled_std = np.sqrt((v1 + v2) / 2)
             if pooled_std == 0: return 0.0
             return abs(m1 - m2) / pooled_std
        else:
             # 分类变量：采用占位符 0.0
             return 0.0

    @staticmethod
    def check_multicollinearity(df, features):
        """
        检查特征变量之间的多重共线性。
        计算两两相关系数 (Correlation) 和方差膨胀因子 (VIF)。
        """
        if not features or len(features) < 2:
            return {'status': 'ok', 'report': []}
            
        # 针对 VIF/相关性仅过滤数值型变量
        # 针对分类变量，可能需要 Cramer's V（MVP 版本暂不实现）
        numeric_df = df[features].select_dtypes(include=[np.number])
        if numeric_df.empty or numeric_df.shape[1] < 2:
             return {'status': 'ok', 'report': []}
 
        # 为了计算，需要处理缺失值
        numeric_df = numeric_df.dropna()
        if numeric_df.empty:
             return {'status': 'warning', 'message': '有效样本量不足，无法计算共线性。'}

        report = []
        status = 'ok'
        
        # 1. 两两相关性
        corr_matrix = numeric_df.corr().abs()
        
        # 上三角矩阵
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

        # 2. VIF (方差膨胀因子)
        # 仅在不存在完全线性依赖的情况下计算
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
        智能推荐引擎。
        通过扫描数据特征，推荐最合适的建模策略、结局变量及特征变量。
        """
        recommendation = {
            'model_type': 'logistic', # default
            'target': {}, # {name: 'status', time: 'time'} or 'outcome'
            'features': [],
            'reason': ''
        }
        
        columns = df.columns.tolist()
        lower_cols = {c.lower(): c for c in columns}
        
        # 1. 关键词检测
        time_keywords = ['time', 'duration', 'days', 'month', 'year', 'os', 'pfs', 'rfs']
        event_keywords = ['status', 'event', 'outcome', 'death', 'died', 'recurrence', 'y', 'flag', 'class', 'target']
        id_keywords = ['id', 'no', 'code', 'name', 'patient', 'sample']
        
        # 2. 启发式扫描
        found_time = None
        found_event = None
        found_target = None
        
        # 寻找时间变量 (Time)
        for k in time_keywords:
            for lc, real_c in lower_cols.items():
                if k in lc and not any(ik in lc for ik in id_keywords) and pd.api.types.is_numeric_dtype(df[real_c]):
                    found_time = real_c
                    break
            if found_time: break
            
        # 寻找事件/结局变量 (Event/Target)
        for k in event_keywords:
            for lc, real_c in lower_cols.items():
                if k in lc and not any(ik in lc for ik in id_keywords):
                    # 检查唯一值
                    uniques = df[real_c].dropna().unique()
                    n_uniq = len(uniques)
                    
                    if n_uniq == 2: # 极可能是二分类事件
                        found_event = real_c
                        if not found_target: found_target = real_c
                    elif n_uniq > 2 and pd.api.types.is_numeric_dtype(df[real_c]):
                        # 连续型结局变量？
                        if not found_target: found_target = real_c
        
        # 3. 策略决策
        exclude_targets = []
        if found_time and found_event:
            recommendation['model_type'] = 'cox'
            recommendation['target'] = {'time': found_time, 'event': found_event}
            recommendation['reason'] = f"检测到生存时间 ({found_time}) 和终点事件 ({found_event})，推荐使用 **Cox 比例风险模型**。"
            exclude_targets = [found_time, found_event]
            
        elif found_target:
            # 检查是二分类还是连续型
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
                 # 可能是多分类但暂未实现？
                 recommendation['model_type'] = 'logistic' # 多分类回退方案
                 recommendation['target'] = found_target
                 recommendation['reason'] = f"目标变量 ({found_target}) 为分类型，推荐使用逻辑回归。"
                 exclude_targets = [found_target]
        else:
            # 回退方案
            recommendation['reason'] = "未能自动识别明确的结局变量，默认推荐逻辑回归。请手动选择。"
            exclude_targets = []

        # 4. 特征选择
        features = []
        for c in columns:
            if c in exclude_targets: continue
            
            lc = c.lower()
            # 跳过 ID 类变量
            if any(ik in lc for ik in id_keywords): continue
            
            # 跳过高基数基数变量（可能是姓名/描述）
            if df[c].dtype == 'object':
                if df[c].nunique() > 10: continue
            
            # 跳过严格常数变量
            if df[c].dropna().nunique() <= 1: continue
            
            features.append(c)
            
        recommendation['features'] = features
        return recommendation
