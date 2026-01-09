
import statsmodels.api as sm
import numpy as np
import pandas as pd
from .base import BaseModelStrategy
from app.utils.formatter import ResultFormatter

class LinearRegressionStrategy(BaseModelStrategy):
    def fit(self, df, target, features, params):
        X = df[features]
        X = sm.add_constant(X)
        y = df[target]
        
        model = sm.OLS(y, X)
        res = model.fit()
        
        return self._format_results(res)

    def _format_results(self, res):
        summary = []
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()

        for name in params.index:
            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(params[name], 3),
                'se': ResultFormatter.format_float(bse[name], 3),
                'p_value': pvalues[name], # Keep raw for sorting/logic, format logic handles display? 
                # Actually frontend expects number for logic, but maybe we should provide formatted string too?
                # For MVP compatibility, let's keep raw numbers here but maybe add formatted fields if needed.
                # Wait, review requirement: "Result Formatting: APA style P-values (<0.001)". 
                # Since frontend does `scope.row.p_value.toFixed(4)`, we should arguably update frontend or return string.
                # BUT, `sigVars.filter` needs numbers. 
                # Strategy: Return raw numbers for logic, AND formatted strings for display?
                # Or simply ensure backend precision is handled. 
                # Let's keep raw numbers for `p_value` to not break frontend logic `v.p_value < 0.05`.
                # We can add `p_value_fmt` or just rely on frontend for now but maybe frontend needs update?
                # Re-reading req: "In medical journals... must write <0.001... ResultFormatter utility... ensuring export matches".
                # Export service uses these results. So we should probably keep raw for UI logic, but maybe format for export? 
                # Or better: The UI logic `toFixed` is what user identified as "Problem". 
                # Let's return raw, but maybe we can update UI later. 
                # For now let's stick to returning CLEAN floats (rounded) as requested by "Three decimal places for Coef".
                
                'ci_lower': ResultFormatter.format_float(conf.loc[name][0], 3),
                'ci_upper': ResultFormatter.format_float(conf.loc[name][1], 3)
            }
            summary.append(row)

        return {
            'model_type': 'linear',
            'summary': summary,
            'metrics': {
                'rsquared': ResultFormatter.format_float(res.rsquared, 4),
                'aic': ResultFormatter.format_float(res.aic, 2),
                'bic': ResultFormatter.format_float(res.bic, 2)
            }
        }

class LogisticRegressionStrategy(BaseModelStrategy):
    def fit(self, df, target, features, params):
        X = df[features]
        X = sm.add_constant(X)
        y = df[target]
        
        model = sm.Logit(y, X)
        try:
            res = model.fit(disp=0)
        except Exception as e:
            if 'Perfect separation' in str(e) or 'singular matrix' in str(e).lower():
                 raise ValueError("Model failed to converge. Possible reasons: Perfect separation or Singular Matrix.")
            raise e
            
        return self._format_results(res)

    def _format_results(self, res):
        summary = []
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()

        for name in params.index:
            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(params[name], 3),
                'se': ResultFormatter.format_float(bse[name], 3),
                'p_value': pvalues[name],
                'ci_lower': ResultFormatter.format_float(conf.loc[name][0], 3),
                'ci_upper': ResultFormatter.format_float(conf.loc[name][1], 3),
                'or': ResultFormatter.format_float(np.exp(params[name]), 2),
                'or_ci_lower': ResultFormatter.format_float(np.exp(conf.loc[name][0]), 2),
                'or_ci_upper': ResultFormatter.format_float(np.exp(conf.loc[name][1]), 2)
            }
            summary.append(row)

        return {
            'model_type': 'logistic',
            'summary': summary,
            'metrics': {
                'prsquared': ResultFormatter.format_float(res.prsquared, 4),
                'aic': ResultFormatter.format_float(res.aic, 2),
                'bic': ResultFormatter.format_float(res.bic, 2)
            }
        }
