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
    def check_data_integrity(df, features, target):
        """
        Checks for NaNs, Infs in features and target.
        """
        # Check features
        if df[features].isnull().any().any():
            missing_cols = df[features].columns[df[features].isnull().any()].tolist()
            raise ValueError(f"Feature variables contain missing values (NaN): {', '.join(missing_cols)}. Please impute missing values in 'Data Cleaning' first.")
            
        if np.isinf(df[features].select_dtypes(include=np.number)).values.any():
             raise ValueError("Feature variables contain infinite values. Please check your data.")

        # Check target
        if isinstance(target, str):
            if df[target].isnull().any():
                raise ValueError(f"Target variable '{target}' contains missing values.")
        elif isinstance(target, dict): # Cox time/event
            if df[target['time']].isnull().any() or df[target['event']].isnull().any():
                 raise ValueError("Target variables (Time/Event) contain missing values.")

    @staticmethod
    def run_model(df, model_type, target, features, model_params=None):
        """
        Run statistical or ML model.
        """
        model_params = model_params or {}
        
        # 1. Integrity Check
        ModelingService.check_data_integrity(df, features, target)
        
        X = df[features]
        results = {}
        
        try:
            if model_type in ['linear', 'logistic']:
                 X = sm.add_constant(X)
                 if model_type == 'linear':
                    y = df[target]
                    model = sm.OLS(y, X)
                    res = model.fit()
                    results = ModelingService._format_statsmodels(res)
                 elif model_type == 'logistic':
                    y = df[target]
                    model = sm.Logit(y, X)
                    try:
                        res = model.fit(disp=0) # disp=0 to silence stdout
                    except Exception as e:
                        if 'Perfect separation' in str(e) or 'singular matrix' in str(e).lower():
                             raise ValueError("Model failed to converge. Possible reasons: Perfect separation (data classes are too easy to separate) or Singular Matrix (variables are highly correlated).")
                        raise e
                        
                    results = ModelingService._format_statsmodels(res, logistic=True)

            elif model_type == 'cox':
                time_col = target['time']
                event_col = target['event']
                cph = CoxPHFitter()
                
                # Check for low variance in event column
                if df[event_col].nunique() < 2:
                     raise ValueError(f"Event column '{event_col}' must have at least 2 unique values (0 and 1).")
                     
                data = df[features + [time_col, event_col]]
                try:
                    cph.fit(data, duration_col=time_col, event_col=event_col)
                except Exception as e:
                    if 'singular matrix' in str(e).lower():
                        raise ValueError("LinAlgError: Singular matrix detected. This usually means two or more variables are perfectly correlated (multi-collinearity). Please remove redundant variables.")
                    raise e
                    
                results = ModelingService._format_lifelines(cph)

            elif model_type in ['random_forest', 'xgboost']:
                 results = ModelingService._run_ml_model(df, model_type, target, features, model_params)

            else:
                raise ValueError(f"Unknown model type: {model_type}")
                
        except np.linalg.LinAlgError:
             raise ValueError("Linear Algebra Error: Singular matrix detected. Please check for perfect multi-collinearity among your variables.")
        except Exception as e:
            # Re-raise known ValueErrors, wrap others
            if isinstance(e, ValueError):
                raise e
            raise RuntimeError(f"Model execution failed: {str(e)}")

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

        if is_classification and not pd.api.types.is_numeric_dtype(y):
             y = pd.Categorical(y).codes
        
        # Robustly handle categorical features in X for Sklearn/XGB
        X = X.copy()
        for col in X.columns:
            if not pd.api.types.is_numeric_dtype(X[col]):
                # Fill NaN for categorical with a placeholder if present (though check_integrity might catch it)
                # But to be safe for encoding:
                X[col] = X[col].astype(str)
                X[col] = pd.Categorical(X[col]).codes
        
        # Extract params with defaults
        n_estimators = int(params.get('n_estimators', 100))
        max_depth = params.get('max_depth', None)
        if max_depth is not None and str(max_depth).strip() != '':
             max_depth = int(max_depth)
        else:
             max_depth = None # None for RF means unlimited, for XGB it means 6 (default) usually
             
        learning_rate = float(params.get('learning_rate', 0.1))

        model = None
        if model_type == 'random_forest':
            if is_classification:
                model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        elif model_type == 'xgboost':
            # XGBoost default max_depth is 6 if None is passed? Usually we set a default.
            if max_depth is None: max_depth = 6
            
            if is_classification:
                model = xgb.XGBClassifier(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate, random_state=42, use_label_encoder=False, eval_metric='logloss')
            else:
                model = xgb.XGBRegressor(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate, random_state=42)
        
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
