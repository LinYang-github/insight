
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
            
        return self._format_results(cph)

    def _format_results(self, cph):
        summary = []
        for name in cph.params_.index:
            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(cph.params_[name], 3),
                'se': ResultFormatter.format_float(cph.standard_errors_[name], 3),
                'p_value': cph.summary.loc[name, 'p'],
                'hr': ResultFormatter.format_float(cph.hazard_ratios_[name], 2),
                'hr_ci_lower': ResultFormatter.format_float(np.exp(cph.confidence_intervals_.loc[name].iloc[0]), 2),
                'hr_ci_upper': ResultFormatter.format_float(np.exp(cph.confidence_intervals_.loc[name].iloc[1]), 2)
            }
            summary.append(row)
            
        return {
            'model_type': 'cox',
            'summary': summary,
            'metrics': {
                'c_index': ResultFormatter.format_float(cph.concordance_index_, 3),
                'aic': ResultFormatter.format_float(cph.AIC_partial_, 2)
            }
        }
