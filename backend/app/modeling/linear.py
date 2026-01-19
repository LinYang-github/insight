"""
app.modeling.linear.py

线性与逻辑回归模型策略。
包含 OLS (普通最小二乘法) 和 Logit (逻辑回归) 的实现。
结果输出包含 OR 值、VIF 诊断等学术核心指标。
"""
import statsmodels.api as sm
import numpy as np
import pandas as pd
from .base import BaseModelStrategy
from app.utils.formatter import ResultFormatter

class LinearRegressionStrategy(BaseModelStrategy):
    """
    线性回归策略 (OLS)。
    用于分析连续型结局变量与特征变量之间的线性关系。
    """
    def fit(self, df, target, features, params):
        X = df[features]
        X = sm.add_constant(X)
        y = df[target]
        
        model = sm.OLS(y, X)
        
        # 诊断是否存在奇异矩阵 (Singular Matrix)
        rank = np.linalg.matrix_rank(X)
        cols = X.shape[1]
        if rank < cols:
             # 抛出 LinAlgError，以便 ModelingService 进行捕获并给出诊断建议
             raise np.linalg.LinAlgError("检测到奇异矩阵 (Singular Matrix)")
             
        res = model.fit()
        
        return self._format_results(res, df, features)
        


    def _format_results(self, res, df=None, features=None):
        # 计算方差膨胀因子 (VIF)
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
            row = {
                'variable': "截距 (Constant)" if name == 'const' else name,
                'coef': float(params[name]),
                'se': float(bse[name]),
                'p_value': float(pvalues[name]),
                'ci_lower': float(conf.loc[name][0]),
                'ci_upper': float(conf.loc[name][1]),
                'vif': vn # VIF stays string or we should ensure it handles '-'
            }
            # VIF 处理：如果是横杠则保持字符串，否则为浮点数？前端可以很好地处理字符串 '-'。
            # 这里的逻辑：vif_map.get(name, '-')
            row['vif'] = vif_map.get(name, '-') if name != 'const' else '-'
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
    """
    逻辑回归策略 (Logistic Regression)。
    用于分析二分类结局变量（如：发病/不发病）。
    输出包含优势比 (OR, Odds Ratio) 及其 95% 置信区间。
    """
    def fit(self, df, target, features, params):
        X = df[features]
        X = sm.add_constant(X)
        y = df[target]
        
        model = sm.Logit(y, X)
        try:
            res = model.fit(disp=0)
            
            # 检查收敛及是否存在完全分离 (Perfect Separation) 的迹象
            # if np.abs(res.params).max() > 20 or np.any(np.isnan(res.bse)):
            #       raise ValueError("模型未能收敛（检测到完全分离）。")
                  
        except Exception as e:
            if 'singular matrix' in str(e).lower():
                 raise np.linalg.LinAlgError("检测到奇异矩阵 (Singular Matrix)")
            if 'Perfect separation' in str(e):
                 raise ValueError("模型未能收敛。可能原因：存在数据完全分离 (Perfect separation)。")
            raise e
            
        # 模型评价
        y_prob = res.predict(X)
        from app.utils.evaluation import ModelEvaluator
        metrics, plots = ModelEvaluator.evaluate_classification(y, y_prob)
        
        # 3. 列线图 (Nomogram) 数据 (用于打分系统)
        try:
            from app.utils.nomogram_generator import NomogramGenerator
            original_df = params.get('original_df', df)
            original_features = params.get('original_features', features)
            
            nomogram_spec = NomogramGenerator.generate_spec(res, original_df, original_features)
            if nomogram_spec:
                 plots['nomogram'] = nomogram_spec
        except Exception as e:
            print(f"Logistic 诺谟图生成失败: {e}")
            # 回退到简易版
            nomogram_data = {
                'intercept': res.params.get('const', 0),
                'vars': []
            }
            for name, coef in res.params.items():
                if name == 'const': continue
                nomogram_data['vars'].append({
                    'name': name,
                    'coef': coef,
                    'or': np.exp(coef)
                })
            plots['nomogram'] = nomogram_data
        
        # 5 折交叉验证
        from sklearn.model_selection import KFold
        from sklearn.metrics import roc_auc_score
        
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_aucs = []
        
        try:
            # 如果使用 sklearn，需要重新准备不含常数项的 X 以便分割，但 sm (statsmodels) 可以处理。
            # 使用 dataframe 索引是最稳妥的。
            X_reset = X.reset_index(drop=True)
            y_reset = y.reset_index(drop=True)
            
            for train_index, test_index in kf.split(X_reset):
                X_train, X_test = X_reset.iloc[train_index], X_reset.iloc[test_index]
                y_train, y_test = y_reset.iloc[train_index], y_reset.iloc[test_index]
                
                # Fit on train
                try:
                    cv_model = sm.Logit(y_train, X_train)
                    cv_res = cv_model.fit(disp=0)
                    # 在测试集上进行预测
                    y_cv_prob = cv_res.predict(X_test)
                    
                    if len(np.unique(y_test)) == 2:
                        cv_aucs.append(roc_auc_score(y_test, y_cv_prob))
                except Exception:
                    continue # 跳过失败的折叠 (例如由于完全分离)
                    
            if cv_aucs:
                metrics['cv_auc_mean'] = ResultFormatter.format_float(np.mean(cv_aucs), 3)
                metrics['cv_auc_std'] = ResultFormatter.format_float(np.std(cv_aucs), 3)
                
        except Exception as e:
            # 交叉验证失败不应阻碍主结果的生成
            print(f"交叉验证 (CV) 失败: {e}")
            pass
        # 交叉验证逻辑 ... (保留现有逻辑)
            
        # 模型诊断: VIF
        from app.utils.diagnostics import ModelDiagnostics
        vif_data = ModelDiagnostics.calculate_vif(df, features)
        
        return self._format_results(res, metrics, plots, vif_data)

    def _format_results(self, res, metrics=None, plots=None, vif_data=None):
        summary = []
        params = res.params
        bse = res.bse
        pvalues = res.pvalues
        conf = res.conf_int()
        
        # 创建 VIF 映射表
        vif_map = {item['variable']: item['vif'] for item in (vif_data or [])}

        for name in params.index:
            row = {
                'variable': "截距 (Constant)" if name == 'const' else name,
                'coef': float(params[name]),
                'se': float(bse[name]),
                'p_value': float(pvalues[name]),
                'ci_lower': float(conf.loc[name][0]),
                'ci_upper': float(conf.loc[name][1]),
                'or': float(np.exp(params[name])),
                'or_ci_lower': float(np.exp(conf.loc[name][0])),
                'or_ci_upper': float(np.exp(conf.loc[name][1])),
                'vif': vif_map.get(name, '-') if name != 'const' else '-'
            }
            summary.append(row)
            
        # 如果需要则添加截距，目前循环会遍历所有参数
        # 截距 (const) 可能已在 params.index 中。
        # 上方的循环会处理 params.index 中的任何内容。
        
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
