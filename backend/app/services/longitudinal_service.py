import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from app.utils.formatter import ResultFormatter

class LongitudinalService:
    @staticmethod
    def fit_lmm(df, id_col, time_col, outcome_col, fixed_effects=[], random_slope=True):
        """
        Fit Linear Mixed Model (LMM).
        Formula: outcome ~ time + fixed_effects + (1 + time | id)
        """
        df_clean = df.dropna(subset=[id_col, time_col, outcome_col] + fixed_effects)
        
        # Formula Construction
        # Fixed effects: time + covariates
        fe_terms = [time_col] + fixed_effects
        formula = f"{outcome_col} ~ {' + '.join(fe_terms)}"
        
        try:
            # Fit Model
            # re_formula='~time_col' means random slope on time
            # re_formula='1' means random intercept only
            re_formula = f"~{time_col}" if random_slope else "1"
            
            model = smf.mixedlm(formula, df_clean, groups=df_clean[id_col], re_formula=re_formula)
            result = model.fit()
            
            # Extract Results
            summary = []
            # Fixed Effects
            for name, val in result.params.items():
                if name == 'Group Var': continue # Skip variance params for summary table usually
                
                row = {
                    'variable': name,
                    'coef': val,
                    'stderr': result.bse.get(name),
                    'z': result.tvalues.get(name),
                    'p_value': result.pvalues.get(name),
                    'ci_lower': result.conf_int().loc[name][0],
                    'ci_upper': result.conf_int().loc[name][1]
                }
                summary.append(row)
                
            # Random Effects (Individual Slopes/Intercepts)
            # result.random_effects is a dict of {id: pd.Series}
            # We want to extract slope (time coef) for each ID if available
            random_effects = []
            
            # Identify the names in random effects
            # Usually: Group (Intercept), time_col
            re_names = result.random_effects[list(result.random_effects.keys())[0]].index.tolist()
            
            for pid, eff in result.random_effects.items():
                # Base estimates (Fixed + Random)
                # Intercept for ID = Fixed_Intercept + Random_Intercept
                # Slope for ID = Fixed_Slope + Random_Slope
                
                # Careful: params keys might differ from re_names
                intercept_fixed = result.params['Intercept']
                slope_fixed = result.params[time_col] if time_col in result.params else 0
                
                r_int = eff.get('Group', 0) # Statsmodels often names random intercept 'Group'
                r_slope = eff.get(time_col, 0)
                
                est_intercept = intercept_fixed + r_int
                est_slope = slope_fixed + r_slope
                
                random_effects.append({
                    'id': str(pid),
                    'random_intercept': float(r_int),
                    'random_slope': float(r_slope),
                    'total_intercept': float(est_intercept),
                    'total_slope': float(est_slope)
                })
                
            return {
                'summary': summary,
                'random_effects': random_effects,
                'aic': result.aic,
                'bic': result.bic,
                'converged': result.converged,
                'methodology': LongitudinalService._generate_lmm_methodology(fixed_effects, random_slope)
            }
            
        except Exception as e:
            raise ValueError(f"LMM fitting failed: {str(e)}")

    @staticmethod
    def _generate_lmm_methodology(fixed_effects, random_slope):
        re_text = "random intercepts and slopes" if random_slope else "random intercepts"
        fe_text = f" Fixed effects included {', '.join(['Time'] + fixed_effects)}."
        return (f"Linear mixed-effects models (LMM) were fitted with {re_text} to account for within-subject correlations."
                f"{fe_text} The models were estimated using Maximum Likelihood (ML) or REML.")

    @staticmethod
    def cluster_trajectories(df, id_col, time_col, outcome_col, n_clusters=3):
        """
        Trajectory Latent Class Analysis (Simplified via K-Means on Slopes).
        1. Calculate OLS slope for each ID.
        2. Cluster IDs based on (Intercept, Slope).
        """
        ids = df[id_col].unique()
        params_list = []
        
        # 1. Individual OLS
        for pid in ids:
            sub = df[df[id_col] == pid].dropna(subset=[time_col, outcome_col])
            if len(sub) < 2: continue # Need at least 2 points
            
            # Simple linear fit: outcome = a + b*time
            # polyfit is fast
            slope, intercept = np.polyfit(sub[time_col], sub[outcome_col], 1)
            params_list.append({
                'id': str(pid),
                'slope': slope,
                'intercept': intercept
            })
            
        if not params_list:
            raise ValueError("Not enough data to fit individual trajectories.")
            
        params_df = pd.DataFrame(params_list)
        
        # 2. Clustering
        X = params_df[['intercept', 'slope']].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        params_df['cluster'] = labels
        
        # 3. Analyze Clusters (Label them by Slope: Rapid Decline, Stable, etc.)
        # Calculate mean slope per cluster to order them or name them
        cluster_stats = params_df.groupby('cluster')['slope'].mean().reset_index()
        cluster_stats = cluster_stats.sort_values('slope') # Ascending slope (e.g. -5, -1, 0)
        
        # Map intuitive names? 
        # Lowest slope = "Rapid Decline" (if outcome is eGFR)
        # Highest slope = "Stable/Improve"
        # Let's just return stats and let frontend label or use Cluster 1, 2, 3 ordered.
        
        # Re-map labels so 0 is worst, N is best? Or just returned ordered list
        order_map = { row.cluster: i for i, row in enumerate(cluster_stats.itertuples()) }
        params_df['cluster_ordered'] = params_df['cluster'].map(order_map)
        
        return {
            'clusters': params_df.to_dict(orient='records'),
            'centroids': cluster_stats.to_dict(orient='records'),
            'methodology': LongitudinalService._generate_clustering_methodology(n_clusters)
        }

    @staticmethod
    def _generate_clustering_methodology(n_clusters):
        return (f"Trajectory clustering was performed using a two-step approach: 1) Individual slopes and intercepts were estimated using linear regression. "
                f"2) K-means clustering (k={n_clusters}) was applied to these features to identify distinct trajectory patterns.")

    @staticmethod
    def calculate_variability(df, id_col, outcome_col):
        """
        Calculate Visit-to-Visit Variability (VVV).
        SD, CV, VIM, ARV.
        """
        results = []
        
        for pid, sub in df.groupby(id_col):
            vals = sub[outcome_col].dropna()
            if len(vals) < 2: continue
            
            mean_val = vals.mean()
            sd = vals.std()
            cv = (sd / mean_val) * 100 if mean_val != 0 else 0
            
            # ARV (Average Real Variability): Average of absolute differences between consecutive readings
            # ARV = sum(|x_{i+1} - x_i|) / (N-1)
            diffs = np.abs(np.diff(vals))
            arv = np.mean(diffs)
            
            # VIM (Variability Independent of Mean)
            # VIM = k * SD / Mean^beta
            # beta is derived from population: slope of ln(SD) vs ln(Mean) plot
            # For individual calculation, simple formula VIM? Usually requires population beta.
            # We will return SD, CV, ARV first.
            # VIM requires 2-pass (calculate beta first).
            
            results.append({
                'id': str(pid),
                'n_visits': len(vals),
                'mean': float(mean_val),
                'sd': float(sd),
                'cv': float(cv),
                'arv': float(arv)
            })
            
        return {
            'variability_data': results,
            'methodology': LongitudinalService._generate_variability_methodology()
        }

    @staticmethod
    def _generate_variability_methodology():
        return ("Visit-to-visit variability (VVV) was assessed using standard deviation (SD), coefficient of variation (CV), and average real variability (ARV). "
                "These metrics capture different aspects of fluctuation independent of the mean level.")
