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
try:
    import shap
except ImportError:
    shap = None
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

        # 判定任务类型 (Classification 还是 Regression)
        is_classification = False
        if pd.api.types.is_numeric_dtype(y):
             if y.nunique() <= 10 and sorted(y.unique().tolist()) == [0, 1]:
                 is_classification = True
             elif y.nunique() <= 10:
                 is_classification = True # 启发式判定
             else:
                 is_classification = False
        else:
             is_classification = True

        # 对结局变量 Y 进行编码
        if is_classification and not pd.api.types.is_numeric_dtype(y):
             y = pd.Categorical(y).codes
        
        # 对特征变量 X 进行编码 (稳健的分类变量处理)
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
        
        # Extended Params
        min_samples_split = int(params.get('min_samples_split', 2))
        min_samples_leaf = int(params.get('min_samples_leaf', 1))
        
        # XGBoost 特定参数
        subsample = float(params.get('subsample', 1.0))
        colsample_bytree = float(params.get('colsample_bytree', 1.0))

        # 初始化模型
        model = self._init_model(is_classification, n_estimators, max_depth, learning_rate, 
                                 min_samples_split, min_samples_leaf, subsample, colsample_bytree)
        
        # Fit
        model.fit(X, y)
        
        # 模型评估
        metrics, plots = self._evaluate(model, X, y, is_classification)
        
        # 模型解释 (基于 SHAP)
        importance = self._explain(model, X, features)
        
        return {
            'model_type': self.model_type,
            'task': 'classification' if is_classification else 'regression',
            'metrics': metrics,
            'importance': importance,
            'plots': plots
        }
    
    def _init_model(self, is_clf, n_est, depth, lr, min_split, min_leaf, subsample, colsample):
        if self.model_type == 'random_forest':
            if is_clf: 
                return RandomForestClassifier(n_estimators=n_est, max_depth=depth, 
                                            min_samples_split=min_split, min_samples_leaf=min_leaf,
                                            random_state=42)
            else: 
                return RandomForestRegressor(n_estimators=n_est, max_depth=depth,
                                           min_samples_split=min_split, min_samples_leaf=min_leaf,
                                           random_state=42)
        elif self.model_type == 'xgboost':
            if is_clf: 
                return xgb.XGBClassifier(n_estimators=n_est, max_depth=depth, learning_rate=lr, 
                                       subsample=subsample, colsample_bytree=colsample,
                                       random_state=42, eval_metric='logloss')
            else: 
                return xgb.XGBRegressor(n_estimators=n_est, max_depth=depth, learning_rate=lr, 
                                      subsample=subsample, colsample_bytree=colsample,
                                      random_state=42)
        raise ValueError(f"Unknown model type {self.model_type}")

    def _evaluate(self, model, X, y, is_clf):
        metrics = {}
        plots = {}
        y_pred = model.predict(X)
        
        if is_clf:
            y_prob = model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            from app.utils.evaluation import ModelEvaluator
            metrics, plots = ModelEvaluator.evaluate_classification(y, y_prob, y_pred)
            
            # 5 折交叉验证
            try:
                from sklearn.model_selection import cross_val_score
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
                metrics['cv_auc_mean'] = ResultFormatter.format_float(np.mean(cv_scores), 3)
                metrics['cv_auc_std'] = ResultFormatter.format_float(np.std(cv_scores), 3)
            except Exception as e:
                print(f"交叉验证 (CV) 失败: {e}")
                pass
        else:
            metrics['r2'] = ResultFormatter.format_float(r2_score(y, y_pred), 4)
            metrics['rmse'] = ResultFormatter.format_float(np.sqrt(mean_squared_error(y, y_pred)), 4)
            
        return metrics, plots

    def _explain(self, model, X, features):
        feature_importance = None
        
        try:
            if shap is None:
                raise ImportError("未安装 SHAP 库")
 
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            
            if isinstance(shap_values, list): 
                shap_values = shap_values[1]
            
            feature_importance = np.abs(shap_values).mean(axis=0)
            
        except Exception as e:
            # 如果 SHAP 失败 (例如由于字符串无法转换为浮点数)，则使用原生的特征重要性作为回退
            print(f"SHAP 解释失败: {e}。改用原生的特征重要性 (feature_importances_)。")
            if hasattr(model, 'feature_importances_'):
                feature_importance = model.feature_importances_
            else:
                return [{"feature": "重要性不可用 (N/A)", "importance": 0}]

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
