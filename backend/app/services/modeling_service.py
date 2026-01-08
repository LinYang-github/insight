import pandas as pd
import statsmodels.api as sm
from lifelines import CoxPHFitter
import numpy as np

class ModelingService:
    @staticmethod
    def run_model(df, model_type, target, features, model_params=None):
        """
        Run statistical model.
        :param df: pandas DataFrame
        :param model_type: 'linear', 'logistic', 'cox'
        :param target: target variable name (or tuple for survival: (time, event))
        :param features: list of feature names
        :param model_params: dict of optional parameters
        :return: dict with results
        """
        X = df[features]
        # Add constant for statsmodels (except Cox)
        if model_type in ['linear', 'logistic']:
            X = sm.add_constant(X)
        
        results = {}
        
        if model_type == 'linear':
            y = df[target]
            model = sm.OLS(y, X)
            res = model.fit()
            results = ModelingService._format_statsmodels(res)
            
        elif model_type == 'logistic':
            y = df[target]
            model = sm.Logit(y, X)
            res = model.fit()
            results = ModelingService._format_statsmodels(res, logistic=True)
            
        elif model_type == 'cox':
            time_col = target['time']
            event_col = target['event']
            
            cph = CoxPHFitter()
            # Combine X and y for lifelines
            data = df[features + [time_col, event_col]]
            cph.fit(data, duration_col=time_col, event_col=event_col)
            results = ModelingService._format_lifelines(cph)
            
        else:
            raise ValueError(f"Unknown model type: {model_type}")
            
        return results

    @staticmethod
    def _format_statsmodels(res, logistic=False):
        # Extract coefficients, CI, P-values
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()
        
        summary = []
        for name in params.index:
            row = {
                'variable': name,
                'coef': params[name],
                'se': bse[name],
                'p_value': pvalues[name],
                'ci_lower': conf.loc[name][0],
                'ci_upper': conf.loc[name][1]
            }
            if logistic:
                row['or'] = np.exp(params[name])
                row['or_ci_lower'] = np.exp(conf.loc[name][0])
                row['or_ci_upper'] = np.exp(conf.loc[name][1])
            summary.append(row)
            
        metric_dict = {
            'aic': res.aic,
            'bic': res.bic
        }
        if logistic:
             metric_dict['prsquared'] = res.prsquared
        else:
             metric_dict['rsquared'] = res.rsquared
             
        return {
            'summary': summary,
            'metrics': metric_dict
        }

    @staticmethod
    def _format_lifelines(cph):
        summary = []
        for name in cph.params_.index:
            row = {
                'variable': name,
                'coef': cph.params_[name],
                'se': cph.standard_errors_[name],
                'p_value': cph.summary.loc[name, 'p'],
                'hr': cph.hazard_ratios_[name],
                'hr_ci_lower': np.exp(cph.confidence_intervals_.loc[name].iloc[0]),
                'hr_ci_upper': np.exp(cph.confidence_intervals_.loc[name].iloc[1])
            }
            summary.append(row)
            
        return {
            'summary': summary,
            'metrics': {
                'c_index': cph.concordance_index_,
                'aic': cph.AIC_partial_
            }
        }
