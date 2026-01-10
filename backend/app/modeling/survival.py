"""
app.modeling.survival.py

生存分析模型策略。
包含 Cox 比例风险模型 (Cox Proportional Hazards Model)。
输出包含风险比 (HR, Hazard Ratio) 及 PH 假定校验结果。
"""
from lifelines import CoxPHFitter
import numpy as np
import pandas as pd
from .base import BaseModelStrategy
from app.utils.formatter import ResultFormatter

class CoxStrategy(BaseModelStrategy):
    """
    Cox 比例风险模型策略。
    用于生存数据分析，探究协变量（Covariates）对终点事件（Event）发生风险的影响。
    
    结果说明：
    - HR > 1: 风险增加因素。
    - HR < 1: 保护性因素。
    - ph_test_p: PH 假定校验 P 值。如果 P < 0.05，可能违反比例风险假定，需谨慎解释。
    """
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
            err_msg = str(e).lower()
            
            # Diagnose specific variable causing separation
            culprit = self._diagnose_separation(data, features, event_col)
            culprit_msg = f"\n可能的问题变量：{culprit} (在某一组中方差极低或完全分离)" if culprit else ""

            if 'singular matrix' in err_msg:
                raise ValueError(f"模型计算失败：检测到严重的多重共线性 (Singular Matrix)。{culprit_msg}\n建议移除该变量后重试。")
            if 'low variance' in err_msg or 'complete separation' in err_msg or 'converge' in err_msg or 'nan' in err_msg:
                 raise ValueError(f"模型收敛失败：检测到完全分离 (Perfect Separation) 或数据异常。{culprit_msg}\n详细错误：{str(e)}\n建议：检查并移除样本量极少或分布极不平衡的特征变量。")
            raise e
            
        # PH Assumption Test
        from lifelines.statistics import proportional_hazard_test
        ph_test_results = None
        try:
             # decimals=3 for rounding
             ph_test = proportional_hazard_test(cph, data, time_transform='km')
             ph_test_results = ph_test
        except Exception as e:
             pass

        return self._format_results(cph, ph_test_results)

    def _diagnose_separation(self, df, features, event_col):
        """
        Check for variables that might cause perfect separation or low variance.
        """
        for feature in features:
            try:
                # 1. Check Variance in each group
                # If a feature is constant within the Event=1 or Event=0 group, it causes separation.
                groups = df.groupby(event_col)[feature]
                for name, group in groups:
                    if group.dropna().nunique() <= 1:
                        return feature
                
                # 2. For Categorical with very unbalanced splits (e.g. 5 vs 0)
                # Crosstab check
                if df[feature].nunique() < 10: # Only check categorical-like
                    ct = pd.crosstab(df[feature], df[event_col])
                    if (ct == 0).any().any():
                         return feature
            except:
                continue
        return None

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
