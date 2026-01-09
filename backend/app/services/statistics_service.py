
import pandas as pd
import numpy as np
from scipy import stats
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from app.utils.formatter import ResultFormatter

class StatisticsService:
    @staticmethod
    def generate_table_one(df, group_by, variables):
        """
        Generates Table 1 statistics.
        :param df: DataFrame
        :param group_by: Column name to group by (optional)
        :param variables: List of variable names to analyze
        :return: List of rows for Table 1
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
        
        for var in variables:
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
            
            # 2. Group Stats & P-value
            if group_by:
                group_stats = {}
                group_data = [] # List of array-likes for hypothesis test
                
                for g in groups:
                    sub_df = df[df[group_by] == g]
                    group_stats[str(g)] = StatisticsService._calc_stats(sub_df[var])
                    group_data.append(sub_df[var].dropna())
                    
                row['groups'] = group_stats
                
                # Hypothesis Test
                if row['type'] == 'numeric':
                    try:
                        if len(groups) == 2:
                            # Independent T-test
                            stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=False) # Welch's T-test
                            row['test'] = 'Welch T-test'
                        else:
                            # ANOVA
                            stat, p = stats.f_oneway(*group_data)
                            row['test'] = 'ANOVA'
                    except Exception:
                        p = None
                        row['test'] = 'Error'
                        
                else:
                    # Categorical: Chi-square
                    ct = pd.crosstab(df[var], df[group_by])
                    try:
                        stat, p, dof, expected = stats.chi2_contingency(ct)
                        row['test'] = 'Chi-square'
                    except Exception:
                        p = None
                        row['test'] = 'Error'

                row['p_value'] = ResultFormatter.format_p_value(p) if p is not None else 'N/A'
                
            results.append(row)
            
        return results

    @staticmethod
    def _calc_stats(series):
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
            
            return {
                'n': int(n),
                'missing': int(missing),
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
                
            return {
                'n': int(n),
                'missing': int(missing),
                'counts': formatted
            }

    @staticmethod
    def generate_km_data(df, time_col, event_col, group_col=None):
        """
        Generates Kaplan-Meier survival curves data.
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
                # multivariate_logrank_test(event_durations, groups, event_observed)
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
            
        return {
            'plot_data': plot_data,
            'p_value': p_value
        }

    @staticmethod
    def perform_psm(df, treatment, covariates):
        """
        Performs Propensity Score Matching.
        1. Logistic Regression for PS.
        2. NN Matching (1:1).
        3. Returns matched indices and balance stats.
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
