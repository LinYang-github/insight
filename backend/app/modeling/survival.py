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
    def fit(self, df: pd.DataFrame, target: dict, features: list, params: dict) -> dict:
        """
        拟合 Cox 模型。

        Args:
            df (pd.DataFrame): 经过预处理的数据集（已完成 One-Hot 编码）。
            target (dict): 包含 'time' (生存时间列名) 和 'event' (终点事件列名) 的字典。
            features (list): 协变量列表。
            params (dict): 模型参数。

        Returns:
            dict: 格式化后的模型结果。

        Raises:
            ValueError: 
                - 当 Event 列只有一种取值（无法建模）时。
                - 当检测到奇异矩阵或完全分离（Perfect Separation）时。
        """
        time_col = target['time']
        event_col = target['event']
        
        # Check for low variance in event column
        # Cox 模型要求 Event 必须至少有两个水平 (0/1)，否则无法比较风险差异。
        if df[event_col].nunique() < 2:
             raise ValueError(f"Event column '{event_col}' must have at least 2 unique values (0 and 1).")
             
        data = df[features + [time_col, event_col]]
        cph = CoxPHFitter()
        
        try:
            cph.fit(data, duration_col=time_col, event_col=event_col)
        except Exception as e:
            err_msg = str(e).lower()
            
            # 诊断导致完全分离的具体变量 (culprit)
            culprit = self._diagnose_separation(data, features, event_col)
            culprit_msg = f"\n可能的问题变量：{culprit} (在某一组中方差极低或完全分离)" if culprit else ""
 
            if 'singular matrix' in err_msg:
                raise ValueError(f"模型计算失败：检测到严重的多重共线性 (Singular Matrix)。{culprit_msg}\n建议移除该变量后重试。")
            if 'low variance' in err_msg or 'complete separation' in err_msg or 'converge' in err_msg or 'nan' in err_msg:
                 raise ValueError(f"模型收敛失败：检测到完全分离 (Perfect Separation) 或数据异常。{culprit_msg}\n详细错误：{str(e)}\n建议：检查并移除样本量极少或分布极不平衡的特征变量。")
            raise e
            
        # PH 假定校验 (Proportional Hazard Test)
        from lifelines.statistics import proportional_hazard_test
        ph_test_results = None
        try:
             # decimals=3 用于四舍五入
             ph_test = proportional_hazard_test(cph, data, time_transform='km')
             ph_test_results = ph_test
        except Exception as e:
             pass

        # --- 临床评价 (DCA, 校准曲线, 时间依赖 ROC) ---
        from app.services.evaluation_service import EvaluationService
        clinical_eval = {
            'dca': {},
            'calibration': {},
            'roc': {},
            'extended_metrics': {},
            'predictions': {},
            'nomogram': {}
        }
        
        # 1. 生成列线图 (Nomogram)
        try:
            from app.utils.nomogram_generator import NomogramGenerator
            
            original_df = params.get('original_df', data) # 如果缺失，回退到 'data' (已处理过的数据)
            original_features = params.get('original_features', features)
            
            max_t = data[time_col].max()
            qt = np.quantile(data.loc[data[event_col]==1, time_col], [0.25, 0.5, 0.75])
            nomogram_times = sorted(list(set([int(q) for q in qt])))
            
            nomogram_spec = NomogramGenerator.generate_spec(
                cph, 
                original_df, 
                original_features, 
                nomogram_times
            )
            if nomogram_spec:
                clinical_eval['nomogram'] = nomogram_spec
        except Exception as e:
            print(f"列线图生成失败: {e}")
            import traceback
            traceback.print_exc()

        # 2. 确定评价图表的时间点
        try:
            max_dur = data[time_col].max()
            points = []
            
            # 简单启发式判定：如果最大随访时间 > 730 (假设以天为单位的 2 年)，则判定单位为“天”。
            # 否则判定为“月”。
            time_unit = 'months'
            if max_dur > 730:
                time_unit = 'days'
                # 1年, 2年, 3年, 4年, 5年
                candidates = [365, 730, 1095, 1460, 1825]
                for c in candidates:
                     if max_dur > c: points.append(c)
            else:
                time_unit = 'months'
                candidates = [12, 36, 48, 60]
                for c in candidates:
                     if max_dur > c: points.append(c)
            
            # 用户需求：“所有终点” -> 包含最后一次发生事件的时间
            try:
                max_evt_time = int(data.loc[data[event_col]==1, time_col].max())
                # 仅当该时间点与现有时间点有明显区分时才添加 (例如 > 10% 差异)？
                # 为简单起见，直接添加并去重。
                points.append(max_evt_time)
            except: pass
            
            # 去重并排序
            points = sorted(list(set(points)))
            
            clinical_eval['time_unit'] = time_unit
            if not points:
                points = [int(data[time_col].median())]
                
            # 3. 遍历时间点 (细粒度错误处理)
            for t in points:
                # 校准曲线 (Calibration)
                try:
                    cal = EvaluationService.calculate_survival_calibration(cph, data, time_col, event_col, t)
                    clinical_eval['calibration'][t] = cal
                except Exception: pass
                
                # DCA 曲线
                try:
                    dca = EvaluationService.calculate_survival_dca(cph, data, time_col, event_col, t)
                    clinical_eval['dca'][t] = dca
                except Exception: pass
                
                # 时间依赖 ROC
                try:
                    surv_df = cph.predict_survival_function(data, times=[t])
                    y_score = 1 - surv_df.iloc[0].values
                    mask = (data[time_col] > t) | ((data[time_col] <= t) & (data[event_col] == 1))
                    y_true = (data.loc[mask, time_col] <= t).astype(int)
                    y_score_masked = y_score[mask]
                    
                    if len(np.unique(y_true)) > 1:
                        from sklearn.metrics import roc_curve, auc
                        fpr, tpr, _ = roc_curve(y_true, y_score_masked)
                        roc_auc = auc(fpr, tpr)
                        clinical_eval['roc'][t] = {
                            'fpr': fpr.tolist(),
                            'tpr': tpr.tolist(),
                            'auc': roc_auc
                        }
                    
                    # 存储预测值 (用于计算 NRI/IDI)
                    clinical_eval['predictions'][t] = {
                        'y_true': y_true.tolist(),
                        'y_pred': y_score_masked.tolist()
                    }
                except Exception: pass

                # 扩展指标 (Extended Metrics)
                try:
                    ext_metrics = EvaluationService.calculate_survival_metrics_at_t(cph, data, time_col, event_col, t)
                    clinical_eval['extended_metrics'][t] = ext_metrics
                except Exception: pass

        except Exception as e:
            print(f"Cox 临床评价设置失败: {e}")
            # 不应因为评价失败而导致整个模型运行中断

        return self._format_results(cph, ph_test_results, clinical_eval)

    def _diagnose_separation(self, df: pd.DataFrame, features: list, event_col: str) -> "str | None":
        """
        诊断导致完全分离 (Perfect Separation) 的具体变量。

        Strategy:
        1. 检查各特征在 Event=0 和 Event=1 两个子组中是否方差为 0 (Constant)。
           如果某变量在某组中是常数，说明该变量完全预测了结局（例如：所有 'DrugA' 用户都存活）。
        2. 对于名义分类变量，检查列联表 (Crosstab) 是否存在零单元格。

        Args:
           df: 包含数据的数据框.
           features: 特征列表.
           event_col: 结局列名.

        Returns:
           str: 疑似存在问题的变量名，如果未找到则返回 None.
        """
        for feature in features:
            try:
                # 1. 检查各组方差
                # 如果某个特征在 Event=1 或 Event=0 组内是常数，则会导致分离。
                groups = df.groupby(event_col)[feature]
                for name, group in groups:
                    if group.dropna().nunique() <= 1:
                        return feature
                
                # 2. 针对分类变量进行分布不均检测 (例如 5 vs 0)
                # 列联表检查
                if df[feature].nunique() < 10: # 仅检查类似分类的变量
                    ct = pd.crosstab(df[feature], df[event_col])
                    if (ct == 0).any().any():
                         return feature
            except:
                continue
        return None

    def _format_results(self, cph, ph_results=None, clinical_eval=None):
        summary = []
        
        # 如果可用，解析 PH 校验结果
        # ph_results.summary 是一个以变量名为索引的 DataFrame
        ph_table = None
        if ph_results is not None:
             ph_table = ph_results.summary
             
        for name in cph.params_.index:
            ph_p = '-'
            if ph_table is not None and name in ph_table.index:
                 ph_p = ResultFormatter.format_float(ph_table.loc[name, 'p'], 3)

            row = {
                'variable': name,
                'coef': float(cph.params_[name]),
                'se': float(cph.standard_errors_[name]),
                'p_value': float(cph.summary.loc[name, 'p']),
                'hr': float(cph.hazard_ratios_[name]),
                'hr_ci_lower': float(np.exp(cph.confidence_intervals_.loc[name].iloc[0])),
                'hr_ci_upper': float(np.exp(cph.confidence_intervals_.loc[name].iloc[1])),
                'ph_test_p': ph_p # 该值根据格式化器的不同可以是字符串或浮点数
            }
            summary.append(row)
            
        n_events = cph.event_observed.sum()
        k = len(cph.params_)
        ll = cph.log_likelihood_
        bic = -2 * ll + k * np.log(n_events)
        
        metrics = {
            'c_index': ResultFormatter.format_float(cph.concordance_index_, 3),
            'aic': ResultFormatter.format_float(cph.AIC_partial_, 2),
            'bic': ResultFormatter.format_float(bic, 2),
            'log_likelihood': ResultFormatter.format_float(ll, 2),
            'n_events': int(n_events),
            'ph_global_p': float(ph_table.loc['GLOBAL', 'p']) if ph_table is not None and 'GLOBAL' in ph_table.index else None
        }
        
        plots = {}
        if clinical_eval:
             plots['nomogram'] = clinical_eval.get('nomogram')
             plots['roc'] = clinical_eval.get('roc')
             plots['calibration'] = clinical_eval.get('calibration')
             plots['dca'] = clinical_eval.get('dca')

        return {
            'model_type': 'cox',
            'summary': summary,
            'metrics': metrics,
            'clinical_eval': clinical_eval,
            'plots': plots
        }
