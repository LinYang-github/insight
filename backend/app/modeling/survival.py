
from lifelines import CoxPHFitter
import numpy as np
import pandas as pd
from .base import BaseModelStrategy
from app.utils.formatter import ResultFormatter

class CoxStrategy(BaseModelStrategy):
    def fit(self, df, target, features, params):
        time_col = target['time']
        event_col = target['event']
        
        # Check for low variance in event column
        if df[event_col].nunique() < 2:
             raise ValueError(f"Event column '{event_col}' must have at least 2 unique values (0 and 1).")
             
        data = df[features + [time_col, event_col]]
        cph = CoxPHFitter()
        
        try:
            cph.fit(data, duration_col=time_col, event_col=event_col)
        except Exception as e:
            if 'singular matrix' in str(e).lower():
                raise ValueError("LinAlgError: Singular matrix detected. Multi-collinearity suspect.")
            raise e
            
        # PH Assumption Test
        from lifelines.statistics import proportional_hazard_test
        ph_test_results = None
        try:
             # decimals=3 for rounding
             ph_test = proportional_hazard_test(cph, data, time_transform='km')
             ph_test_results = ph_test
        except Exception as e:
             # Don't fail model run if stats test fails (e.g. sample size)
             # print using logging ideally
             pass

        return self._format_results(cph, ph_test_results)

    def _format_results(self, cph, ph_results=None):
        summary = []
        
        # Parse PH results if available
        # ph_results.summary is a DataFrame with index = variable
        ph_table = None
        if ph_results is not None:
             ph_table = ph_results.summary
             
        for name in cph.params_.index:
            ph_p = '-'
            if ph_table is not None and name in ph_table.index:
                 ph_p = ResultFormatter.format_float(ph_table.loc[name, 'p'], 3)

            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(cph.params_[name], 3),
                'se': ResultFormatter.format_float(cph.standard_errors_[name], 3),
                'p_value': cph.summary.loc[name, 'p'],
                'hr': ResultFormatter.format_float(cph.hazard_ratios_[name], 2),
                'hr_ci_lower': ResultFormatter.format_float(np.exp(cph.confidence_intervals_.loc[name].iloc[0]), 2),
                'hr_ci_upper': ResultFormatter.format_float(np.exp(cph.confidence_intervals_.loc[name].iloc[1]), 2),
                'ph_test_p': ph_p
            }
            summary.append(row)
            
        metrics = {
            'c_index': ResultFormatter.format_float(cph.concordance_index_, 3),
            'aic': ResultFormatter.format_float(cph.AIC_partial_, 2)
        }
        
        if ph_results is not None:
             # Need global test? cph.check_assumptions() usually output it.
             # proportional_hazard_test returns object.
             # The result usually doesn't clearly expose a SINGLE global p-value in a simple property 
             # without checking documentation. 
             # Wait, documentation says it returns a StatisticalResult object. 
             # It performs a test for each variable + global.
             # The result.summary index has variable names, does it have 'Global'?
             # Usually not directly in result.summary unless one specific transform?
             # Let's check keys of summary.
             pass 

        return {
            'model_type': 'cox',
            'summary': summary,
            'metrics': metrics
        }
