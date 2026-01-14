"""
app.services.model_selection_service.py

提供自动化的变量筛选功能，包括逐步回归 (Stepwise Selection) 和 LASSO 回归。
支持线性回归 (Linear)、逻辑回归 (Logistic) 和 Cox 比例风险回归 (Cox)。
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from lifelines import CoxPHFitter
from sklearn.linear_model import LassoCV, LogisticRegressionCV
from sklearn.preprocessing import StandardScaler

class ModelSelectionService:

    @staticmethod
    def run_stepwise_selection(df, target, features, model_type, direction='both', criterion='aic'):
        """
        执行逐步回归变量筛选。
        
        Args:
            df (pd.DataFrame): 数据集。
            target (str|dict): 结局变量。
            features (list): 候选变量列表。
            model_type (str): 'linear', 'logistic', 'cox'。
            direction (str): 'forward', 'backward', 'both'。
            criterion (str): 'aic' 或 'bic'。
            
        Returns:
            dict: {
                'selected_features': list,
                'steps': list,
                'eliminated_features': list
            }
        """
        if model_type == 'cox':
            return ModelSelectionService._stepwise_cox(df, target, features, direction, criterion)
        else:
            return ModelSelectionService._stepwise_statsmodels(df, target, features, model_type, direction, criterion)

    @staticmethod
    def _stepwise_statsmodels(df, target, features, model_type, direction, criterion):
        """针对 statsmodels 支持的模型 (Linear, Logistic) 的逐步回归"""
        remaining = set(features)
        selected = []
        best_score = float('inf')
        steps = []
        
        # 结果包装
        def get_score(current_features):
            if not current_features:
                return float('inf')
            X = sm.add_constant(df[current_features])
            try:
                if model_type == 'linear':
                    model = sm.OLS(df[target], X).fit()
                else: # logistic
                    model = sm.Logit(df[target], X).fit(disp=0)
                return model.aic if criterion == 'aic' else model.bic
            except:
                return float('inf')

        # 初始分值 (空模型或全模型)
        if direction == 'backward':
            selected = list(features)
            remaining = set()
            best_score = get_score(selected)

        changed = True
        while changed:
            changed = False
            
            # Forward step
            if direction in ['forward', 'both'] and remaining:
                scores_with_candidates = []
                for candidate in remaining:
                    score = get_score(selected + [candidate])
                    scores_with_candidates.append((score, candidate))
                
                scores_with_candidates.sort()
                best_candidate_score, best_candidate = scores_with_candidates[0]
                
                if best_candidate_score < best_score:
                    remaining.remove(best_candidate)
                    selected.append(best_candidate)
                    best_score = best_candidate_score
                    changed = True
                    steps.append(f"Add {best_candidate} (Score: {best_score:.2f})")
            
            # Backward step
            if direction in ['backward', 'both'] and selected:
                scores_with_removal = []
                for candidate in selected:
                    current_subset = [f for f in selected if f != candidate]
                    score = get_score(current_subset)
                    scores_with_removal.append((score, candidate))
                
                scores_with_removal.sort()
                best_removal_score, worst_candidate = scores_with_removal[0]
                
                if best_removal_score < best_score:
                    selected.remove(worst_candidate)
                    remaining.add(worst_candidate)
                    best_score = best_removal_score
                    changed = True
                    steps.append(f"Remove {worst_candidate} (Score: {best_score:.2f})")
            
            if direction == 'forward' and not changed: break
            if direction == 'backward' and not changed: break

        return {
            'selected_features': selected,
            'eliminated_features': list(set(features) - set(selected)),
            'steps': steps,
            'final_score': best_score
        }

    @staticmethod
    def _stepwise_cox(df, target, features, direction, criterion):
        """针对 Cox 模型的逐步回归"""
        from lifelines import CoxPHFitter
        
        remaining = set(features)
        selected = []
        best_score = float('inf')
        steps = []
        
        time_col = target['time']
        event_col = target['event']

        def get_score(current_features):
            if not current_features:
                return float('inf')
            cph = CoxPHFitter()
            try:
                cph.fit(df[[time_col, event_col] + current_features], duration_col=time_col, event_col=event_col)
                # AIC = -2 * LL + 2 * k
                # BIC = -2 * LL + k * log(n)
                ll = cph.log_likelihood_
                k = len(current_features)
                n = len(df)
                if criterion == 'aic':
                    return -2 * ll + 2 * k
                else:
                    return -2 * ll + k * np.log(n)
            except:
                return float('inf')

        if direction == 'backward':
            selected = list(features)
            remaining = set()
            best_score = get_score(selected)

        changed = True
        while changed:
            changed = False
            
            if direction in ['forward', 'both'] and remaining:
                scores_with_candidates = []
                for candidate in remaining:
                    score = get_score(selected + [candidate])
                    scores_with_candidates.append((score, candidate))
                
                scores_with_candidates.sort()
                best_candidate_score, best_candidate = scores_with_candidates[0]
                
                if best_candidate_score < best_score:
                    remaining.remove(best_candidate)
                    selected.append(best_candidate)
                    best_score = best_candidate_score
                    changed = True
                    steps.append(f"Add {best_candidate} (Score: {best_score:.2f})")
            
            if direction in ['backward', 'both'] and selected:
                scores_with_removal = []
                for candidate in selected:
                    current_subset = [f for f in selected if f != candidate]
                    score = get_score(current_subset)
                    scores_with_removal.append((score, candidate))
                
                scores_with_removal.sort()
                best_removal_score, worst_candidate = scores_with_removal[0]
                
                if best_removal_score < best_score:
                    selected.remove(worst_candidate)
                    remaining.add(worst_candidate)
                    best_score = best_removal_score
                    changed = True
                    steps.append(f"Remove {worst_candidate} (Score: {best_score:.2f})")
            
            if not changed: break

        return {
            'selected_features': selected,
            'eliminated_features': list(set(features) - set(selected)),
            'steps': steps,
            'final_score': best_score
        }

    @staticmethod
    def run_lasso_selection(df, target, features, model_type):
        """
        执行 LASSO 变量筛选。
        """
        # 数据标准化 (LASSO 必需)
        scaler = StandardScaler()
        X = df[features]
        X_scaled = scaler.fit_transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=features)
        
        selected = []
        importance = []

        if model_type == 'linear':
            y = df[target]
            lasso = LassoCV(cv=5, random_state=42).fit(X_scaled, y)
            coefs = lasso.coef_
        elif model_type == 'logistic':
            y = df[target]
            # LogisticRegressionCV doesn't have a simple 'l1' path with coef_ for selection easily?
            # Actually it does.
            clf = LogisticRegressionCV(cv=5, penalty='l1', solver='liblinear', random_state=42).fit(X_scaled, y)
            coefs = clf.coef_[0]
        elif model_type == 'cox':
            # Lifelines LASSO
            time_col = target['time']
            event_col = target['event']
            # We need to scale but lifelines likes dataframes
            df_scaled = X_scaled_df.copy()
            df_scaled[time_col] = df[time_col].values
            df_scaled[event_col] = df[event_col].values
            
            # Lifelines doesn't have built-in LassoCV. 
            # We'll use a moderate penalizer or a small grid if we want to be fancy.
            # For now, let's use a heuristic or a fixed penalizer that yields sparse results.
            cph = CoxPHFitter(penalizer=0.1, l1_ratio=1.0)
            cph.fit(df_scaled, duration_col=time_col, event_col=event_col)
            coefs = cph.params_.values
        
        for feat, coef in zip(features, coefs):
            if abs(coef) > 1e-5: # Threshold for selection
                selected.append(feat)
            importance.append({
                'variable': feat,
                'coefficient': float(coef),
                'absolute_coefficient': float(abs(coef))
            })
            
        importance.sort(key=lambda x: x['absolute_coefficient'], reverse=True)
        
        return {
            'selected_features': selected,
            'eliminated_features': list(set(features) - set(selected)),
            'importance': importance
        }
