"""
app.modeling.tree.py

机器学习树模型策略。
包含 随机森林 (Random Forest) 和 XGBoost。
集成 SHAP (SHapley Additive exPlanations) 用于模型可解释性分析，
并提供 5 折交叉验证 (5-Fold CV) 以评估模型泛化能力。
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import roc_curve, auc, confusion_matrix, accuracy_score, mean_squared_error, r2_score
import xgboost as xgb
import shap
from .base import BaseModelStrategy
from app.utils.formatter import ResultFormatter

class TreeModelStrategy(BaseModelStrategy):
    """
    树模型抽象策略。
    
    特点：
    - 自动处理分类变量转换（Label Encoding）。
    - 自动区分二分类 (Classification) 与回归 (Regression) 任务。
    - 使用 SHAP 值评估特征重要性，符合当前机器学习解释性的主流标准。
    """
    def __init__(self, model_type):
        self.model_type = model_type

    def fit(self, df, target, features, params):
        X = df[features]
        y = df[target]

        # Determine task
        is_classification = False
        if pd.api.types.is_numeric_dtype(y):
             if y.nunique() <= 10 and sorted(y.unique().tolist()) == [0, 1]:
                 is_classification = True
             elif y.nunique() <= 10:
                 is_classification = True # Assumption
             else:
                 is_classification = False
        else:
             is_classification = True

        # Encode Y
        if is_classification and not pd.api.types.is_numeric_dtype(y):
             y = pd.Categorical(y).codes
        
        # Encode X (Robust encoding for Categorical)
        X = X.copy()
        for col in X.columns:
            if not pd.api.types.is_numeric_dtype(X[col]):
                X[col] = X[col].astype(str)
                X[col] = pd.Categorical(X[col]).codes

        # Params
        n_estimators = int(params.get('n_estimators', 100))
        max_depth = params.get('max_depth', None)
        if max_depth is not None and str(max_depth).strip() != '':
             max_depth = int(max_depth)
        else:
             max_depth = None if self.model_type == 'random_forest' else 6
             
        learning_rate = float(params.get('learning_rate', 0.1))

        # Model Init
        model = self._init_model(is_classification, n_estimators, max_depth, learning_rate)
        
        # Fit
        model.fit(X, y)
        
        # Eval
        metrics, plots = self._evaluate(model, X, y, is_classification)
        
        # Explain
        importance = self._explain(model, X, features)
        
        return {
            'model_type': self.model_type,
            'task': 'classification' if is_classification else 'regression',
            'metrics': metrics,
            'importance': importance,
            'plots': plots
        }
    
    def _init_model(self, is_clf, n_est, depth, lr):
        if self.model_type == 'random_forest':
            if is_clf: return RandomForestClassifier(n_estimators=n_est, max_depth=depth, random_state=42)
            else: return RandomForestRegressor(n_estimators=n_est, max_depth=depth, random_state=42)
        elif self.model_type == 'xgboost':
            if is_clf: return xgb.XGBClassifier(n_estimators=n_est, max_depth=depth, learning_rate=lr, random_state=42, use_label_encoder=False, eval_metric='logloss')
            else: return xgb.XGBRegressor(n_estimators=n_est, max_depth=depth, learning_rate=lr, random_state=42)
        raise ValueError(f"Unknown model type {self.model_type}")

    def _evaluate(self, model, X, y, is_clf):
        metrics = {}
        plots = {}
        y_pred = model.predict(X)
        
        if is_clf:
            y_prob = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            from app.utils.evaluation import ModelEvaluator
            metrics, plots = ModelEvaluator.evaluate_classification(y, y_prob, y_pred)
            
            # 5-Fold Cross Validation
            try:
                from sklearn.model_selection import cross_val_score
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
                metrics['cv_auc_mean'] = ResultFormatter.format_float(np.mean(cv_scores), 3)
                metrics['cv_auc_std'] = ResultFormatter.format_float(np.std(cv_scores), 3)
            except Exception as e:
                print(f"CV Failed: {e}")
                pass
        else:
            metrics['r2'] = ResultFormatter.format_float(r2_score(y, y_pred), 4)
            metrics['rmse'] = ResultFormatter.format_float(np.sqrt(mean_squared_error(y, y_pred)), 4)
            
        return metrics, plots

    def _explain(self, model, X, features):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        if isinstance(shap_values, list): 
            shap_values = shap_values[1]
        
        feature_importance = np.abs(shap_values).mean(axis=0)
        importance_df = pd.DataFrame({
            'feature': features,
            'importance': feature_importance
        }).sort_values(by='importance', ascending=False)
        
        return importance_df.to_dict(orient='records')

class RandomForestStrategy(TreeModelStrategy):
    def __init__(self):
        super().__init__('random_forest')

class XGBoostStrategy(TreeModelStrategy):
    def __init__(self):
        super().__init__('xgboost')
