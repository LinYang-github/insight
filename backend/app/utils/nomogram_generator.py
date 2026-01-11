import numpy as np
import pandas as pd

class NomogramGenerator:
    """
    Generates specification for a visualization-ready Nomogram from a fitted Cox model.
    Follows RMS (Regression Modeling Strategies) principles.
    """
    
    @staticmethod
    def generate_counts(df, features, target_event_col):
        """
        Generate raw counts/distributions for the variable ranges.
        """
        # Dictionary of variable -> min, max, or categories
        pass 

    @staticmethod
    def generate_spec(cph_model, df, features, time_points):
        """
        Args:
            cph_model: Fitted lifelines CoxPHFitter
            df: Original DataFrame (before one-hot, to get ranges)
            features: List of feature names used (before one-hot)
            time_points: List of time points to predict [12, 36, 60]
            
        Returns:
            dict: Nomogram Specification
        """
        # 1. Parse Coefficients & Group by Original Variable
        # Lifelines params index are: Continuous (Age), Dummies (Sex_Male, Race_Black...)
        params = cph_model.params_
        summary = cph_model.summary 
        
        # We need to map Model Coefficients back to Feature Specs
        # Structure:
        # {
        #   'Age': { type: 'continuous', min: 20, max: 80, coef: 0.05 },
        #   'Sex': { type: 'categorical', levels: [ {label: 'F', coef:0}, {label: 'M', coef: 0.5} ] }
        # }
        
        var_specs = {}
        
        # Helper: Determine if a param comes from a categorical feature
        # We naively assume features in 'features' list are the keys.
        # If feature is continuous, it appears as is.
        # If categorical, it appears as {Feature}_{Level} usually (if get_dummies used manually).
        # Need robust mapping.
        
        # Better approach: Iterate over USER features.
        for feat in features:
            if feat in df.columns:
                is_cat = df[feat].dtype == 'object' or str(df[feat].dtype) == 'category' or df[feat].nunique() < 10 # Heuristic
                
                # Check 1: Is this feature directly in params? (Continuous)
                if feat in params.index:
                    # Continuous
                    min_val = df[feat].min()
                    max_val = df[feat].max()
                    coef = params[feat]
                    
                    var_specs[feat] = {
                        'type': 'continuous',
                        'min': float(min_val),
                        'max': float(max_val),
                        'coef': float(coef),
                        'effect_range': abs(coef * (max_val - min_val))
                    }
                    
                else:
                    # Check 2: Are there dummy variables starting with this feature?
                    # This relies on the naming convention used in DataService (pd.get_dummies)
                    # Convention: "{feat}_{level}"
                    dummies = [p for p in params.index if p.startswith(f"{feat}_")]
                    
                    if dummies:
                        levels = []
                        # Reference Level handling is tricky because it's implicit (coef=0).
                        # We need to find all levels from DF to identify the reference.
                        all_levels = sorted(df[feat].unique().tolist())
                        
                        # Find which level is NOT in dummies -> Reference
                        # Assumption: level name is suffix
                        dummy_suffixes = [d.replace(f"{feat}_", "") for d in dummies]
                        
                        # Calculate effect range (Max coef - Min coef)
                        # Reference coef is 0.
                        coefs = [0.0] # start with Ref
                        for d in dummies:
                            coefs.append(params[d])
                        
                        min_coef = min(coefs)
                        max_coef = max(coefs)
                        
                        # Construct level specs
                        # We iterate ALL levels from data to ensure correct order/inclusion
                        level_specs = []
                        for level in all_levels:
                            level_str = str(level)
                            # Find matching dummy
                            # Note: pandas get_dummies might modify string (e.g. spaces to _)
                            # Simple matching check
                            dummy_match = None
                            for d in dummies:
                                if d == f"{feat}_{level_str}": 
                                    dummy_match = d
                                    break
                            
                            coef = 0.0
                            if dummy_match:
                                coef = params[dummy_match]
                            
                            level_specs.append({
                                'label': level_str,
                                'coef': float(coef)
                            })
                            
                        var_specs[feat] = {
                            'type': 'categorical',
                            'levels': level_specs,
                            'effect_range': max_coef - min_coef
                        }

        # 2. Normalize to 100 Points
        # Find variable with largest effect_range
        if not var_specs:
            return None
            
        max_effect_var = max(var_specs.items(), key=lambda x: x[1]['effect_range'])
        max_effect_val = max_effect_var[1]['effect_range']
        
        if max_effect_val == 0:
            points_per_unit = 0 # Singular model?
        else:
            points_per_unit = 100.0 / max_effect_val
            
        # 3. Build Axis Data (Mapping Value -> Points)
        axes = []
        
        # Also track Total Points Range
        min_total_points = 0
        max_total_points = 0
        
        for name, spec in var_specs.items():
            if spec['type'] == 'continuous':
                # Linear scale
                # Points = |Coef * (Value - Base)| * Scale?
                # Usually we align "0 points" to the value that gives min effect, OR just Min Value.
                # Let's align Min Value to 0 points contribution relative to itself?
                # No, contribution = Coef * Value.
                # We map (Coef * Value) to Points.
                # Relative to what? Usually we shift so min contribution is 0.
                
                contributions = [spec['min'] * spec['coef'], spec['max'] * spec['coef']]
                min_contrib = min(contributions)
                max_contrib = max(contributions)
                
                # Convert contribution range to points
                # Points = (Contribution - GlobalBase?) * Scale
                # Standard Nomogram: For each variable, we define a "0 point" baseline locally.
                # Local Points = (Contribution - Min_Local_Contribution) * points_per_unit
                
                spec['points_at_min'] = 0
                spec['points_at_max'] = (max_contrib - min_contrib) * points_per_unit
                
                # Add to total points range
                max_total_points += spec['points_at_max']
                
                axes.append({
                    'name': name,
                    'type': 'continuous',
                    'min': spec['min'],
                    'max': spec['max'],
                    'ticks': [spec['min'], spec['max']], # Start/End
                    # Calculate Points for Min and Max
                    # If coef > 0: Min -> 0 pts, Max -> N pts
                    # If coef < 0: Max -> 0 pts, Min -> N pts
                    'points': {
                        str(spec['min']): 0 if spec['coef'] > 0 else spec['points_at_max'],
                        str(spec['max']): spec['points_at_max'] if spec['coef'] > 0 else 0
                    }
                })
                
            elif spec['type'] == 'categorical':
                # Local Points = (Coef - Min_Coef) * points_per_unit
                coefs = [l['coef'] for l in spec['levels']]
                min_c = min(coefs)
                max_c = max(coefs)
                
                local_max_points = (max_c - min_c) * points_per_unit
                max_total_points += local_max_points
                
                levels_visual = []
                for l in spec['levels']:
                    p = (l['coef'] - min_c) * points_per_unit
                    levels_visual.append({
                        'label': l['label'],
                        'points': p,
                        'coef': l['coef']
                    })
                    
                axes.append({
                    'name': name,
                    'type': 'categorical',
                    'levels': levels_visual
                })

        # 4. Total Points to Survival Mapping
        # Formula: S(t|x) = S0(t) ^ exp(LP)
        # LP = Sum(Coef * X)
        # TotalPoints = Sum(LocalPoints)
        # We need relationship between LP and TotalPoints.
        # LocalPoints_i = (Coef_i * X_i - MinContrib_i) * Scale
        # Sum(LocalPoints) = Scale * (Sum(Coef*X) - Sum(MinContrib))
        # Sum(LocalPoints) = Scale * (LP - Constant_Offset)
        # LP = (TotalPoints / Scale) + Constant_Offset
        # Constant_Offset = Sum(MinContrib_i of all vars) 
        
        sum_min_contrib = 0
        for name, spec in var_specs.items():
            if spec['type'] == 'continuous':
                contribs = [spec['min'] * spec['coef'], spec['max'] * spec['coef']]
                sum_min_contrib += min(contribs)
            elif spec['type'] == 'categorical':
                 coefs = [l['coef'] for l in spec['levels']]
                 sum_min_contrib += min(coefs)
                 
        # Precompute Base Survivals S0(t)
        baseline_survival = cph_model.baseline_survival_
        # baseline_survival index is time, value is S0(t)
        
        survival_scales = []
        for t in time_points:
            # Find S0(t)
            # Find closest index
            idx = baseline_survival.index.get_indexer([t], method='nearest')[0]
            s0_t = baseline_survival.iloc[idx, 0]
            
            # Generate mapping table for visual axis
            # Total Points: 0 to max_total_points (e.g. 200)
            # Step size 10
            ticks = []
            steps = 20
            step_size = max_total_points / steps
            
            for i in range(steps + 1):
                pt = i * step_size
                # Convert Pt -> LP
                # LP = (Pt / Scale) + Offset
                lp = (pt / points_per_unit) + sum_min_contrib
                # S(t) = S0(t) ^ exp(LP)
                surv = s0_t ** np.exp(lp)
                
                ticks.append({
                    'points': pt,
                    'survival': surv
                })
                
            survival_scales.append({
                'time': t,
                'ticks': ticks
            })
            
        return {
            'axes': axes,
            'total_points': {
                'min': 0,
                'max': max_total_points
            },
            'survival_scales': survival_scales,
            'base_survivals': { t: baseline_survival.iloc[baseline_survival.index.get_indexer([t], method='nearest')[0], 0] for t in time_points },
            'formula_params': {
                'points_per_unit': points_per_unit,
                'constant_offset': sum_min_contrib
            }
        }
