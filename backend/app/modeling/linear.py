
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
        
        return self._format_results(res, df, features)

    def _format_results(self, res, df=None, features=None):
        # Calculate VIF
        vif_data = []
        if df is not None and features is not None:
             from app.utils.diagnostics import ModelDiagnostics
             vif_data = ModelDiagnostics.calculate_vif(df, features)
        
        vif_map = {item['variable']: item['vif'] for item in vif_data}

        summary = []
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()

        for name in params.index:
            if name == 'const': continue
            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(params[name], 3),
                'se': ResultFormatter.format_float(bse[name], 3),
                'p_value': pvalues[name],
                'ci_lower': ResultFormatter.format_float(conf.loc[name][0], 3),
                'ci_upper': ResultFormatter.format_float(conf.loc[name][1], 3),
                'vif': vif_map.get(name, '-')
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
            
        # Evaluation
        y_prob = res.predict(X)
        from app.utils.evaluation import ModelEvaluator
        metrics, plots = ModelEvaluator.evaluate_classification(y, y_prob)
        
        # 5-Fold Cross Validation
        from sklearn.model_selection import KFold
        from sklearn.metrics import roc_auc_score
        
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_aucs = []
        
        try:
            # Need to re-prepare X without constant for splitting if using sklearn, but sm handles it.
            # Using dataframe indices is safest.
            X_reset = X.reset_index(drop=True)
            y_reset = y.reset_index(drop=True)
            
            for train_index, test_index in kf.split(X_reset):
                X_train, X_test = X_reset.iloc[train_index], X_reset.iloc[test_index]
                y_train, y_test = y_reset.iloc[train_index], y_reset.iloc[test_index]
                
                # Fit on train
                try:
                    cv_model = sm.Logit(y_train, X_train)
                    cv_res = cv_model.fit(disp=0)
                    # Predict on test
                    y_cv_prob = cv_res.predict(X_test)
                    
                    if len(np.unique(y_test)) == 2:
                        cv_aucs.append(roc_auc_score(y_test, y_cv_prob))
                except Exception:
                    continue # Skip failed folds (e.g. separation)
                    
            if cv_aucs:
                metrics['cv_auc_mean'] = ResultFormatter.format_float(np.mean(cv_aucs), 3)
                metrics['cv_auc_std'] = ResultFormatter.format_float(np.std(cv_aucs), 3)
                
        except Exception as e:
            # CV failure shouldn't block main result
            print(f"CV Failed: {e}")
            pass
        # CV logic ... (keep existing)
            
        # Diagnostics: VIF
        from app.utils.diagnostics import ModelDiagnostics
        vif_data = ModelDiagnostics.calculate_vif(df, features)
        
        return self._format_results(res, metrics, plots, vif_data)

    def _format_results(self, res, metrics=None, plots=None, vif_data=None):
        summary = []
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()
        
        # Create VIF map
        vif_map = {item['variable']: item['vif'] for item in (vif_data or [])}

        for name in params.index:
            if name == 'const': continue # Skip const for table usually, or keep? 
            # Existing code kept const. Let's keep it but VIF is usually N/A for const.
            
            row = {
                'variable': name,
                'coef': ResultFormatter.format_float(params[name], 3),
                'se': ResultFormatter.format_float(bse[name], 3),
                'p_value': pvalues[name],
                'ci_lower': ResultFormatter.format_float(conf.loc[name][0], 3),
                'ci_upper': ResultFormatter.format_float(conf.loc[name][1], 3),
                'or': ResultFormatter.format_float(np.exp(params[name]), 2),
                'or_ci_lower': ResultFormatter.format_float(np.exp(conf.loc[name][0]), 2),
                'or_ci_upper': ResultFormatter.format_float(np.exp(conf.loc[name][1]), 2),
                'vif': vif_map.get(name, '-')
            }
            summary.append(row)
            
        # Add const if needed, currently loop iterates all params
        # But 'const' might be in params.index.
        # My loop above handles whatever is in params.index.
        
        metrics = metrics or {}
        metrics['prsquared'] = ResultFormatter.format_float(res.prsquared, 4)
        metrics['aic'] = ResultFormatter.format_float(res.aic, 2)
        metrics['bic'] = ResultFormatter.format_float(res.bic, 2)

        return {
            'model_type': 'logistic',
            'summary': summary,
            'metrics': metrics,
            'plots': plots
        }
