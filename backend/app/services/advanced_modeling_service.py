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
            
        return results

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
            
        return results

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
                    
        return results

    @staticmethod
    def generate_nomogram(df, target, event_col, model_type, predictors):
        """
        Generate data for Nomogram and Web Calculator.
        
        Logic:
        1. Fit Model -> Get Coefs.
        2. Calculate "Points" for each variable based on its effect size relative to the one with max effect.
        3. Create mapping: Value -> Points.
        4. Create mapping: Total Points -> Probability.
        """
        results = {
            'variables': [],
            'risk_table': []
        }
        
        # 1. Fit Model
        # Simple Logic: Reuse fit_simple_model or just fit here.
        # We need the model object to predict.
        df_clean = df[[target] + predictors].copy()
        if event_col: 
            df_clean = df[[target, event_col] + predictors].dropna()
        else:
            df_clean = df_clean.dropna()

        df_clean = DataService.preprocess_for_formula(df_clean)

        # Fit
        params = {}
        model = None
        base_risk = 0 # Intercept
        
        if model_type == 'logistic':
             # formula
             f = f"{target} ~ {' + '.join(predictors)}"
             model_res = smf.logit(f, data=df_clean).fit(disp=0)
             params = model_res.params.to_dict()
             # params include Intercept
        elif model_type == 'cox':
             cph = CoxPHFitter()
             cph.fit(df_clean, duration_col=target, event_col=event_col, formula=" + ".join(predictors))
             params = cph.params_.to_dict()
             # Cox has no intercept in partial hazard, but baseline hazard exists.
             # Nomogram for Cox usually predicts Survival at Time T.
             # We need a baseline survival at specific T (e.g. median time).
             # Let's pick median time for now.
             median_time = df_clean[target].median()
             baseline_sf = cph.predict_survival_function(pd.DataFrame({p:[0] for p in predictors}, index=[0]), times=[median_time]).iloc[0,0]
             # S(t|x) = S0(t)^exp(lp)
             # lp = Xb (centered? lifelines centers data)
             # Let's stick to Linear Predictor points.
             
        # 2. Calculate Points Scaling
        # Find the variable with largest effect range (beta * (max-min))
        max_effect = 0
        effect_ranges = {}
        
        var_metas = {} # Store min/max/categories
        
        for var in predictors:
            if var not in params and f"C({var})" not in str(params.keys()):
                # Categorical might be dummy encoded in params? 
                # Statsmodels/Lifelines formula handles it.
                # Simplification: Assume numeric predictors for MVP or check simple categorical logic.
                pass
            
            # Numeric logic
            if pd.api.types.is_numeric_dtype(df_clean[var]):
                 coef = params.get(var, 0)
                 mn, mx = df_clean[var].min(), df_clean[var].max()
                 rng = abs(coef * (mx - mn))
                 effect_ranges[var] = rng
                 var_metas[var] = {'type': 'numeric', 'min': mn, 'max': mx, 'coef': coef}
                 if rng > max_effect: max_effect = rng
            else:
                 # Categorical
                 # Coefs are usually Var[T.Level]
                 # Find all levels
                 levels = df_clean[var].unique()
                 # Find max coef diff
                 # base level is 0
                 c_values = [0]
                 for l in levels:
                     k = f"{var}[T.{l}]"
                     if k in params: c_values.append(params[k])
                 
                 rng = max(c_values) - min(c_values)
                 effect_ranges[var] = rng
                 # Store levels coeff
                 # ... (skipped for MVP complex categorical, assuming numeric/binary for simplicity or handling nicely)
                 # Actually, let's assume numeric for now to prevent complexity explosion in 1 step.
                 # If user passes categorical, we might skip or simplistic handle.
                 pass

        if max_effect == 0:
            return results # No significant vars or empty
            
        points_per_unit_beta = 100 / max_effect
        
        # 3. Generate Variable Scales
        total_min_points = 0
        total_max_points = 0
        
        for var in predictors:
            if var in var_metas:
                meta = var_metas[var]
                coef = meta['coef']
                
                # Points for Min and Max
                # We align Min Value to 0 points? No.
                # If coef > 0: MinVal -> 0 pts (relative), MaxVal -> 100 pts.
                # Linear contribution: Pts = (Val - Min) * Coef * Scaling ?? 
                # Standard Nomogram: 
                #  LP_contribution = Val * Coef
                #  Points = abs(LP_contribution) * Scaling? 
                #  Usually relative to base.
                #  Let's define: Points(Val) = (Val * Coef - Min_Contribution) * points_per_unit_beta
                
                contributions = [meta['min']*coef, meta['max']*coef]
                min_c = min(contributions)
                max_c = max(contributions)
                
                def val_to_point(v):
                    c = v * coef
                    # We map [min_c, max_c] to [0, 100] (normalized to max_effect)
                    # wait, max_effect is the global max span.
                    # so current span maps to (max_c - min_c) * points_per_unit_beta
                    return (c - min_c) * points_per_unit_beta
                
                # Setup visualization axis
                # Ticks
                ticks = np.linspace(meta['min'], meta['max'], 10)
                tick_points = [val_to_point(t) for t in ticks]
                
                results['variables'].append({
                    'name': var,
                    'type': 'numeric',
                    'min': float(meta['min']),
                    'max': float(meta['max']),
                    'coef': float(coef),
                    'points_mapping': [{'val': float(t), 'pts': float(p)} for t, p in zip(ticks, tick_points)]
                })
                
                total_min_points += 0 # By definition of shift
                total_max_points += (max_c - min_c) * points_per_unit_beta

        # 4. Risk Mapping
        # Total Points -> LP -> Prob
        # LP = Intercept + Sum(Val*Coef)
        # We shifted Val*Coef by min_c.
        # LP = Intercept + Sum(Points / Scaling + Min_C)
        #    = Intercept + Sum(Min_C) + Total_Points / Scaling
        
        sum_min_c = sum([var_metas[v]['min']*var_metas[v]['coef'] for v in predictors if v in var_metas]+[0]) # +0 for safety
        intercept = params.get('Intercept', 0)
        
        point_grid = np.linspace(0, total_max_points, 100)
        risks = []
        
        for pt in point_grid:
            lp = intercept + sum_min_c + (pt / points_per_unit_beta)
            if model_type == 'logistic':
                prob = 1 / (1 + np.exp(-lp))
                risks.append(prob)
            elif model_type == 'cox':
                 # 1 - S0(t)^exp(lp)
                 # need baseline
                 prob = 1 - (baseline_sf ** np.exp(lp - intercept)) # Cox Logic is complex. LP is usually Xb-Mean(Xb).
                 # Simpler: Risk at Median Time.
                 prob = 1 - (baseline_sf ** np.exp(lp)) 
                 # Note: lifelines 'partial hazard' usually excludes baseline.
                 risks.append(prob)
                 
        results['risk_table'] = [{'points': float(pt), 'risk': float(r)} for pt, r in zip(point_grid, risks)]
        
        # Meta info for Calculator
        results['formula'] = {
            'intercept': float(intercept),
            'baseline_survival': float(baseline_sf) if model_type == 'cox' else None,
            'coeffs': {v: float(var_metas[v]['coef']) for v in predictors if v in var_metas},
            'model_type': model_type
        }
        return results

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
            name = config['name']
            feats = config['features']
            
            try:
                metrics = {}
                roc_data = []
                
                if model_type == 'logistic':
                    # Use ModelingService for standard Logistic
                    model_res = ModelingService.run_model(df_clean, 'logistic', target, feats)
                    metrics = model_res.get('metrics', {})
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
                    
                    # C-Index
                    c_index = cph.concordance_index_
                    metrics['auc'] = c_index # Show C-index in AUC column for now
                    metrics['auc_ci'] = f"C-idx"
                    
                    # Time-Dependent ROC Logic (at Median)
                    # Get Partial Hazard (Risk Score)
                    risk_score = cph.predict_partial_hazard(temp_df)
                    
                    # Define Binary Outcome at T=Median
                    # Case: Event occurred at or before Median (Event=1, Time<=Med)
                    # Control: Survived past Median (Time>Med)
                    # Exclude: Censored before Median (Event=0, Time<=Med)
                    
                    mask_case = (temp_df[event_col] == 1) & (temp_df[target] <= median_time)
                    mask_control = (temp_df[target] > median_time)
                    
                    valid_mask = mask_case | mask_control
                    y_binary = mask_case[valid_mask].astype(int)
                    y_scores = risk_score[valid_mask]
                    
                    if len(y_binary.unique()) > 1:
                        fpr, tpr, _ = roc_curve(y_binary, y_scores)
                        roc_auc = calc_auc(fpr, tpr)
                        # We might overwrite metrics['auc'] with this Time-Dep AUC or separate it
                        # Let's keep C-index in table, but plot this ROC.
                        # Actually standard practice: Plot this ROC, show this AUC in plot legend.
                        # Table shows C-index? Or this AUC?
                        # Let's update metrics['auc'] to this ROC AUC to match plot.
                        metrics['auc'] = roc_auc
                        metrics['auc_ci'] = f"at Median={median_time:.1f}"
                        
                        roc_data = [{'fpr': f, 'tpr': t} for f, t in zip(fpr, tpr)]
                    else:
                        metrics['error'] = "Not enough events at median time for ROC"
                
                results.append({
                    'name': name,
                    'features': feats,
                    'n': n_samples,
                    'metrics': metrics,
                    'roc_data': roc_data
                })
                
            except Exception as e:
                # If one fails (e.g. perfect separation on subset), we report it
                results.append({
                    'name': name,
                    'error': str(e)
                })
                
        return results
