import pandas as pd
import statsmodels.api as sm
from lifelines import CoxPHFitter
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import roc_curve, auc, confusion_matrix, accuracy_score, mean_squared_error, r2_score
import xgboost as xgb
import shap
from app.services.data_service import DataService

class ModelingService:
    @staticmethod
    def run_model(df, model_type, target, features, model_params=None):
        """
        Run statistical or ML model.
        """
        model_params = model_params or {}
        
        # Robust encoding read is handled by caller (api) getting dataframe via robust method, 
        # but here we receive a DF directly.
        
        X = df[features]
        
        results = {}
        
        if model_type in ['linear', 'logistic']:
             X = sm.add_constant(X)
             # ... existing statsmodels logic ...
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
            data = df[features + [time_col, event_col]]
            cph.fit(data, duration_col=time_col, event_col=event_col)
            results = ModelingService._format_lifelines(cph)

        elif model_type in ['random_forest', 'xgboost']:
             results = ModelingService._run_ml_model(df, model_type, target, features, model_params)

        else:
            raise ValueError(f"Unknown model type: {model_type}")
            
        return DataService.sanitize_for_json(results)

    @staticmethod
    def _run_ml_model(df, model_type, target, features, params):
        X = df[features]
        y = df[target]
        
        # Simple task checking: if target is float -> Regression, else (int/str) -> Classification
        is_classification = False
        if pd.api.types.is_numeric_dtype(y):
             # If few unique values, could be classification (e.g. 0/1)
             if y.nunique() <= 10 and sorted(y.unique().tolist()) == [0, 1]:
                 is_classification = True
             elif y.nunique() <= 10:
                 # Multiclass or just small numeric? Treat as regression for now unless explicitly stated?
                 # For medical MVP, usually 0/1 is classification.
                 is_classification = True # Assumption: small unique int-like is class
             else:
                 is_classification = False
        else:
             is_classification = True

        # encode y if classification and not numeric
        if is_classification and not pd.api.types.is_numeric_dtype(y):
             y = pd.Categorical(y).codes
        
        model = None
        if model_type == 'random_forest':
            if is_classification:
                model = RandomForestClassifier(n_estimators=100, max_depth=None, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, max_depth=None, random_state=42)
        elif model_type == 'xgboost':
            if is_classification:
                model = xgb.XGBClassifier(n_estimators=100, max_depth=6, random_state=42, use_label_encoder=False, eval_metric='logloss')
            else:
                model = xgb.XGBRegressor(n_estimators=100, max_depth=6, random_state=42)
        
        model.fit(X, y)
        
        # Evaluation
        metrics = {}
        plots = {}
        
        if is_classification:
            y_pred = model.predict(X)
            y_prob = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            
            metrics['accuracy'] = accuracy_score(y, y_pred)
            if len(np.unique(y)) == 2:
                 fpr, tpr, _ = roc_curve(y, y_prob)
                 metrics['auc'] = auc(fpr, tpr)
                 plots['roc'] = {'fpr': fpr.tolist(), 'tpr': tpr.tolist()}
                 
            cm = confusion_matrix(y, y_pred)
            metrics['confusion_matrix'] = cm.tolist()
        else:
            y_pred = model.predict(X)
            metrics['r2'] = r2_score(y, y_pred)
            metrics['rmse'] = np.sqrt(mean_squared_error(y, y_pred))

        # SHAP Interpretability available for Tree models
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        # For classification, shap_values is a list [class0, class1], we usually want class1 for binary
        if isinstance(shap_values, list): 
            shap_values = shap_values[1] # Focus on positive class
        
        # Feature Importance (mean absolute SHAP)
        feature_importance = np.abs(shap_values).mean(axis=0)
        importance_df = pd.DataFrame({
            'feature': features,
            'importance': feature_importance
        }).sort_values(by='importance', ascending=False)
        
        return {
            'model_type': model_type,
            'task': 'classification' if is_classification else 'regression',
            'metrics': metrics,
            'importance': importance_df.to_dict(orient='records'),
            'plots': plots
        }
    
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
