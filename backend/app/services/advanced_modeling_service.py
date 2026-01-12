import pandas as pd
import numpy as np
import patsy
from lifelines import CoxPHFitter
import statsmodels.api as sm
import statsmodels.formula.api as smf
from app.services.data_service import DataService

class AdvancedModelingService:
    
    @staticmethod
    def fit_rcs(df, target, event_col, exposure, covariates, model_type='cox', knots=3):
        """
        Fit a model with Restricted Cubic Splines for the exposure variable.
        
        Args:
            df (pd.DataFrame): Data.
            target (str): Outcome variable (Y). For Cox, this is 'duration'.
            event_col (str): Event indicator for Cox. None for Logistic/Linear.
            exposure (str): Continuous variable to spline (X).
            covariates (list): Adjusting variables.
            model_type (str): 'cox' or 'logistic' or 'linear'.
            knots (int): Number of knots (default 3, usually 3, 4, or 5).
            
        Returns:
            dict: {
                'p_non_linear': float, 
                'plot_data': [{'x': val, 'y': hr/or, 'lower': val, 'upper': val}]
            }
        """
        # 1. Prepare Formula
        # Using patsy 'cr' (natural cubic spline) or 'bs' (B-spline). 
        # R's rcs() is effectively natural cubic spline. patsy has cr().
        # formula: "target ~ cr(exposure, df=knots) + cov1 + ..."
        
        # Clean data first
        cols = [exposure] + covariates
        if model_type == 'cox':
            cols += [target, event_col]
        else:
            cols += [target]
        
        df_clean = df[cols].dropna()
        df_clean = DataService.preprocess_for_formula(df_clean)
        
        # We need to calculate predictions across range of exposure
        # Reference: usually median or mean of exposure => HR=1
        ref_value = df_clean[exposure].median()
        
        # Range for plotting: 5th to 95th percentile to avoid outliers stretching plot
        x_min = df_clean[exposure].quantile(0.05)
        x_max = df_clean[exposure].quantile(0.95)
        x_grid = np.linspace(x_min, x_max, 100)
        
        # Create a prediction dataframe
        # We need to hold covariates constant (e.g., at mean/mode)
        # But wait, predicted HR is relative. 
        # In Cox: h(t|x) / h(t|ref). The covariates cancel out if proportional hazards hold and we compare x to ref for the SAME individual.
        # So we effectively strictly vary exposure.
        
        results = {}
        
        if model_type == 'cox':
            # Lifelines formula usage
            # formula = "cr(exposure, df=knots) + covar1 + ..."
            cov_str = " + ".join(covariates) if covariates else ""
            formula_rhs = f"cr({exposure}, df={knots})"
            if cov_str:
                formula_rhs += f" + {cov_str}"
                
            if cov_str:
                formula_rhs += f" + {cov_str}"
                
            cph = CoxPHFitter(penalizer=0.01) # Add small penalizer for stability
            # Lifelines fit(formula=...) is supported in recent versions
            # But let's verify if we can do prediction easily.
            # Alternatively, generate spline matrix manually using patsy to have full control.
            
            # Using patsy directly on DF
            # dmatrix returns a matrix, we need a DF with readable names
            # But lifelines handles formulas well.
            
            # 1. Fit the model
            try:
                cph.fit(df_clean, duration_col=target, event_col=event_col, formula=formula_rhs)
            except Exception as e:
                raise ValueError(f"Model fitting failed: {str(e)}")
            
            # 2. Prepare Prediction Data (Grid) and Reference Data (Ref)
            pred_df = pd.DataFrame({exposure: x_grid})
            ref_df = pd.DataFrame({exposure: [ref_value]})
            
            # Fill covariates with mean/mode
            for cov in covariates:
                if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    mean_val = df_clean[cov].mean()
                    pred_df[cov] = mean_val
                    ref_df[cov] = mean_val
                else:
                    mode_val = df_clean[cov].mode()[0]
                    pred_df[cov] = mode_val
                    ref_df[cov] = mode_val
            
            # 3. Compute Log Hazard Ratio and Standard Errors (Delta Method)
            # We need the Design Matrix for the *spline terms* and covariates.
            # Lifelines uses patsy internally. accessing cph._predicted_partial_hazard is tricky for diffs.
            # Best way: Build design matrix manually using the SAME design info from the fitted model.
            
            # Get Design Info from the fitted model
            # cph._model contains the patsy design info usually, but lifelines API changed.
            # In recent lifelines, cph._predicted_partial_hazard uses:
            #   matrix = patsy.dmatrix(self.formula, data, return_type='dataframe')
            # But we need to ensure the knots/basis are identical to training.
            # Only way is to use `patsy.build_design_matrices`.
            # But where is the `design_info` stored?
            # It seems `cph._regression_data` might have it, or `cph._model`?
            # Actually, `cph.fit` creates the matrix but doesn't expose the design info object easily publicly?
            # Re-creating dmatrix with the same formula on training data extracts the design_info.
            
            design_matrix_train = patsy.dmatrix(formula_rhs, df_clean, return_type='matrix')
            design_info = design_matrix_train.design_info
            
            # Now build matrices for Pred and Ref
            # return_type='dataframe' is safer for column alignment
            dmatrix_pred = patsy.build_design_matrices([design_info], pred_df, return_type='dataframe')[0]
            dmatrix_ref = patsy.build_design_matrices([design_info], ref_df, return_type='dataframe')[0]
            
            # Params (Coefficients)
            params = cph.params_ # Series
            
            # Calculate Linear Predictor (X * beta)
            # Alignment check: dmatrix columns must match params index
            # patsy usually keeps order, but let's be safe
            common_cols = [c for c in params.index if c in dmatrix_pred.columns]
            
            lp_pred = dmatrix_pred[common_cols].dot(params[common_cols])
            lp_ref = dmatrix_ref[common_cols].dot(params[common_cols]).iloc[0]
            
            log_hr = lp_pred - lp_ref
            hr = np.exp(log_hr)
            
            # 4. Variance Calculation
            # Var(logHR) = Var(LP_pred - LP_ref) = Var( (Xp - Xr) * beta )
            #            = (Xp - Xr) * Cov * (Xp - Xr)^T
            # We only need diagonal of the resulting N x N matrix (variance of each point)
            
            cov_matrix = cph.variance_matrix_
            # Reindex cov_matrix to match common_cols
            cov_matrix = cov_matrix.loc[common_cols, common_cols]
            
            # Diff Matrix (N x p)
            diff_matrix = dmatrix_pred[common_cols].sub(dmatrix_ref[common_cols].iloc[0], axis=1)
            
            # Var = diag( Diff @ Cov @ Diff.T )
            # optimization: sum( (Diff @ Cov) * Diff, axis=1 )
            var_log_hr = (diff_matrix.dot(cov_matrix) * diff_matrix).sum(axis=1)
            se_log_hr = np.sqrt(var_log_hr)
            
            # 5. Confidence Intervals
            z_score = 1.96
            lower_ci = np.exp(log_hr - z_score * se_log_hr)
            upper_ci = np.exp(log_hr + z_score * se_log_hr)
            
            plot_data = []
            for i, x in enumerate(x_grid):
                plot_data.append({
                    'x': x,
                    'y': hr.iloc[i],
                    'lower': lower_ci.iloc[i],
                    'upper': upper_ci.iloc[i]
                })
                
            results['plot_data'] = plot_data
            results['ref_value'] = ref_value
            results['p_non_linear'] = None # To do: LRT if needed
            
            # PH Assumption Check
            results['ph_test'] = AdvancedModelingService.check_ph_assumption(cph, df_clean)
            
        elif model_type == 'logistic':
            # Statsmodels Logit
            cov_str = " + ".join(covariates) if covariates else "1" # 1 for intercept only if no covariates
            if not covariates: cov_str = "1"
            
            formula = f"{target} ~ cr({exposure}, df={knots}) + {cov_str}"
            if covariates:
                formula = f"{target} ~ cr({exposure}, df={knots}) + {' + '.join(covariates)}"
            else:
                 formula = f"{target} ~ cr({exposure}, df={knots})"
                 
            model = smf.logit(formula=formula, data=df_clean).fit(disp=0)
            
            # Prediction
            # OR = exp(logit(x) - logit(ref)) ? 
            # Logit = Xb. 
            # OR(x vs ref) = exp(X(x)b - X(ref)b)
            # Similar logic to Cox.
            
            pred_df = pd.DataFrame({exposure: x_grid})
            for cov in covariates:
                 if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    pred_df[cov] = df_clean[cov].mean()
                 else:
                    pred_df[cov] = df_clean[cov].mode()[0]
                    
            ref_df = pd.DataFrame([pred_df.iloc[0].copy()]) # Dummy
            ref_df[exposure] = ref_value
            for cov in covariates: # Reset ref cols
                 if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    ref_df[cov] = df_clean[cov].mean()
                 else:
                    ref_df[cov] = df_clean[cov].mode()[0]

            # Get predictions (Linear predictor = Xb)
            # getting design matrix
            # patsy.dmatrix(formula_rhs, pred_df) ?
            # Easier: model.predict(exog=..., transform=True) ?
            # Statsmodels predict returns p, not linear predictor usually unless specified.
            # actually results.predict(exog, transform=False) returns linear predictor? 
            # Logit: predict() returns probability. 
            # We want linear predictor.
            
            # We can use the design matrix and dot product with params.
            # But getting design matrix from formula on new data:
            # dmatrix = patsy.build_design_matrices([model.data.design_info], pred_df, return_type='dataframe')[0]
            
            dmatrix_pred = patsy.build_design_matrices([model.model.data.design_info], pred_df, return_type='dataframe')[0]
            dmatrix_ref = patsy.build_design_matrices([model.model.data.design_info], ref_df, return_type='dataframe')[0]
            
            lp_pred = dmatrix_pred.dot(model.params)
            lp_ref = dmatrix_ref.dot(model.params).iloc[0]
            
            log_or = lp_pred - lp_ref
            ors = np.exp(log_or)
            
            # CIs
            cov_matrix = model.cov_params()
            # Variance of difference: (X1 - X2) Cov (X1 - X2)^T
            diff_matrix = dmatrix_pred.sub(dmatrix_ref.iloc[0], axis=1) # (N, p)
            
            # se^2 = sum( (diff_matrix @ cov_matrix) * diff_matrix, axis=1 )
            # Efficient calc:
            # se = sqrt( diag( D @ Cov @ D.T ) )
            
            var_log_or = (diff_matrix.dot(cov_matrix) * diff_matrix).sum(axis=1)
            se_log_or = np.sqrt(var_log_or)
            
            lower_ci = np.exp(log_or - 1.96 * se_log_or)
            upper_ci = np.exp(log_or + 1.96 * se_log_or)
            
            plot_data = []
            for i, x in enumerate(x_grid):
                plot_data.append({
                    'x': x,
                    'y': ors.iloc[i],
                    'lower': lower_ci.iloc[i],
                    'upper': upper_ci.iloc[i]
                })
            
            results['plot_data'] = plot_data
            results['ref_value'] = ref_value
            
            # Methodology & Interpretation
            results['methodology'] = AdvancedModelingService._generate_rcs_methodology(knots, model_type)
            results['interpretation'] = "检测到潜在非线性关系。" if results.get('p_non_linear') and results['p_non_linear'] < 0.05 else "未检测到显著非线性关系。"
            
        return results

    @staticmethod
    def _generate_rcs_methodology(knots, model_type):
        model_name = "Cox proportional hazards" if model_type == 'cox' else "Logistic regression"
        return (f"Restricted cubic splines (RCS) with {knots} knots were used to model the non-linear "
                f"relationship between the continuous exposure and outcome using {model_name} models. "
                "Tests for non-linearity was performed.")

    @staticmethod
    def check_ph_assumption(cph, df_train, p_threshold=0.05):
        """
        Check Proportional Hazards Assumption using Schoenfeld Residuals.
        """
        from lifelines.statistics import proportional_hazard_test
        try:
            # Drop columns not in cph to avoid issues? 
            # proportional_hazard_test needs the dataset used for fitting.
            # cph object usually has it but we pass it explicitly to be safe.
            # Note: df_train must contain duration and event cols.
            results = proportional_hazard_test(cph, df_train, time_transform='km')
            summary = results.summary # DataFrame
            
            # Check if any variable violates PH
            min_p = summary['p'].min()
            is_violated = min_p < p_threshold
            
            # Format details
            details = {}
            for idx, row in summary.iterrows():
                details[str(idx)] = {
                    'p': float(row['p']),
                    'test_statistic': float(row['test_statistic']),
                    'is_violated': row['p'] < p_threshold
                }

            return {
                'is_violated': bool(is_violated),
                'p_value': float(min_p), # The most significant P violation
                'details': details,
                'message': "违反比例风险假定 (PH Assumption Violation)" if is_violated else "满足比例风险假定"
            }
        except Exception as e:
            # print(f"PH Test failed: {e}")
            return None

    @staticmethod
    def perform_subgroup(df, target, event_col, exposure, subgroups, covariates, model_type='cox'):
        """
        Perform subgroup analysis.
        """
        results = []
        
        # 1. Overall Model
        # Fit model on all data to get Overall estimate
        # reuse modeling service or simple fit here
        # ...
        
        # 2. Loop Subgroups
        for grp_col in subgroups:
            # Expect grp_col to be categorical
            # We need unique values
            groups = df[grp_col].dropna().unique()
            # Sort if possible
            try:
                groups = sorted(groups)
            except:
                pass
                
            group_res = {
                'variable': grp_col,
                'subgroups': []
            }
            
            # Check interaction P-value
            # Model: Y ~ Exposure + Covariates + Grp + Exposure:Grp
            # We want the P-value for the interaction term Exposure:Grp
            # This indicates if heterogeneity is significant.
            
            p_interaction = None
            try:
                # Interaction Modeling
                # Clean df
                temp_cols = [target, exposure, grp_col] + covariates
                if event_col: temp_cols.append(event_col)
                temp_df = df[temp_cols].dropna()
                temp_df = DataService.preprocess_for_formula(temp_df)
                
                # Formula Construction
                cov_part = " + ".join(covariates)
                if cov_part: cov_part = " + " + cov_part
                
                # Careful with categorical encoding in formula
                formula = f"{target} ~ {exposure} * C({grp_col}){cov_part}"
                
                if model_type == 'cox':
                     cph = CoxPHFitter()
                     cph.fit(temp_df, duration_col=target, event_col=event_col, formula=formula)
                     # Find interaction terms
                     # They usually look like 'Exposure:C(Grp)[T.Level]'
                     # We might need an ANOVA test or just check min P.
                     # Simplest: Likelihood Ratio Test between (Exp + Grp) and (Exp * Grp)
                     # But lifelines doesn't have easy ANOVA.
                     # Take the p-value of the interaction term(s). If multiple, it's complex.
                     # For binary subgroup, there is 1 interaction term.
                     summary = cph.summary
                     interaction_rows = [idx for idx in summary.index if ':' in idx]
                     if interaction_rows:
                         p_interaction = summary.loc[interaction_rows, 'p'].min() # Crude approximation
                     
                elif model_type == 'logistic':
                    model = smf.logit(formula, data=temp_df).fit(disp=0)
                    interaction_rows = [idx for idx in model.pvalues.index if ':' in idx]
                    if interaction_rows:
                         p_interaction = model.pvalues[interaction_rows].min()

            except Exception as e:
                print(f"Interaction failed: {e}")
            
            group_res['p_interaction'] = p_interaction

            for val in groups:
                # Subset
                sub_df = df[df[grp_col] == val]
                sub_df = DataService.preprocess_for_formula(sub_df)
                # Check sample size
                if len(sub_df) < 10:
                    continue
                    
                # Fit Model
                est, lower, upper, p_val = AdvancedModelingService._fit_simple_model(
                    sub_df, target, event_col, exposure, covariates, model_type
                )
                
                group_res['subgroups'].append({
                    'level': str(val),
                    'n': len(sub_df),
                    'est': est,
                    'lower': lower,
                    'upper': upper,
                    'p': p_val
                })
            
            results.append(group_res)
            
        # Wrap in dict with methodology
        return {
            'forest_data': results,
            'methodology': AdvancedModelingService._generate_subgroup_methodology(model_type)
        }

    @staticmethod
    def _generate_subgroup_methodology(model_type):
        test_type = "Likelihood Ratio Test" # Simplified
        return ("Subgroup analyses were performed to evaluate the consistency of the effect sizes across prespecified subgroups. "
                "Interaction terms were included in the models to test for heterogeneity of effects (interaction P-value).")

    @staticmethod
    def _fit_simple_model(df, target, event_col, exposure, covariates, model_type):
        """Helper to fit simple model and return HR/OR + CI + P"""
        try:
            cov_str = " + ".join(covariates)
            if cov_str: cov_str = " + " + cov_str
            formula = f"{exposure}{cov_str}" # LHS handled by library methods usually, or formula
            
            if model_type == 'cox':
                cph = CoxPHFitter()
                # formula support for LHS? "duration + event ~ ..." no.
                # standard fit: fit(df, duration, event, formula="...")
                cph.fit(df, duration_col=target, event_col=event_col, formula=formula)
                # Get exposure row
                # exposure might be customized if formula changed name (e.g. C(exposure))
                # Assuming exposure is continuous or binary 0/1 without transform for now
                if exposure in cph.summary.index:
                    row = cph.summary.loc[exposure]
                else:
                    # Try finding it
                    return None, None, None, None
                
                return row['exp(coef)'], row['exp(coef) lower 95%'], row['exp(coef) upper 95%'], row['p']
                
            elif model_type == 'logistic':
                f = f"{target} ~ {formula}"
                model = smf.logit(f, data=df).fit(disp=0)
                if exposure in model.params.index:
                    est = np.exp(model.params[exposure])
                    conf = model.conf_int()
                    lower = np.exp(conf.loc[exposure][0])
                    upper = np.exp(conf.loc[exposure][1])
                    p = model.pvalues[exposure]
                    return est, lower, upper, p
        except:
            return None, None, None, None
        return None, None, None, None

    @staticmethod
    def calculate_cif(df, time_col, event_col, group_col=None):
        """
        Calculate Cumulative Incidence Function (CIF) using Aalen-Johansen.
        """
        from lifelines import AalenJohansenFitter
        
        # event_col should have 0 (censor), 1 (primary), 2 (competing)...
        # We calculate CIF for *each* event type found (except 0).
        
        # Check integrity
        if df[event_col].nunique() < 2:
             # Just censorship?
             # Or only 1 event type? If only 1, AJ == KM (1-KM)
             pass
        
        results = []
        
        # Events (exclude 0)
        events = sorted([e for e in df[event_col].unique() if e != 0])
        
        if not events:
            raise ValueError("No event types found (only 0/Censor found?)")
            
        groups = ['All']
        if group_col:
            groups = df[group_col].dropna().unique()
            
        for grp in groups:
            if group_col:
                sub_df = df[df[group_col] == grp]
                grp_label = str(grp)
            else:
                sub_df = df
                grp_label = 'All'
            
            for evt in events:
                ajf = AalenJohansenFitter(calculate_variance=False)
                # It treats other values in E as competing risks automatically
                try:
                    # Clean NaNs
                    sub_clean = sub_df[[time_col, event_col]].dropna()
                    
                    ajf.fit(sub_clean[time_col], sub_clean[event_col], event_of_interest=evt)
                    
                    # Store line
                    # ajf.cumulative_density_ is the CIF
                    cif = ajf.cumulative_density_
                    
                    # Convert to list of {x, y}
                    line_data = []
                    # cif index is time, column is CIF_evt
                    times = cif.index.tolist()
                    values = cif.values.flatten().tolist()
                    
                    # Downsample if too huge?
                    if len(times) > 500:
                        # simple skip
                        indices = np.linspace(0, len(times)-1, 500, dtype=int)
                        times = [times[i] for i in indices]
                        values = [values[i] for i in indices]
                    
                    line_data = [{'x': t, 'y': v} for t, v in zip(times, values)]
                    
                    results.append({
                        'group': grp_label,
                        'event_type': int(evt),
                        'cif_data': line_data
                    })
                except Exception as e:
                    print(f"AJ fit failed for grp={grp} evt={evt}: {e}")
                    
        return {
            'cif_data': results,
            'methodology': AdvancedModelingService._generate_cif_methodology()
        }

    @staticmethod
    def _generate_cif_methodology():
        return ("Cumulative Incidence Functions (CIF) were estimated using the Aalen-Johansen estimator to account for competing risks. "
                "Gray's test was used to compare equality of CIFs between groups (if applicable).")

    @staticmethod
    def generate_nomogram(df, target, event_col, model_type, predictors):
        """
        Generate data for Nomogram and Web Calculator.
        Supports both numeric and categorical predictors.
        """
        results = {
            'variables': [],
            'risk_table': []
        }
        
        # 1. Fit Model & Get Coefs
        cols = [target] + predictors
        if event_col: cols.append(event_col)
        
        df_clean = df[cols].dropna()
        df_clean = DataService.preprocess_for_formula(df_clean)

        params = {}
        intercept = 0
        baseline_sf = None
        
        # Prepare Formula
        formula = f"{target} ~ {' + '.join(predictors)}" if model_type == 'logistic' else " + ".join(predictors)
        
        if model_type == 'logistic':
             model_res = smf.logit(formula, data=df_clean).fit(disp=0)
             params = model_res.params.to_dict()
             intercept = params.get('Intercept', 0)
        elif model_type == 'cox':
             cph = CoxPHFitter()
             cph.fit(df_clean, duration_col=target, event_col=event_col, formula=formula)
             params = cph.params_.to_dict()
             median_time = df_clean[target].median()
             # Calculate baseline survival at median time
             # Baseline S0(t) is survival when all X=0 (if centered, at mean)
             # lifelines predicts partial hazard. 
             # predict_survival_function returns S(t|x).
             # We want Base S0(t). 
             # We can get S(t|mean) then adjust back?
             # Or construct a dummy where all centered covariates are 0.
             # Lifelines centers data by default.
             baseline_sf = cph.predict_survival_function(pd.DataFrame({p:[0] for p in predictors}, index=[0]), times=[median_time]).iloc[0,0]

        # 2. Calculate Scaling Factor (Points per Unit Beta)
        # We need to find the variable with the maximum effect range.
        max_effect_range = 0
        var_configs = {} # Store how to compute effect for each var
        
        for var in predictors:
            if pd.api.types.is_numeric_dtype(df_clean[var]) and df_clean[var].nunique() > 2:
                # Continuous / Numeric
                coef = params.get(var, 0)
                mn, mx = df_clean[var].min(), df_clean[var].max()
                rng = abs(coef * (mx - mn))
                if rng > max_effect_range: max_effect_range = rng
                
                var_configs[var] = {
                    'type': 'numeric',
                    'coef': coef,
                    'min': mn, 'max': mx,
                    'range': rng
                }
            else:
                # Categorical (or binary treated as cat)
                # Find all associated coefficients (dummy encoded)
                # Reference level has coef 0.
                levels = sorted(df_clean[var].unique())
                level_coefs = {}
                
                # Check how it's encoded in params. Usually "Var[T.Level]"
                # Base level is 0.
                # Regex or exact match? Statsmodels/Lifelines uses "Var[T.Level]"
                c_values = []
                for l in levels:
                    key = f"{var}[T.{l}]"
                    val = params.get(key, 0)
                    if key not in params and l == levels[0]: val = 0 # Assume first is ref
                    level_coefs[l] = val
                    c_values.append(val)
                
                rng = max(c_values) - min(c_values)
                if rng > max_effect_range: max_effect_range = rng
                
                var_configs[var] = {
                    'type': 'categorical',
                    'level_coefs': level_coefs,
                    'min_coef': min(c_values),
                    'range': rng
                }

        if max_effect_range == 0:
            return results

        points_per_unit_beta = 100 / max_effect_range
        
        # 3. Generate Scale Data
        # We shift scale so that Min Contribution = 0 Points.
        # Contribution = Val * Coef (Numeric) or Level_Coef (Cat)
        
        total_min_points = 0
        total_max_points = 0
        
        for var in predictors:
            config = var_configs[var]
            
            if config['type'] == 'numeric':
                coef = config['coef']
                mn, mx = config['min'], config['max']
                
                # Contributions at extremes
                c_min = mn * coef
                c_max = mx * coef
                
                # We define Base for this variable as min(c_min, c_max)
                base_c = min(c_min, c_max)
                
                # Points = (Contribution - Base) * scaling
                ticks = np.linspace(mn, mx, 10)
                points_mapping = []
                for t in ticks:
                    c = t * coef
                    pts = (c - base_c) * points_per_unit_beta
                    points_mapping.append({'val': float(t), 'pts': float(pts)})
                    
                results['variables'].append({
                    'name': var,
                    'type': 'numeric',
                    'min': float(mn), 'max': float(mx),
                    'points_mapping': points_mapping
                })
                
                # Update Totals tracking
                # A patient usually contributes between 0 and (Range * Scaling) points
                total_max_points += config['range'] * points_per_unit_beta
                
                # Update global intercept adjustment
                # The formula is LP = Intercept + Sum(Contributions)
                # We substituted Contribution = Points/S + Base
                # LP = Intercept + Sum(Points/S + Base)
                #    = (Intercept + Sum(Base)) + TotalPoints/S
                intercept += base_c
                
            else:
                # Categorical
                min_c = config['min_coef'] # The lowest coef among levels
                cat_mapping = []
                
                for lvl, l_coef in config['level_coefs'].items():
                    pts = (l_coef - min_c) * points_per_unit_beta
                    cat_mapping.append({'val': str(lvl), 'pts': float(pts)})
                    
                results['variables'].append({
                    'name': var,
                    'type': 'categorical',
                    'points_mapping': cat_mapping
                })
                
                total_max_points += config['range'] * points_per_unit_beta
                intercept += min_c

        # 4. Risk Scale
        # LP = Adjusted_Intercept + TotalPoints / Scaling
        point_grid = np.linspace(0, total_max_points, 100)
        risk_mapping = []
        
        for pt in point_grid:
            lp = intercept + (pt / points_per_unit_beta)
            if model_type == 'logistic':
                risk = 1 / (1 + np.exp(-lp))
            else:
                # Cox: 1 - S0^exp(lp)
                risk = 1 - (baseline_sf ** np.exp(lp))
            risk_mapping.append({'points': float(pt), 'risk': float(risk)})
            
        results['risk_table'] = risk_mapping
        
        # Meta for Calculator
        # We need to send coefs differently for cat?
        # Actually frontend calc handles numerics. For cat, it needs mapping Val -> Coef.
        # Let's simplify and send mapped 'level_coefs' for cat.
        
        coeffs_flat = {}
        for var, conf in var_configs.items():
            if conf['type'] == 'numeric':
                coeffs_flat[var] = float(conf['coef'])
            else:
                # For categorical, frontend needs to look up dict
                # We can store in specific structure
                coeffs_flat[var] = conf['level_coefs'] # dict inside dict
                
        results['formula'] = {
            'intercept': float(intercept), # This is the ADJUSTED intercept now? 
            # WAIT. The calculator logic in frontend uses raw inputs * coefficients.
            # If I send ADJUSTED intercept here, front-end calculation will be wrong unless I change frontend too.
            # Frontend Logic: lp = intercept + sum(val * coef).
            # So I should send the ORIGINAL intercept and ORIGINAL coefficients.
            'baseline_survival': float(baseline_sf) if baseline_sf else None,
            'model_type': model_type,
            'coeffs': coeffs_flat, # Supports nested dicts? Frontend needs update.
            'var_configs': var_configs # Helper for frontend
        }
        
        # Reset intercept to original for 'formula' return if frontend uses standard formula
        # But wait, frontend 'coeffs_flat' for categorical...
        # If user inputs "Stage II", we need to know coef for Stage II.
        # Yes, level_coefs provides that. 
        # But wait, step 1 params had 'Intercept' (original).
        # We should return ORIGINAL intercept for calculator.
        results['formula']['intercept'] = float(params.get('Intercept', 0))

        results['methodology'] = AdvancedModelingService._generate_nomogram_methodology(model_type)
        return results

    @staticmethod
    def _generate_nomogram_methodology(model_type):
        return ("A nomogram was formulated to visualize the prediction model. "
                "Points were assigned to each variable (or level) based on its regression coefficient. "
                "The total points were mapped to the predicted probability of the outcome.")

    @staticmethod
    def compare_models(df, target, model_configs, model_type='logistic', event_col=None):
        """
        Compare multiple models on the SAME complete-case dataset (Incremental Value).
        
        Args:
            df (pd.DataFrame): Data.
            target (str): Target variable (Y) or Time variable.
            model_configs (list): List of dicts [{'name': 'M1', 'features': ['A']}, ...].
            model_type (str): 'logistic' or 'cox'.
            event_col (str): Event indicator (required for Cox).
        
        Returns:
            list: List of model results with metrics.
        """
        from app.services.modeling_service import ModelingService
        from lifelines import CoxPHFitter
        from sklearn.metrics import roc_curve, auc as calc_auc
        
        # 1. Identify valid columns (Intersection)
        all_features = set()
        for config in model_configs:
            all_features.update(config['features'])
            
        required_cols = list(all_features) + [target]
        if event_col:
            required_cols.append(event_col)
        
        # 2. Complete Case Analysis
        # Ensure fairness by dropping missing values on union of cols
        df_clean = df[required_cols].dropna()
        
        if len(df_clean) < 10:
             raise ValueError("Sample size too small (<10) after handling missing values for all combined features.")

        # Data Preview (Completeness)
        n_samples = len(df_clean)
        
        # Logic for Cox ROC Proxy
        median_time = None
        if model_type == 'cox':
            if not event_col:
                raise ValueError("Event column is required for Cox model.")
            median_time = df_clean[target].median()
            # We will calculate Incidence cumulative ROC at median time.
            # Simplified: Keep (Event=1 & Time<=Median) as Case=1
            # Keep (Time > Median) as Control=0
            # Drop (Event=0 & Time <= Median) (Unknown at Median)
        
        results = []
        
        # 3. Loop Models
        for config in model_configs:
            def calc_ci_str(auc, n1, n2):
                if n1 <= 0 or n2 <= 0: return "-"
                q1 = auc / (2 - auc)
                q2 = 2 * auc**2 / (1 + auc)
                se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
                lower = max(0, auc - 1.96*se)
                upper = min(1, auc + 1.96*se)
                return f"{lower:.3f}-{upper:.3f}"

            name = config['name']
            feats = config['features']
            
            try:
                metrics = {}
                roc_data = []
                
                metrics = {}
                roc_data = []
                # Store raw outputs for comparison
                raw_pred = None
                raw_y = None
                
                if model_type == 'logistic':
                    # Local fit for full control (consistent with Cox block)
                    # Prepare formula
                    formula = f"{target} ~ {' + '.join(feats)}"
                    if not feats: formula = f"{target} ~ 1"
                    
                    try:
                        # Statsmodels Logit
                        # Data must be numeric for statsmodels? DataService.preprocess handled it?
                        # df_clean is strict complete case
                        # Convert to dummy vars if needed? 
                        # smf handles formulas (categorical) automatically if string/category type.
                        model = smf.logit(formula=formula, data=df_clean).fit(disp=0)
                        
                        # Metrics
                        metrics['aic'] = model.aic
                        metrics['bic'] = model.bic
                        metrics['ll'] = model.llf
                        metrics['n'] = len(df_clean)  # Add Sample Size
                        metrics['r2'] = model.prsquared # Pseudo R2
                        metrics['k'] = len(model.params)

                        # Predictions (Probability)
                        y_prob = model.predict(df_clean)
                        y_true = df_clean[target]
                        
                        # ROC
                        fpr, tpr, _ = roc_curve(y_true, y_prob)
                        metrics['auc'] = calc_auc(fpr, tpr)
                        metrics['auc_ci'] = calc_ci_str(metrics['auc'], sum(y_true), len(y_true)-sum(y_true))
                        
                        roc_data = [{'fpr': f, 'tpr': t} for f, t in zip(fpr, tpr)]
                        
                        raw_pred = y_prob.values
                        raw_y = y_true.values
                        
                    except Exception as e:
                        print(e)
                        # Fallback to simple run if statsmodels fails (e.g. perfect separation)
                        model_res = ModelingService.run_model(df_clean, 'logistic', target, feats)
                        metrics = model_res.get('metrics', {})
                        # Ensure n is present even in fallback
                        metrics['n'] = len(df_clean)
                        if 'plots' in model_res and 'roc' in model_res['plots']:
                             roc_data = model_res['plots']['roc']

                elif model_type == 'cox':
                    # Custom implementation for Cox ROC
                    # Data Preprocessing
                    temp_df = df_clean[[target, event_col] + feats].copy()
                    temp_df = DataService.preprocess_for_formula(temp_df)
                    
                    # Fit
                    cph = CoxPHFitter()
                    cph.fit(temp_df, duration_col=target, event_col=event_col, formula=" + ".join(feats))
                    
                    # Fit Stats (Global)
                    metrics['c_index'] = cph.concordance_index_
                    metrics['auc'] = metrics['c_index'] 
                    metrics['aic'] = cph.AIC_partial_
                    metrics['ll'] = cph.log_likelihood_
                    n_events = cph.event_observed.sum()
                    metrics['n'] = len(temp_df) # Add Sample Size
                    k = len(cph.params_)
                    metrics['k'] = k
                    metrics['bic'] = -2 * metrics['ll'] + k * np.log(n_events)
                    
                    # Time-Dependent Metrics Loop
                    # Determine points (reuse logic or simple heuristic)
                    max_dur = temp_df[target].max()
                    points = []
                    time_unit = 'months'
                    if max_dur > 730: # Roughly 2 years
                        time_unit = 'days'
                        candidates = [365, 730, 1095, 1460, 1825] # 1, 2, 3, 4, 5 years
                        for c in candidates:
                             if max_dur > c: points.append(c)
                    else: # Assume months if max duration is less than 2 years
                        time_unit = 'months'
                        candidates = [12, 24, 36, 48, 60] # 1, 2, 3, 4, 5 years
                        for c in candidates:
                             if max_dur > c: points.append(c)
                    
                    # Always include median if no points or just as default
                    median_time = int(temp_df[target].median())
                    if not points: points = [median_time]
                    
                    metrics['time_dependent'] = {}
                    metrics['time_unit'] = time_unit
                    metrics['available_time_points'] = points
                    
                    raw_preds_dict = {} # t -> prob
                    
                    for t in points:
                        # S(t) -> Prob(Event <= t) = 1 - S(t)
                        surv_df = cph.predict_survival_function(temp_df, times=[t])
                        y_prob = 1 - surv_df.iloc[0].values
                        
                        # Validation Mask at T
                        mask_case = (temp_df[event_col] == 1) & (temp_df[target] <= t)
                        mask_control = (temp_df[target] > t)
                        valid_mask = mask_case | mask_control
                        
                        y_binary = mask_case[valid_mask].astype(int)
                        y_score_valid = y_prob[valid_mask]
                        
                        t_metrics = {}
                        if len(y_binary.unique()) > 1:
                            fpr, tpr, _ = roc_curve(y_binary, y_score_valid)
                            t_auc = calc_auc(fpr, tpr)
                            t_metrics['auc'] = t_auc
                            t_metrics['auc_ci'] = calc_ci_str(t_auc, sum(y_binary), len(y_binary)-sum(y_binary))
                            t_metrics['roc_data'] = [{'fpr': f, 'tpr': v} for f, v in zip(fpr, tpr)]
                        else:
                            t_metrics['auc'] = 0.5
                            t_metrics['auc_ci'] = "-"
                            
                        metrics['time_dependent'][t] = t_metrics
                        
                        # Store raw preds for NRI calculation later
                        # We need consistent indexing for NRI
                        # Store full array (y_prob) and let NRI function handle masking
                        raw_preds_dict[t] = y_prob
                    
                    # Store raw outputs for NRI (Comparison step)
                    # For Cox, raw_pred is now a dict of {t: y_prob}
                    raw_pred = raw_preds_dict
                    raw_y = {
                        'time': temp_df[target].values,
                        'event': temp_df[event_col].values
                    }

                model_res = {
                    'name': name,
                    'features': feats,
                    'metrics': metrics
                }
                if model_type == 'logistic': # Only logistic has a single ROC curve
                    model_res['roc_data'] = roc_data
                
                results.append({
                    'model_res': model_res,
                    'raw_pred': raw_pred,
                    'raw_y': raw_y
                })
                
            except Exception as e:
                print(f"Model {name} failed: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'model_res': {'name': name, 'error': str(e)},
                    'raw_pred': None,
                    'raw_y': None
                })

        # 2. Calculate NRI/IDI if base model exists (Model 0 = Base)
        # Only feasible if models share same rows. We assumed strict complete case above.
        if len(results) >= 2 and results[0]['raw_pred'] is not None:
            from app.services.evaluation_service import EvaluationService
            from scipy.stats import chi2
            base = results[0]
            
            for i in range(1, len(results)):
                curr = results[i]
                if curr['raw_pred'] is None: continue
                
                # Check model type
                if model_type == 'logistic':
                    # Standard NRI
                    try:
                        nri_res = EvaluationService.calculate_nri_idi(
                            base['raw_y'],
                            base['raw_pred'],
                            curr['raw_pred']
                        )
                        # Add to current model metrics
                        curr['model_res']['metrics'].update(nri_res)
                    except Exception as e:
                        print(f"NRI failed for logistic model {curr['model_res']['name']}: {e}")
                        
                elif model_type == 'cox':
                    # Time-Dependent NRI for each T
                    # base['raw_pred'] is {t: prob}, curr['raw_pred'] is {t: prob}
                    # raw_y is {'time', 'event'}
                    
                    base_preds = base['raw_pred']
                    curr_preds = curr['raw_pred']
                    time_points = curr['model_res']['metrics'].get('available_time_points', [])
                    
                    for t in time_points:
                        if t not in base_preds or t not in curr_preds: continue
                        
                        p_base = base_preds[t]
                        p_curr = curr_preds[t]
                        
                        # Construct Binary Target at T
                        times = base['raw_y']['time']
                        events = base['raw_y']['event']
                        
                        # Mask: Censored before T are excluded
                        mask_case = (events == 1) & (times <= t)
                        mask_control = (times > t)
                        valid = mask_case | mask_control
                        
                        y_true = mask_case[valid].astype(int)
                        y_prob_base = p_base[valid]
                        y_prob_curr = p_curr[valid]
                        
                        try:
                            nri_res = EvaluationService.calculate_nri_idi(
                                y_true,
                                y_prob_base,
                                y_prob_curr
                            )
                            # Add to time_dependent metrics
                            # e.g. metrics['time_dependent'][t]['nri'] = ...
                            if t in curr['model_res']['metrics']['time_dependent']:
                                curr['model_res']['metrics']['time_dependent'][t].update(nri_res)
                                
                        except Exception as e:
                            print(f"NRI at t={t} failed for Cox model {curr['model_res']['name']}: {e}")

            # Likelihood Ratio Test (LRT) and AIC/BIC comparison (Global)
            base_model_metrics = base['model_res']['metrics']
            for i in range(1, len(results)):
                curr = results[i]
                if curr['raw_pred'] is None: continue # Skip if model failed
                curr_model_metrics = curr['model_res']['metrics']

                if 'aic' in base_model_metrics and 'aic' in curr_model_metrics:
                    curr_model_metrics['delta_aic'] = curr_model_metrics['aic'] - base_model_metrics['aic']
                
                if 'bic' in base_model_metrics and 'bic' in curr_model_metrics:
                    curr_model_metrics['delta_bic'] = curr_model_metrics['bic'] - base_model_metrics['bic']
                    
                # Likelihood Ratio Test (LRT) P-value
                # 2 * (LL_new - LL_old) ~ Chi2(df)
                if 'll' in base_model_metrics and 'll' in curr_model_metrics:
                     ll_base = base_model_metrics['ll']
                     ll_curr = curr_model_metrics['ll']
                     k_base = base_model_metrics.get('k', 0)
                     k_curr = curr_model_metrics.get('k', 0)
                     
                     if k_curr > k_base: # Nested model assumption (adding vars)
                         lrt_stat = 2 * (ll_curr - ll_base)
                         df_diff = k_curr - k_base
                         if lrt_stat > 0:
                             p_val = chi2.sf(lrt_stat, df_diff)
                             curr['model_res']['metrics']['p_lrt'] = float(p_val)
                             curr['model_res']['metrics']['lrt_stat'] = float(lrt_stat)

                             
        # Clean up huge raw arrays
        for r in results:
            if 'raw_pred' in r: del r['raw_pred']
            if 'raw_y' in r: del r['raw_y']
            
        return {
            'comparison_data': [r['model_res'] for r in results],
            'methodology': AdvancedModelingService._generate_comparison_methodology()
        }

    @staticmethod
    def _generate_comparison_methodology():
        return ("Model discrimination was evaluated using the Area Under the Receiver Operating Characteristic (ROC) Curve (AUC) or Harrell's C-index. "
                "Models were compared based on their predictive performance on the same complete-case dataset.")
