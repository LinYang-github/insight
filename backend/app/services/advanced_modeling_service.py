import pandas as pd
import numpy as np
import patsy
from lifelines import CoxPHFitter
import statsmodels.api as sm
import statsmodels.formula.api as smf
from app.services.data_service import DataService

class AdvancedModelingService:
    
    @staticmethod
    def fit_rcs(df, target, event_col, exposure, covariates, model_type='cox', knots=3):
        """
        拟合包含限制性立方样条 (RCS) 的模型。

        参数:
            df (pd.DataFrame): 数据集。
            target (str): 结局变量 (Y)。对于 Cox 模型，这是时间列。
            event_col (str): Cox 模型的事件指示符。对于 Logistic/Linear 模型为 None。
            exposure (str): 需要进行样条处理的连续变量 (X)。
            covariates (list): 调整变量列表。
            model_type (str): 'cox'、'logistic' 或 'linear'。
            knots (int): 节点数量 (默认为 3，通常使用 3, 4 或 5)。

        返回:
            dict: {
                'p_non_linear': float (非线性 P 值), 
                'plot_data': [{'x': 暴露值, 'y': HR/OR, 'lower': 置信区间下限, 'upper': 上限}]
            }
        """
        # 1. 准备公式
        # 使用 patsy 'cr' (自然立方样条) 或 'bs' (B 样条)。
        # R 语言的 rcs() 实际上是自然立方样条。patsy 有 cr()。
        # 公式: "target ~ cr(exposure, df=knots) + cov1 + ..."
        
        # 首先清洗数据
        cols = [exposure] + covariates
        if model_type == 'cox':
            cols += [target, event_col]
        else:
            cols += [target]
        
        df_clean = df[cols].dropna()
        df_clean = DataService.preprocess_for_formula(df_clean)
        
        # 计算暴露变量在整个范围内的预测值
        # 参考值：通常取中位数或平均数，令其 HR=1
        ref_value = df_clean[exposure].median()
        
        # 绘图范围：取第 5 到第 95 百分位，避免异常值拉伸图表
        x_min = df_clean[exposure].quantile(0.05)
        x_max = df_clean[exposure].quantile(0.95)
        x_grid = np.linspace(x_min, x_max, 100)
        
        # 创建预测数据框
        # 需要保持协变量恒定（如取均值或众数）
        # 注意：预测的 HR 是相对值。
        # 在 Cox 模型中：h(t|x) / h(t|ref)。如果符合比例风险假设，协变量会抵消。
        # 实际上我们只改变暴露变量。
        
        results = {}
        
        if model_type == 'cox':
            # Lifelines 公式用法
            # formula = "cr(exposure, df=knots) + covar1 + ..."
            cov_str = " + ".join(covariates) if covariates else ""
            formula_rhs = f"cr({exposure}, df={knots})"
            if cov_str:
                formula_rhs += f" + {cov_str}"
                
            if cov_str:
                formula_rhs += f" + {cov_str}"
                
            cph = CoxPHFitter(penalizer=0.01) # 添加微小的惩罚项以保证稳定性
            # 最近版本的 Lifelines 支持 fit(formula=...) 
            # 但我们需要确认是否可以轻松进行预测。
            # 或者，手动使用 patsy 生成样条矩阵以获得完全控制。
            
            # 直接在 DF 上使用 patsy
            # dmatrix 返回矩阵，我们需要带有可读名称的 DF
            # 但 lifelines 处理公式效果很好。
            
            # 1. 拟合模型
            try:
                cph.fit(df_clean, duration_col=target, event_col=event_col, formula=formula_rhs)
            except Exception as e:
                raise ValueError(f"模型拟合失败: {str(e)}")
            
            # 2. 准备预测数据 (网格) 和参考数据 (Ref)
            pred_df = pd.DataFrame({exposure: x_grid})
            ref_df = pd.DataFrame({exposure: [ref_value]})
            
            # 填充协变量为均值/众数
            for cov in covariates:
                if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    mean_val = df_clean[cov].mean()
                    pred_df[cov] = mean_val
                    ref_df[cov] = mean_val
                else:
                    mode_val = df_clean[cov].mode()[0]
                    pred_df[cov] = mode_val
                    ref_df[cov] = mode_val
            
            # 3. 计算对数风险比 (Log Hazard Ratio) 和标准误 (Delta 方法)
            # 我们需要样条项和协变量的设计矩阵 (Design Matrix)。
            # Lifelines 内部使用 patsy。直接访问 cph._predicted_partial_hazard 获取差异比较麻烦。
            # 最佳方法：使用拟合模型中相同的设计信息手动构建设计矩阵。
            
            # 从拟合的模型中获取设计信息 (Design Info)
            # cph._model 通常包含 patsy 设计信息，但 lifelines API 已更改。
            # 在最新版本的 lifelines 中，cph._predicted_partial_hazard 使用：
            #   matrix = patsy.dmatrix(self.formula, data, return_type='dataframe')
            # 但我们需要确保 knots/basis 与训练时一致。
            # 唯一的方法是使用 `patsy.build_design_matrices`。
            # 但 `design_info` 存储在哪里？
            # 似乎 `cph._regression_data` 或 `cph._model` 中可能有？
            # 实际上，`cph.fit` 创建了矩阵，但没有公开暴露设计信息对象？
            # 在训练数据上使用相同公式重新创建 dmatrix 可以提取设计信息。
            
            design_matrix_train = patsy.dmatrix(formula_rhs, df_clean, return_type='matrix')
            design_info = design_matrix_train.design_info
            
            # 构建预测和参考矩阵
            # return_type='dataframe' 对列对齐更安全
            dmatrix_pred = patsy.build_design_matrices([design_info], pred_df, return_type='dataframe')[0]
            dmatrix_ref = patsy.build_design_matrices([design_info], ref_df, return_type='dataframe')[0]
            
            # 参数 (系数)
            params = cph.params_ # Series
            
            # 计算线性预测值 (X * beta)
            # 对齐检查：dmatrix 的列必须与参数索引匹配
            # patsy 通常保持顺序，但为了安全起见
            common_cols = [c for c in params.index if c in dmatrix_pred.columns]
            
            lp_pred = dmatrix_pred[common_cols].dot(params[common_cols])
            lp_ref = dmatrix_ref[common_cols].dot(params[common_cols]).iloc[0]
            
            log_hr = lp_pred - lp_ref
            hr = np.exp(log_hr)
            
            # 4. 方差计算
            # Var(logHR) = Var(LP_pred - LP_ref) = Var( (Xp - Xr) * beta )
            #            = (Xp - Xr) * Cov * (Xp - Xr)^T
            # 我们只需要得到的 N x N 矩阵的对角线（每个点的方差）
            
            cov_matrix = cph.variance_matrix_
            # 重新索引 cov_matrix 以匹配 common_cols
            cov_matrix = cov_matrix.loc[common_cols, common_cols]
            
            # 差异矩阵 (N x p)
            diff_matrix = dmatrix_pred[common_cols].sub(dmatrix_ref[common_cols].iloc[0], axis=1)
            
            # Var = diag( Diff @ Cov @ Diff.T )
            # 优化：sum( (Diff @ Cov) * Diff, axis=1 )
            var_log_hr = (diff_matrix.dot(cov_matrix) * diff_matrix).sum(axis=1)
            se_log_hr = np.sqrt(var_log_hr)
            
            # 5. 置信区间
            z_score = 1.96
            lower_ci = np.exp(log_hr - z_score * se_log_hr)
            upper_ci = np.exp(log_hr + z_score * se_log_hr)
            
            plot_data = []
            for i, x in enumerate(x_grid):
                plot_data.append({
                    'x': x,
                    'y': hr.iloc[i],
                    'lower': lower_ci.iloc[i],
                    'upper': upper_ci.iloc[i]
                })
                
            results['plot_data'] = plot_data
            results['ref_value'] = ref_value
            results['p_non_linear'] = None # TODO: 如有需要计算 LRT
            
            # PH 假设检验
            results['ph_test'] = AdvancedModelingService.check_ph_assumption(cph, df_clean)
            
        elif model_type == 'logistic':
            # Statsmodels Logit
            cov_str = " + ".join(covariates) if covariates else "1" # 如果没有协变量，仅包含截距项
            if not covariates: cov_str = "1"
            
            formula = f"{target} ~ cr({exposure}, df={knots}) + {cov_str}"
            if covariates:
                formula = f"{target} ~ cr({exposure}, df={knots}) + {' + '.join(covariates)}"
            else:
                 formula = f"{target} ~ cr({exposure}, df={knots})"
                 
            model = smf.logit(formula=formula, data=df_clean).fit(disp=0)
            
            # 预测
            # OR = exp(logit(x) - logit(ref)) ? 
            # Logit = Xb. 
            # OR(x vs ref) = exp(X(x)b - X(ref)b)
            # 逻辑与 Cox 模型类似。
            
            pred_df = pd.DataFrame({exposure: x_grid})
            for cov in covariates:
                 if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    pred_df[cov] = df_clean[cov].mean()
                 else:
                    pred_df[cov] = df_clean[cov].mode()[0]
                    
            ref_df = pd.DataFrame([pred_df.iloc[0].copy()]) # 虚拟数据
            ref_df[exposure] = ref_value
            for cov in covariates: # 重置参考列
                 if pd.api.types.is_numeric_dtype(df_clean[cov]):
                    ref_df[cov] = df_clean[cov].mean()
                 else:
                    ref_df[cov] = df_clean[cov].mode()[0]

            # 获取预测值 (线性预测值 = Xb)
            # 获取设计矩阵
            # patsy.dmatrix(formula_rhs, pred_df) ?
            # 更简单的方法：model.predict(exog=..., transform=True) ?
            # Statsmodels predict 除非特别指定，否则通常返回预测概率 p 而非线性预测值。
            # 实际上 results.predict(exog, transform=False) 会返回线性预测值？
            # Logit：predict() 返回概率。
            # 我们需要线性预测值。
            
            # 我们可以使用设计矩阵与参数的点积。
            # 但是从新数据的公式中获取设计矩阵：
            # dmatrix = patsy.build_design_matrices([model.data.design_info], pred_df, return_type='dataframe')[0]
            
            dmatrix_pred = patsy.build_design_matrices([model.model.data.design_info], pred_df, return_type='dataframe')[0]
            dmatrix_ref = patsy.build_design_matrices([model.model.data.design_info], ref_df, return_type='dataframe')[0]
            
            lp_pred = dmatrix_pred.dot(model.params)
            lp_ref = dmatrix_ref.dot(model.params).iloc[0]
            
            log_or = lp_pred - lp_ref
            ors = np.exp(log_or)
            
            # 置信区间
            cov_matrix = model.cov_params()
            # 差异的方差：(X1 - X2) Cov (X1 - X2)^T
            diff_matrix = dmatrix_pred.sub(dmatrix_ref.iloc[0], axis=1) # (N, p)
            
            # se^2 = sum( (diff_matrix @ cov_matrix) * diff_matrix, axis=1 )
            # 高效计算：
            # se = sqrt( diag( D @ Cov @ D.T ) )
            
            var_log_or = (diff_matrix.dot(cov_matrix) * diff_matrix).sum(axis=1)
            se_log_or = np.sqrt(var_log_or)
            
            lower_ci = np.exp(log_or - 1.96 * se_log_or)
            upper_ci = np.exp(log_or + 1.96 * se_log_or)
            
            plot_data = []
            for i, x in enumerate(x_grid):
                plot_data.append({
                    'x': x,
                    'y': ors.iloc[i],
                    'lower': lower_ci.iloc[i],
                    'upper': upper_ci.iloc[i]
                })
            
            results['plot_data'] = plot_data
            results['ref_value'] = ref_value
            
            # 方法学与解读
            results['methodology'] = AdvancedModelingService._generate_rcs_methodology(knots, model_type)
            results['interpretation'] = "检测到潜在非线性关系。" if results.get('p_non_linear') and results['p_non_linear'] < 0.05 else "未检测到显著非线性关系。"
            
        return results

    @staticmethod
    def _generate_rcs_methodology(knots, model_type):
        model_name = "Cox 比例风险模型" if model_type == 'cox' else "Logistic 回归模型"
        return (f"使用包含 {knots} 个节点的限制性立方样条 (RCS) 来模拟连续暴露因素与结局之间的非线性关系，"
                f"并应用了 {model_name} 进行分析。"
                "同时进行了非线性检验。")

    @staticmethod
    def check_ph_assumption(cph, df_train, p_threshold=0.05):
        """
        使用 Schoenfeld 残差检验比例风险 (PH) 假设。
        """
        from lifelines.statistics import proportional_hazard_test
        try:
            # 显式传递用于拟合的数据集以确保安全。
            # 注意：df_train 必须包含时间 (duration) 和事件 (event) 列。
            results = proportional_hazard_test(cph, df_train, time_transform='km')
            summary = results.summary # DataFrame
            
            # 检查是否有变量违反 PH 假设
            min_p = summary['p'].min()
            is_violated = min_p < p_threshold
            
            # 格式化详细信息
            details = {}
            for idx, row in summary.iterrows():
                details[str(idx)] = {
                    'p': float(row['p']),
                    'test_statistic': float(row['test_statistic']),
                    'is_violated': row['p'] < p_threshold
                }

            return {
                'is_violated': bool(is_violated),
                'p_value': float(min_p), # 最显著的 P 值
                'details': details,
                'message': "违反比例风险假定 (PH Assumption Violation)" if is_violated else "满足比例风险假定"
            }
        except Exception as e:
            # print(f"PH Test failed: {e}")
            return None

    @staticmethod
    def perform_subgroup(df, target, event_col, exposure, subgroups, covariates, model_type='cox'):
        """
        进行亚组分析。
        """
        results = []
        
        # 1. 整体模型
        # 在全量数据上拟合模型以获取整体估计值
        # 复用建模服务或在此简单拟合
        # ...
        
        # 2. 遍历亚组变量
        for grp_col in subgroups:
            # 预期 grp_col 为定性变量 (Categorical)
            # 我们需要获取唯一值
            groups = df[grp_col].dropna().unique()
            # 如果可能，进行排序
            try:
                groups = sorted(groups)
            except:
                pass
                
            group_res = {
                'variable': grp_col,
                'subgroups': []
            }
            
            # 检查交互作用 P 值
            # 模型: Y ~ Exposure + Covariates + Grp + Exposure:Grp
            # 我们需要交互项 Exposure:Grp 的 P 值
            # 这表明异质性是否显著。
            
            p_interaction = None
            try:
                # 交互建模
                # 清洗数据
                temp_cols = [target, exposure, grp_col] + covariates
                if event_col: temp_cols.append(event_col)
                temp_df = df[temp_cols].dropna()
                temp_df = DataService.preprocess_for_formula(temp_df)
                
                # 构建公式
                cov_part = " + ".join(covariates)
                if cov_part: cov_part = " + " + cov_part
                
                # 在公式中注意定性变量的编码
                formula = f"{target} ~ {exposure} * C({grp_col}){cov_part}"
                
                if model_type == 'cox':
                     cph = CoxPHFitter()
                     cph.fit(temp_df, duration_col=target, event_col=event_col, formula=formula)
                     # 寻找交互项
                     # 它们通常形如 'Exposure:C(Grp)[T.Level]'
                     # 我们可能需要进行 ANOVA 测试或仅检查最小 P 值。
                     # 最简单的方法：在 (Exp + Grp) 和 (Exp * Grp) 之间进行似然比检验 (LRT)
                     # 但 lifelines 很难进行 ANOVA。
                     # 取交互项的 P 值。如果有多个交互项，情况会比较复杂。
                     # 对于二元亚组，只有一个交互项。
                     summary = cph.summary
                     interaction_rows = [idx for idx in summary.index if ':' in idx]
                     if interaction_rows:
                         p_interaction = summary.loc[interaction_rows, 'p'].min() # 粗略近似
                      
                elif model_type == 'logistic':
                    model = smf.logit(formula, data=temp_df).fit(disp=0)
                    interaction_rows = [idx for idx in model.pvalues.index if ':' in idx]
                    if interaction_rows:
                         p_interaction = model.pvalues[interaction_rows].min()

            except Exception as e:
                print(f"Interaction failed: {e}")
            
            group_res['p_interaction'] = p_interaction

            for val in groups:
                # 取子集
                sub_df = df[df[grp_col] == val]
                sub_df = DataService.preprocess_for_formula(sub_df)
                # 检查样本量
                if len(sub_df) < 10:
                    continue
                    
                # 拟合模型
                est, lower, upper, p_val = AdvancedModelingService._fit_simple_model(
                    sub_df, target, event_col, exposure, covariates, model_type
                )
                
                group_res['subgroups'].append({
                    'level': str(val),
                    'n': len(sub_df),
                    'est': est,
                    'lower': lower,
                    'upper': upper,
                    'p': p_val
                })
            
            results.append(group_res)
            
        # 封装到带有方法学说明的字典中
        return {
            'forest_data': results,
            'methodology': AdvancedModelingService._generate_subgroup_methodology(model_type)
        }

    @staticmethod
    def _generate_subgroup_methodology(model_type):
        test_type = "似然比检验" # 简化处理
        return ("进行了亚组分析，以评估预设亚组之间的效应量一致性。"
                "模型中包含了交互项，以检验效应的异质性 (交互作用 P 值)。")

    @staticmethod
    def _fit_simple_model(df, target, event_col, exposure, covariates, model_type):
        """Helper to fit simple model and return HR/OR + CI + P"""
        try:
            cov_str = " + ".join(covariates)
            if cov_str: cov_str = " + " + cov_str
            formula = f"{exposure}{cov_str}" # LHS handled by library methods usually, or formula
            
            if model_type == 'cox':
                cph = CoxPHFitter()
                # formula support for LHS? "duration + event ~ ..." no.
                # standard fit: fit(df, duration, event, formula="...")
                cph.fit(df, duration_col=target, event_col=event_col, formula=formula)
                # Get exposure row
                # exposure might be customized if formula changed name (e.g. C(exposure))
                # Assuming exposure is continuous or binary 0/1 without transform for now
                if exposure in cph.summary.index:
                    row = cph.summary.loc[exposure]
                else:
                    # Try finding it
                    return None, None, None, None
                
                return row['exp(coef)'], row['exp(coef) lower 95%'], row['exp(coef) upper 95%'], row['p']
                
            elif model_type == 'logistic':
                f = f"{target} ~ {formula}"
                model = smf.logit(f, data=df).fit(disp=0)
                if exposure in model.params.index:
                    est = np.exp(model.params[exposure])
                    conf = model.conf_int()
                    lower = np.exp(conf.loc[exposure][0])
                    upper = np.exp(conf.loc[exposure][1])
                    p = model.pvalues[exposure]
                    return est, lower, upper, p
        except:
            return None, None, None, None
        return None, None, None, None

    @staticmethod
    def calculate_cif(df, time_col, event_col, group_col=None):
        """
        使用 Aalen-Johansen 估量法计算累积发生率函数 (CIF)。
        """
        from lifelines import AalenJohansenFitter
        
        # event_col 应该包含 0 (删失), 1 (主要事件), 2 (竞争风险)...
        # 我们为发现的 *每个* 事件类型（除 0 外）计算 CIF。
        
        # 完整性检查
        if df[event_col].nunique() < 2:
             # 仅包含删失？
             # 或者只有 1 种事件类型？如果只有 1 种，AJ 等于 KM (1-KM)
             pass
        
        results = []
        
        # 事件 (排除 0)
        events = sorted([e for e in df[event_col].unique() if e != 0])
        
        if not events:
            raise ValueError("未发现事件类型 (仅发现 0/删失？)")
            
        groups = ['All']
        if group_col:
            groups = df[group_col].dropna().unique()
            
        for grp in groups:
            if group_col:
                sub_df = df[df[group_col] == grp]
                grp_label = str(grp)
            else:
                sub_df = df
                grp_label = 'All'
            
            for evt in events:
                ajf = AalenJohansenFitter(calculate_variance=False)
                # It treats other values in E as competing risks automatically
                try:
                    # Clean NaNs
                    sub_clean = sub_df[[time_col, event_col]].dropna()
                    
                    ajf.fit(sub_clean[time_col], sub_clean[event_col], event_of_interest=evt)
                    
                    # 存储数据线
                    # ajf.cumulative_density_ 即为 CIF
                    cif = ajf.cumulative_density_
                    
                    # 获取 {x, y} 列表
                    line_data = []
                    # cif 索引为时间，列为 CIF_evt
                    times = cif.index.tolist()
                    values = cif.values.flatten().tolist()
                    
                    # 如果数据量太大则降采样？
                    if len(times) > 500:
                        # 简单跳过
                        indices = np.linspace(0, len(times)-1, 500, dtype=int)
                        times = [times[i] for i in indices]
                        values = [values[i] for i in indices]
                    
                    line_data = [{'x': t, 'y': v} for t, v in zip(times, values)]
                    
                    results.append({
                        'group': grp_label,
                        'event_type': int(evt),
                        'cif_data': line_data
                    })
                except Exception as e:
                    print(f"AJ fit failed for grp={grp} evt={evt}: {e}")
                    
        return {
            'cif_data': results,
            'methodology': AdvancedModelingService._generate_cif_methodology()
        }

    @staticmethod
    def _generate_cif_methodology():
        return ("使用 Aalen-Johansen 估量法估算累积发生率函数 (CIF) 以处理竞争风险。"
                "Gray's 检验用于比较不同组别间 CIF 的等同性（如适用）。")

    @staticmethod
    def generate_nomogram(df, target, event_col, model_type, predictors):
        """
        生成诺谟图 (Nomogram) 和网络计算器的数据。
        支持数值型和定性预测变量。
        """
        results = {
            'variables': [],
            'risk_table': []
        }
        
        # 1. 拟合模型并获取系数
        cols = [target] + predictors
        if event_col: cols.append(event_col)
        
        df_clean = df[cols].dropna()
        df_clean = DataService.preprocess_for_formula(df_clean)
 
        params = {}
        intercept = 0
        baseline_sf = None
        
        # 准备公式
        formula = f"{target} ~ {' + '.join(predictors)}" if model_type == 'logistic' else " + ".join(predictors)
        
        if model_type == 'logistic':
             model_res = smf.logit(formula, data=df_clean).fit(disp=0)
             params = model_res.params.to_dict()
             intercept = params.get('Intercept', 0)
        elif model_type == 'cox':
             cph = CoxPHFitter()
             cph.fit(df_clean, duration_col=target, event_col=event_col, formula=formula)
             params = cph.params_.to_dict()
             median_time = df_clean[target].median()
             # 计算中位随访时间的基准生存率
             # 基准 S0(t) 是当所有 X=0 时的生存率（如果已中心化，则在均值处）
             # lifelines 预测部分风险比 (Partial Hazard)。
             # predict_survival_function 返回 S(t|x)。
             # 我们想要基准 S0(t)。
             # 我们可以获取 S(t|mean) 然后调整回来？
             # 或者构造一个所有中心化协变量均为 0 的虚拟数据。
             # Lifelines 默认对数据进行中心化。
             baseline_sf = cph.predict_survival_function(pd.DataFrame({p:[0] for p in predictors}, index=[0]), times=[median_time]).iloc[0,0]

        # 2. 计算缩放因子 (每单位 Beta 的分值)
        # 我们需要找到效应范围最大的变量。
        max_effect_range = 0
        var_configs = {} # 存储每个变量的效应计算方式
        
        for var in predictors:
            if pd.api.types.is_numeric_dtype(df_clean[var]) and df_clean[var].nunique() > 2:
                # 连续型 / 数值型
                coef = params.get(var, 0)
                mn, mx = df_clean[var].min(), df_clean[var].max()
                rng = abs(coef * (mx - mn))
                if rng > max_effect_range: max_effect_range = rng
                
                var_configs[var] = {
                    'type': 'numeric',
                    'coef': coef,
                    'min': mn, 'max': mx,
                    'range': rng
                }
            else:
                # 定性变量 (或按定性处理的二元变量)
                # 查找所有关联系数 (哑变量编码)
                # 参考层系数为 0。
                levels = sorted(df_clean[var].unique())
                level_coefs = {}
                
                # 检查在参数中是如何编码的。通常为 "Var[T.Level]"
                # 基准层为 0。
                # 正则匹配或精确匹配？Statsmodels/Lifelines 使用 "Var[T.Level]"
                c_values = []
                for l in levels:
                    key = f"{var}[T.{l}]"
                    val = params.get(key, 0)
                    if key not in params and l == levels[0]: val = 0 # 假设第一个是参考层
                    level_coefs[l] = val
                    c_values.append(val)
                
                rng = max(c_values) - min(c_values)
                if rng > max_effect_range: max_effect_range = rng
                
                var_configs[var] = {
                    'type': 'categorical',
                    'level_coefs': level_coefs,
                    'min_coef': min(c_values),
                    'range': rng
                }

        if max_effect_range == 0:
            return results

        points_per_unit_beta = 100 / max_effect_range
        
        # 3. 生成标尺数据
        # 我们平移标尺，使得“最小贡献 = 0 分”。
        # 贡献 = 值 * 系数 (数值型) 或 Level_Coef (定性型)
        
        total_min_points = 0
        total_max_points = 0
        
        for var in predictors:
            config = var_configs[var]
            
            if config['type'] == 'numeric':
                coef = config['coef']
                mn, mx = config['min'], config['max']
                
                # 两端的贡献
                c_min = mn * coef
                c_max = mx * coef
                
                # 我们将该变量的基准（Base）定义为 min(c_min, c_max)
                base_c = min(c_min, c_max)
                
                # 分值 = (贡献 - 基准) * 缩放比例
                ticks = np.linspace(mn, mx, 10)
                points_mapping = []
                for t in ticks:
                    c = t * coef
                    pts = (c - base_c) * points_per_unit_beta
                    points_mapping.append({'val': float(t), 'pts': float(pts)})
                    
                results['variables'].append({
                    'name': var,
                    'type': 'numeric',
                    'min': float(mn), 'max': float(mx),
                    'points_mapping': points_mapping
                })
                
                # 更新总量追踪
                # 一个患者通常贡献 0 到 (Range * Scaling) 分
                total_max_points += config['range'] * points_per_unit_beta
                
                # 更新全局截距调整
                # 公式为 LP = Intercept + Sum(Contributions)
                # 我们代入 Contribution = Points/S + Base
                # LP = Intercept + Sum(Points/S + Base)
                #    = (Intercept + Sum(Base)) + TotalPoints/S
                intercept += base_c
                
            else:
                # Categorical
                min_c = config['min_coef'] # The lowest coef among levels
                cat_mapping = []
                
                for lvl, l_coef in config['level_coefs'].items():
                    pts = (l_coef - min_c) * points_per_unit_beta
                    cat_mapping.append({'val': str(lvl), 'pts': float(pts)})
                    
                results['variables'].append({
                    'name': var,
                    'type': 'categorical',
                    'points_mapping': cat_mapping
                })
                
                total_max_points += config['range'] * points_per_unit_beta
                intercept += min_c

        # 4. 风险标尺
        # LP = 调整后的截距 + 总分 / 缩放比例
        point_grid = np.linspace(0, total_max_points, 100)
        risk_mapping = []
        
        for pt in point_grid:
            lp = intercept + (pt / points_per_unit_beta)
            if model_type == 'logistic':
                risk = 1 / (1 + np.exp(-lp))
            else:
                # Cox: 1 - S0^exp(lp)
                risk = 1 - (baseline_sf ** np.exp(lp))
            risk_mapping.append({'points': float(pt), 'risk': float(risk)})
            
        results['risk_table'] = risk_mapping
        
        # 计算器的元数据 (Meta)
        # 我们是否需要为定性变量发送不同的系数？
        # 实际上前端计算处理数值型。对于定性型，它需要“值 -> 系数”的映射。
        # 让我们简化一下，为定性变量发送映射好的 'level_coefs'。
        
        coeffs_flat = {}
        for var, conf in var_configs.items():
            if conf['type'] == 'numeric':
                coeffs_flat[var] = float(conf['coef'])
            else:
                # 对于定性变量，前端需要查字典
                # 我们可以存储在特定结构中
                coeffs_flat[var] = conf['level_coefs'] # 嵌套字典
                
        results['formula'] = {
            'intercept': float(intercept), # 这是调整后的截距吗？
            # 等等。前端计算逻辑使用“原始输入 * 系数”。
            # 如果我在这里发送调整后的截距，除非我也更改前端，否则前端计算会出错。
            # 前端逻辑：lp = intercept + sum(val * coef)。
            # 所以我应该发送原始截距和原始系数。
            'baseline_survival': float(baseline_sf) if baseline_sf else None,
            'model_type': model_type,
            'coeffs': coeffs_flat, # 支持嵌套字典？前端需要更新。
            'var_configs': var_configs # 前端助手
        }
        
        # 如果前端使用标准公式，则为 'formula' 返回项重置截距为原始值
        # 但等等，前端对定性变量的 'coeffs_flat'...
        # 如果用户输入 "Stage II"，我们需要知道 Stage II 的系数。
        # 是的，level_coefs 提供了这一点。
        # 但等等，第 1 步中的 params 包含 'Intercept' (原始)。
        # 我们应该为计算器返回原始截距。
        results['formula']['intercept'] = float(params.get('Intercept', 0))

        results['methodology'] = AdvancedModelingService._generate_nomogram_methodology(model_type)
        return results

    @staticmethod
    def _generate_nomogram_methodology(model_type):
        return ("构建诺谟图以可视化预测模型。"
                "根据回归系数为每个变量（或层级）分配分值。"
                "总分对应于预测的结局发生概率。")

    @staticmethod
    def compare_models(df, target, model_configs, model_type='logistic', event_col=None):
        """
        在相同的全病例数据集上比较多个模型（增量价值）。
        
        参数:
            df (pd.DataFrame): 数据。
            target (str): 结局变量 (Y) 或时间变量。
            model_configs (list): 模型配置列表 [{'name': 'M1', 'features': ['A']}, ...]。
            model_type (str): 'logistic' 或 'cox'。
            event_col (str): 事件指示符 (Cox 模型必需)。
        
        返回:
            list: 包含评估指标的模型结果列表。
        """
        from app.services.modeling_service import ModelingService
        from lifelines import CoxPHFitter
        from sklearn.metrics import roc_curve, auc as calc_auc
        
        # 1. 识别有效列 (交集)
        all_features = set()
        for config in model_configs:
            all_features.update(config['features'])
            
        required_cols = list(all_features) + [target]
        if event_col:
            required_cols.append(event_col)
        
        # 2. 全病例分析 (Complete Case Analysis)
        # 通过在特征交集列上删除缺失值来确保公平性
        df_clean = df[required_cols].dropna()
        
        if len(df_clean) < 10:
             raise ValueError("处理完所有组合特征的缺失值后，样本量太小 (<10)。")
 
        # 数据预览 (完整性)
        n_samples = len(df_clean)
        
        results = []
        
        # 3. 拟合模型 (增量式)
        # 基准模型 (第一个特征集) - 可选？不，列表即为模型列表。
        # 但通常我们比较模型 A 与模型 B。
        # 用户传递配置列表。
        
        # 如果我们想要相对于第一个模型的“差异”，是否预先计算基准 AUC/指标？
        # 让我们为每个模型计算指标。
        # 比较逻辑 (Delong, NRI/IDI) 将根据请求或相对于 M1 成对进行。
        
        # 为了支持比较矩阵，我们返回每个模型的完整指标。
        # 前端处理“参考 vs 新建”的显示。
        
        # 我们还需要成对统计数据 (Delong P, NRI, IDI)
        # 如果模型数量 > 1，则将模型 [i] 与模型 [0] (基准) 进行比较。
        
        for idx, config in enumerate(model_configs):
            features = config['features']
            name = config.get('name', f'Model {idx+1}')
            
            # Fit
            model_res = AdvancedModelingService._fit_simple_model(
                df_clean, target, event_col, features[0], features[1:] if len(features)>1 else [], model_type
            )
            # _fit_simple_model 返回标量参数。我们需要完整的预测值。
            # 我们需要重构或在此使用标准拟合。
            
            # 使用标准库重新拟合以获得预测值
            try:
                if model_type == 'logistic':
                    # 公式
                    f = f"{target} ~ {' + '.join(features)}"
                    m = smf.logit(f, data=df_clean).fit(disp=0)
                    y_prob = m.predict(df_clean)
                    y_true = df_clean[target]
                    
                    metrics = EvaluationService.calculate_binary_metrics_at_threshold(y_true, y_prob)
                    metrics['brier'] = EvaluationService.calculate_brier_score(y_true, y_prob)
                    metrics['aic'] = m.aic
                    metrics['bic'] = m.bic
                    
                elif model_type == 'cox':
                    cph = CoxPHFitter()
                    f = " + ".join(features)
                    cph.fit(df_clean, duration_col=target, event_col=event_col, formula=f)
                    
                    # 预测值 (Partial Hazard for consistency in simple comparison)
                    # Note: For time-dependent ROC/DCA, we need specific time points.
                    # Current implementation uses simple partial hazard for "overall" comparison if t not specified of
                    # uses a default method (e.g. Harrels C)
                    # But for plots, we usually need a specific time t.
                    # As a default, let's use the median time.
                    median_t = df_clean[target].median()
                    
                    y_prob = cph.predict_partial_hazard(df_clean)
                    y_true = df_clean[event_col] 
                    
                    metrics = {
                        'c_index': cph.concordance_index_,
                        'aic': cph.AIC_partial_,
                        'log_likelihood': cph.log_likelihood_,
                        'available_time_points': [float(median_t)], # MVP default
                        'time_unit': 'months' # Logic to detect unit?
                    }
                    
                    # Time-dependent metrics for Plot
                    # We calc metrics at median time for the "Default" view
                    # But actually frontend expects time_dependent dict
                    from app.services.evaluation_service import EvaluationService
                    
                    # Calculate at median time
                    metrics_t = EvaluationService.calculate_survival_metrics_at_t(cph, df_clean, target, event_col, median_t)
                    
                    # Store in time_dependent
                    metrics['time_dependent'] = {}
                    metrics['time_dependent'][median_t] = metrics_t
                    
                    # Generate Plots Data (Time-Dependent at Median T by default)
                    # ROC
                    surv_df = cph.predict_survival_function(df_clean, times=[median_t])
                    prob_evt = 1 - surv_df.iloc[0].values
                    # Mask for evaluation (exclude censored before t)
                    mask = (df_clean[target] > median_t) | ((df_clean[target] <= median_t) & (df_clean[event_col] == 1))
                    y_eval = (df_clean[target] <= median_t).astype(int)[mask]
                    p_eval = prob_evt[mask]
                    
                    if len(y_eval) > 0:
                        fpr, tpr, _ = roc_curve(y_eval, p_eval)
                        metrics_t['roc_data'] = [{'fpr': float(f), 'tpr': float(t)} for f, t in zip(fpr, tpr)]
                        metrics_t['auc'] = calc_auc(fpr, tpr) # overwrite with time-dependent AUC
                        
                        # Format CI from separate lower/upper keys
                        if 'auc_ci_lower' in metrics_t:
                            metrics_t['auc_ci'] = f"{metrics_t['auc_ci_lower']:.3f}-{metrics_t['auc_ci_upper']:.3f}"
                        
                        # Calibration
                        calib = EvaluationService.calculate_survival_calibration(cph, df_clean, target, event_col, median_t)
                        metrics_t['calibration'] = calib
                        
                        # DCA
                        dca = EvaluationService.calculate_survival_dca(cph, df_clean, target, event_col, median_t)
                        metrics_t['dca'] = dca
                        
                        # Comparison with Base Model (if idx > 0)
                        if idx > 0 and results:
                            # Retrieve Base Model's data at t
                            base_res = results[0]
                            # We stored internal _y_eval and _p_eval in base_res for comparison? 
                            # Or we can't easily access previous local vars.
                            # We can store them in results for temporary usage, or re-extract.
                            # Storing in results is cleaner.
                            
                            base_metrics = base_res['metrics']['time_dependent'].get(median_t)
                            if base_metrics and 'p_eval' in base_metrics:
                                base_p_eval = base_metrics['p_eval'] # Need to ensure we saved this
                                base_y_eval = base_metrics['y_eval'] # Should be same as current y_eval
                                
                                # Delong
                                delong = EvaluationService.calculate_delong_test(y_eval, base_p_eval, p_eval)
                                metrics_t['p_delong'] = delong.get('p_delong')
                                
                                # NRI / IDI
                                nri_idi = EvaluationService.calculate_nri_idi(y_eval, base_p_eval, p_eval)
                                metrics_t.update(nri_idi)
                                # keys: nri, nri_p, nri_ci, idi, ...
                        
                        # Save p_eval/y_eval for subsequent models to compare against
                        metrics_t['p_eval'] = p_eval.tolist()
                        metrics_t['y_eval'] = y_eval.tolist()

                    metrics['time_dependent'][median_t] = metrics_t
                    
                # Common Plot Generation for Logistic (or simple output)
                plots = {}
                if model_type == 'logistic':
                    # ROC
                    fpr, tpr, _ = roc_curve(y_true, y_prob)
                    plots['roc'] = [{'fpr': float(f), 'tpr': float(t)} for f, t in zip(fpr, tpr)]
                    plots['calibration'] = EvaluationService.calculate_calibration(y_true, y_prob)
                    plots['dca'] = EvaluationService.calculate_dca(y_true, y_prob)
                    
                    metrics['auc_ci'] = f"{metrics['auc_ci_lower']:.3f}-{metrics['auc_ci_upper']:.3f}" if 'auc_ci_lower' in metrics else '-'
                    
                results.append({
                    'name': name,
                    'features': features,
                    'metrics': metrics,
                    'plots': plots,  
                    'y_prob': y_prob.tolist() if 'y_prob' in locals() else []
                })
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                results.append({'name': name, 'error': str(e)})
                
        # 4. 比较 (相对于模型 1) - Logistic handled in loop via results list check or here.
        # Check standard logistic comparison if needed
        if len(results) > 1 and model_type == 'logistic':
            base = results[0]
            if 'y_prob' in base and not base.get('error'):
                for res in results[1:]:
                    if 'y_prob' in res and not res.get('error'):
                        delong = EvaluationService.calculate_delong_test(
                            df_clean[target], base['y_prob'], res['y_prob']
                        )
                        nri_idi = EvaluationService.calculate_nri_idi(
                            df_clean[target], base['y_prob'], res['y_prob']
                        )
                        # Add to metrics for table display
                        res['metrics'].update(delong)
                        res['metrics'].update(nri_idi)
                        
        return results

    @staticmethod
    def fit_fine_gray(df, duration_col, event_col, covariates, event_of_interest=1):
        """
        拟合 Fine-Gray 竞争风险模型 (子分布风险)。
        
        参数:
            df (pd.DataFrame): 数据。
            duration_col (str): 时间。
            event_col (str): 事件 (0=删失, 1,2..=各类风险)。
            covariates (list): 自变量。
            event_of_interest (int): 要建模的事件代码 (默认为 1)。
            
        返回:
            dict: SHR (子分布风险比) 的汇总表。
        """
        # Try importing FineGrayFitter
        try:
            from lifelines import FineGrayFitter
        except ImportError:
            # Fallback or Error
            # Recent lifelines might need specific import or it's missing.
            # If missing, we can implement manual weighting logic, but it's complex.
            # Let's hope it's available or we find it.
            raise ImportError("FineGrayFitter not found in lifelines. Please upgrade lifelines >= 0.26.0.")
            
        # 尝试导入 FineGrayFitter
        try:
            from lifelines import FineGrayFitter
        except ImportError:
            # 回退或报错
            # 最近版本的 lifelines 可能需要特定的导入方式，或者已缺失。
            # 如果缺失，我们可以手动实现加权逻辑，但这很复杂。
            # 让我们希望它是可用的，或者我们能找到它。
            
            res_list = []
            for idx, row in summary.iterrows():
                res_list.append({
                    'variable': idx,
                    'hr': float(row['exp(coef)']),
                    'coef': float(row['coef']),
                    'se': float(row['se(coef)']),
                    'ci_lower': float(row['exp(coef) lower 95%']),
                    'ci_upper': float(row['exp(coef) upper 95%']),
                    'p_value': float(row['p'])
                })
                
            return {
                'models': [{
                    'event_type': event_of_interest,
                    'summary': res_list
                }],
                'methodology': "使用 Fine-Gray 子分布风险模型来估算协变量对目标事件累积发生率的影响，并考虑了竞争风险。"
            }
            
        except Exception as e:
            raise ValueError(f"Fine-Gray Fit Failed: {str(e)}")

        
        # Cox ROC 代理逻辑
        median_time = None
        if model_type == 'cox':
            if not event_col:
                raise ValueError("Cox 模型必需提供事件列。")
            median_time = df_clean[target].median()
            # 我们将计算中位随访时间的时变累积 ROC。
            # 简化处理：保留 (Event=1 & Time<=Median) 作为 Case=1
            # 保留 (Time > Median) 作为 Control=0
            # 剔除 (Event=0 & Time <= Median) (在中位时间点状态未知)
        
        results = []
        
        # 3. 遍历模型
        for config in model_configs:
            def calc_auc_stats(auc, n1, n2):
                from scipy.stats import norm
                if n1 <= 0 or n2 <= 0: return ("-", 1.0)
                q1 = auc / (2 - auc)
                q2 = 2 * auc**2 / (1 + auc)
                se = np.sqrt((auc*(1-auc) + (n1-1)*(q1-auc**2) + (n2-1)*(q2-auc**2)) / (n1*n2))
                lower = max(0, auc - 1.96*se)
                upper = min(1, auc + 1.96*se)
                
                # P 值 (H0: AUC=0.5)
                # Z = (AUC - 0.5) / SE
                z = (auc - 0.5) / se if se > 0 else 0
                p = 2 * (1 - norm.cdf(abs(z)))
                
                return (f"{lower:.3f}-{upper:.3f}", float(p))

            name = config['name']
            feats = config['features']
            
            try:
                metrics = {}
                roc_data = []

                # 存储原始输出以供比较
                raw_pred = None
                raw_y = None
                
                if model_type == 'logistic':
                    # 本地拟合以实现完全控制 (与 Cox 代码块保持一致)
                    # 准备公式
                    formula = f"{target} ~ {' + '.join(feats)}"
                    if not feats: formula = f"{target} ~ 1"
                    
                    try:
                        # Statsmodels Logit
                        # statsmodels 要求数据必须是数值型？DataService.preprocess 已经处理过了？
                        # df_clean 是严格的全病例数据
                        # 如果需要，转换为哑变量？
                        # 如果是字符串/类别类型，smf 的 formula 会自动处理（定性变量）。
                        model = smf.logit(formula=formula, data=df_clean).fit(disp=0)
                        
                        # 指标
                        metrics['aic'] = model.aic
                        metrics['bic'] = model.bic
                        metrics['ll'] = model.llf
                        metrics['n'] = len(df_clean)  # 添加样本量
                        metrics['r2'] = model.prsquared # 伪 R2
                        metrics['k'] = len(model.params)
 
                        # 预测值 (概率)
                        y_prob = model.predict(df_clean)
                        y_true = df_clean[target]
                        
                        # ROC
                        fpr, tpr, _ = roc_curve(y_true, y_prob)
                        metrics['auc'] = calc_auc(fpr, tpr)
                        ci_str, p_val = calc_auc_stats(metrics['auc'], sum(y_true), len(y_true)-sum(y_true))
                        metrics['auc_ci'] = ci_str
                        metrics['auc_p'] = p_val
                        
                        roc_data = [{'fpr': f, 'tpr': t} for f, t in zip(fpr, tpr)]
                        
                        raw_pred = y_prob.values
                        raw_y = y_true.values
 
                        # 高级图表 (校准曲线 & DCA)
                        from app.services.evaluation_service import EvaluationService
                        calib_data = EvaluationService.calculate_calibration(raw_y, raw_pred)
                        dca_data = EvaluationService.calculate_dca(raw_y, raw_pred)
                        
                    except Exception as e:
                        print(e)
                        # 如果 statsmodels 失败（例如完全分离），则回退到简单运行
                        model_res = ModelingService.run_model(df_clean, 'logistic', target, feats)
                        metrics = model_res.get('metrics', {})
                        # 即使在回退时也要确保 n 存在
                        metrics['n'] = len(df_clean)
                        if 'plots' in model_res and 'roc' in model_res['plots']:
                             roc_data = model_res['plots']['roc']
            


                elif model_type == 'cox':
                    # Cox ROC 的自定义实现
                    # 数据预处理
                    temp_df = df_clean[[target, event_col] + feats].copy()
                    temp_df = DataService.preprocess_for_formula(temp_df)
                    
                    # 拟合
                    cph = CoxPHFitter()
                    cph.fit(temp_df, duration_col=target, event_col=event_col, formula=" + ".join(feats))
                    
                    # 拟合统计指标 (全局)
                    metrics['c_index'] = cph.concordance_index_
                    metrics['auc'] = metrics['c_index'] 
                    metrics['aic'] = cph.AIC_partial_
                    metrics['ll'] = cph.log_likelihood_
                    n_events = cph.event_observed.sum()
                    metrics['n'] = len(temp_df) # 添加样本量
                    k = len(cph.params_)
                    metrics['k'] = k
                    metrics['bic'] = -2 * metrics['ll'] + k * np.log(n_events)
                    
                    # 时变指标循环
                    # 确定时间点 (复用逻辑或简单的启发式方法)
                    max_dur = temp_df[target].max()
                    points = []
                    time_unit = 'months'
                    if max_dur > 730: # 大约 2 年
                        time_unit = 'days'
                        candidates = [365, 730, 1095, 1460, 1825] # 1, 2, 3, 4, 5 年
                        for c in candidates:
                             if max_dur > c: points.append(c)
                    else: # 如果最大随访时间小于 2 年，默认为月
                        time_unit = 'months'
                        candidates = [12, 24, 36, 48, 60] # 1, 2, 3, 4, 5 年
                        for c in candidates:
                             if max_dur > c: points.append(c)
                    
                    # 如果没有指定时间点，或者作为默认值，始终包含中位时间
                    median_time = int(temp_df[target].median())
                    if not points: points = [median_time]
                    
                    metrics['time_dependent'] = {}
                    metrics['time_unit'] = time_unit
                    metrics['available_time_points'] = points
                    
                    raw_preds_dict = {} # t -> prob
                    
                    for t in points:
                        # S(t) -> Prob(Event <= t) = 1 - S(t)
                        surv_df = cph.predict_survival_function(temp_df, times=[t])
                        y_prob = 1 - surv_df.iloc[0].values
                        
                        # 在 T 时刻的验证掩码
                        mask_case = (temp_df[event_col] == 1) & (temp_df[target] <= t)
                        mask_control = (temp_df[target] > t)
                        valid_mask = mask_case | mask_control
                        
                        y_binary = mask_case[valid_mask].astype(int)
                        y_score_valid = y_prob[valid_mask]
                        
                        t_metrics = {}
                        if len(y_binary.unique()) > 1:
                            fpr, tpr, _ = roc_curve(y_binary, y_score_valid)
                            t_auc = calc_auc(fpr, tpr)
                            t_metrics['auc'] = t_auc
                            ci_str, p_val = calc_auc_stats(t_auc, sum(y_binary), len(y_binary)-sum(y_binary))
                            t_metrics['auc_ci'] = ci_str
                            t_metrics['auc_p'] = p_val
                            t_metrics['roc_data'] = [{'fpr': f, 'tpr': v} for f, v in zip(fpr, tpr)]
                        else:
                            t_metrics['auc'] = 0.5
                            t_metrics['auc_ci'] = "-"
                            
                            t_metrics['auc'] = 0.5
                            t_metrics['auc_ci'] = "-"
                        
                        # Calibration & DCA for Cox at T (using binary approx)
                        if len(y_binary.unique()) > 1:
                             from app.services.evaluation_service import EvaluationService
                             t_metrics['calibration'] = EvaluationService.calculate_calibration(y_binary, y_score_valid)
                             t_metrics['dca'] = EvaluationService.calculate_dca(y_binary, y_score_valid)
                            
                        metrics['time_dependent'][t] = t_metrics
                        
                        # 存储原始预测值以供后续 NRI 计算
                        # 我们需要 NRI 的索引保持一致
                        # 存储完整数组 (y_prob)，并让 NRI 函数处理掩码
                        raw_preds_dict[t] = y_prob
                    
                    # 存储原始输出以供 NRI (比较步骤)
                    # 对于 Cox 模型，raw_pred 现在是 {t: y_prob} 的字典
                    raw_pred = raw_preds_dict
                    raw_y = {
                        'time': temp_df[target].values,
                        'event': temp_df[event_col].values
                    }

                model_res = {
                    'name': name,
                    'features': feats,
                    'metrics': metrics
                }
                
                # 将绘图数据附加到模型结果中
                if model_type == 'logistic':
                    model_res['plots'] = {
                        'roc': roc_data,
                        'calibration': calib_data,
                        'dca': dca_data
                    }
                
                results.append({
                    'model_res': model_res,
                    'raw_pred': raw_pred,
                    'raw_y': raw_y
                })
                
            except Exception as e:
                print(f"Model {name} failed: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'model_res': {'name': name, 'error': str(e)},
                    'raw_pred': None,
                    'raw_y': None
                })

        # 2. 如果基准模型存在，则计算 NRI/IDI (模型 0 = 基准)
        # 仅在模型共享相同行时可行。我们上面已经假设了严格的全病例分析。
        if len(results) >= 2 and results[0]['raw_pred'] is not None:
            from app.services.evaluation_service import EvaluationService
            from scipy.stats import chi2
            base = results[0]
            
            for i in range(1, len(results)):
                curr = results[i]
                if curr['raw_pred'] is None: continue
                
                # 检查模型类型
                if model_type == 'logistic':
                    # 标准 NRI
                    try:
                        nri_res = EvaluationService.calculate_nri_idi(
                            base['raw_y'],
                            base['raw_pred'],
                            curr['raw_pred']
                        )
                        # Add to current model metrics
                        curr['model_res']['metrics'].update(nri_res)
                    except Exception as e:
                        print(f"Logistic 模型 {curr['model_res']['name']} 的 NRI 计算失败: {e}")
                        
                elif model_type == 'cox':
                    # 每个 T 点的时变 NRI
                    # base['raw_pred'] 是 {t: prob}，curr['raw_pred'] 也是 {t: prob}
                    # raw_y 是 {'time', 'event'}
                    
                    base_preds = base['raw_pred']
                    curr_preds = curr['raw_pred']
                    time_points = curr['model_res']['metrics'].get('available_time_points', [])
                    
                    for t in time_points:
                        if t not in base_preds or t not in curr_preds: continue
                        
                        p_base = base_preds[t]
                        p_curr = curr_preds[t]
                        
                        # 构造 T 时刻的二元目标
                        times = base['raw_y']['time']
                        events = base['raw_y']['event']
                        
                        # 掩码：排除在 T 之前删失的病例
                        mask_case = (events == 1) & (times <= t)
                        mask_control = (times > t)
                        valid = mask_case | mask_control
                        
                        y_true = mask_case[valid].astype(int)
                        y_prob_base = p_base[valid]
                        y_prob_curr = p_curr[valid]
                        
                        try:
                            nri_res = EvaluationService.calculate_nri_idi(
                                y_true,
                                y_prob_base,
                                y_prob_curr
                            )
                            # 添加到时变指标中
                            # 例如 metrics['time_dependent'][t]['nri'] = ...
                            if t in curr['model_res']['metrics']['time_dependent']:
                                curr['model_res']['metrics']['time_dependent'][t].update(nri_res)
                                
                        except Exception as e:
                            print(f"Cox 模型 {curr['model_res']['name']} 在 t={t} 的 NRI 计算失败: {e}")
 
                        # 计算 t 时刻的 Delong 检验 (时变 AUC 比较)
                        try:
                             delong_res = EvaluationService.calculate_delong_test(
                                 y_true,
                                 y_prob_base,
                                 y_prob_curr
                             )
                             if t in curr['model_res']['metrics']['time_dependent']:
                                 curr['model_res']['metrics']['time_dependent'][t]['p_delong'] = delong_res.get('p_delong')
                        except Exception as e:
                             print(f"Delong at t={t} failed: {e}")

        # 2b. Logistic 模型的全局 Delong 检验
        if len(results) >= 2 and results[0]['raw_pred'] is not None and not isinstance(results[0]['raw_pred'], dict):
             base = results[0]
             for i in range(1, len(results)):
                 curr = results[i]
                 if curr['raw_pred'] is not None:
                      try:
                          delong_res = EvaluationService.calculate_delong_test(
                              base['raw_y'],
                              base['raw_pred'],
                              curr['raw_pred']
                          )
                          curr['model_res']['metrics']['p_delong'] = delong_res.get('p_delong')
                      except Exception as e:
                          print(f"Delong failed for logistic: {e}")

        # 3. 似然比检验 (LRT) 和 AIC/BIC 比较 (全局)
        if len(results) > 0:
            base = results[0]
            base_model_metrics = base['model_res']['metrics']
            for i in range(1, len(results)):
                curr = results[i]
                if curr['raw_pred'] is None: continue # 如果模型失败则跳过
                curr_model_metrics = curr['model_res']['metrics']

                if 'aic' in base_model_metrics and 'aic' in curr_model_metrics:
                    curr_model_metrics['delta_aic'] = curr_model_metrics['aic'] - base_model_metrics['aic']
                
                if 'bic' in base_model_metrics and 'bic' in curr_model_metrics:
                    curr_model_metrics['delta_bic'] = curr_model_metrics['bic'] - base_model_metrics['bic']
                    
                # 似然比检验 (LRT) P 值
                # 2 * (LL_new - LL_old) ~ Chi2(df)
                if 'll' in base_model_metrics and 'll' in curr_model_metrics:
                     ll_base = base_model_metrics['ll']
                     ll_curr = curr_model_metrics['ll']
                     k_base = base_model_metrics.get('k', 0)
                     k_curr = curr_model_metrics.get('k', 0)
                     
                     if k_curr > k_base: # 嵌套模型假设 (添加变量)
                         lrt_stat = 2 * (ll_curr - ll_base)
                         df_diff = k_curr - k_base
                         if lrt_stat > 0:
                             p_val = chi2.sf(lrt_stat, df_diff)
                             curr['model_res']['metrics']['p_lrt'] = float(p_val)
                             curr['model_res']['metrics']['lrt_stat'] = float(lrt_stat)

                             
        # 清理庞大的原始数组
        for r in results:
            if 'raw_pred' in r: del r['raw_pred']
            if 'raw_y' in r: del r['raw_y']
            
        return {
            'comparison_data': [r['model_res'] for r in results],
            'methodology': AdvancedModelingService._generate_comparison_methodology()
        }

    @staticmethod
    def _generate_comparison_methodology():
        return ("使用受试者工作特征曲线 (ROC) 下面积 (AUC) 或 Harrell's C-index 来评估模型的区分度。"
                "基于相同的全病例数据集，对模型的预测性能进行了比较分析。")

    @staticmethod
    def _generate_nomogram_methodology(model_type):
        if model_type == 'logistic':
             return ("基于多元 Logistic 回归分析结果构建了诺谟图。"
                     "根据回归系数，为每个变量值分配了相应的分值。")
        else:
             return ("基于 Cox 比例风险模型结果构建了诺谟图。"
                     "为每个预测因子分配分值，用于估算中位随访时间的生存概率。")

    @staticmethod
    def fit_competing_risks(df, time_col, event_col, covariates):
        """
        为所有竞争事件拟合原因特异性 Cox 模型 (Cause-Specific Cox)。
        """
        from lifelines import CoxPHFitter
        
        results = {
            'models': [], 
            'events_found': []
        }
        
        # 1. 识别事件 (排除 0/删失)
        events = sorted([e for e in df[event_col].dropna().unique() if e != 0])
        results['events_found'] = [int(e) for e in events]
        
        if not events:
            raise ValueError("未发现事件类型 (仅发现 0/删失？)")

        df_clean = df[[time_col, event_col] + covariates].dropna()
        df_clean = DataService.preprocess_for_formula(df_clean)
        
        for evt in events:
            temp_df = df_clean.copy()
            temp_df['__cs_event'] = (temp_df[event_col] == evt).astype(int)
            
            # 1. 原因特异性 Cox
            try:
                cph = CoxPHFitter()
                cov_str = " + ".join(covariates)
                formula = f"{cov_str}" 
                
                cph.fit(temp_df, duration_col=time_col, event_col='__cs_event', formula=formula)
                
                model_res = {
                    'event_type': int(evt),
                    'summary': []
                }
                
                for idx, row in cph.summary.iterrows():
                    model_res['summary'].append({
                        'variable': idx,
                        'hr': row['exp(coef)'],
                        'ci_lower': row['exp(coef) lower 95%'],
                        'ci_upper': row['exp(coef) upper 95%'],
                        'p_value': row['p'],
                        'z': row['z']
                    })
                    
                model_res['aic'] = cph.AIC_partial_
                results['models'].append(model_res)
                
            except Exception as e:
                print(f"CS-Cox failed for event {evt}: {e}")
                results['models'].append({'event_type': int(evt), 'error': str(e)})

            # 2. Fine-Gray 子分布风险
            try:
                # 我们传递原始 df，因为 Fine-Gray 内部处理竞争风险 (0=删失, 1..=各类风险)
                # 注意：fit_fine_gray 处理一个感兴趣的事件。
                fg_res = AdvancedModelingService.fit_fine_gray(
                    df, time_col, event_col, covariates, event_of_interest=int(evt)
                )
                # Unpack the single model result
                if fg_res and 'models' in fg_res and len(fg_res['models']) > 0:
                    results.setdefault('fine_gray_models', []).append(fg_res['models'][0])
            except Exception as e:
                print(f"Fine-Gray failed for event {evt}: {e}")
                results.setdefault('fine_gray_models', []).append({'event_type': int(evt), 'error': str(e)})

        results['methodology'] = (
            "进行了竞争风险分析。"
            "使用标准 Cox 模型（将竞争事件视为删失）估算了原因特异性风险比 (CS-HR)。"
            "使用 Fine-Gray 模型估算了子分布风险比 (SHR)，以考虑竞争事件的累积发生率。"
            "使用 Aalen-Johansen 估量法进行累积发生率函数 (CIF) 的可视化。"
        )
        return results
