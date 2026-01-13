"""
app.utils.diagnostics.py

工具模块：提供模型诊断相关的统计指标计算。
目前支持方差膨胀因子 (VIF) 计算，用于检测变量间的多重共线性。
"""
import pandas as pd
import numpy as np
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from app.utils.formatter import ResultFormatter

class ModelDiagnostics:
    @staticmethod
    def calculate_vif(df, features):
        """
        计算特征变量的方差膨胀因子 (VIF, Variance Inflation Factor)。
        
        VIF 是衡量多重共线性 (Multicollinearity) 的重要指标。
        如果 VIF > 5 或 10，通常认为变量之间存在严重的线性相关，可能导致回归系数不稳定。

        Args:
            df (pd.DataFrame): 包含特征变量的数据集。
            features (list): 需要计算 VIF 的特征变量列表。

        Returns:
            list: 包含每个变量及其 VIF 值的字典列表。
        """
        if not features or len(features) < 2:
            return []
            
        try:
            X = df[features].copy()
            # 是否需要处理未编码的分类变量？
            # ModelingService 通常接收原始 DataFrame，而策略类 (Strategies) 处理编码。
            # 本项目中的特定策略（线性/逻辑回归）通常假设输入已完成数值化或独热编码。
            # 参考 LinearRegressionStrategy.fit 逻辑，它直接选取 df[features]。
            # 如果 features 是分类字符串，statsmodels 的 `OLS(y, X)` 会失败。
            # 目前的实现 `X = df[features]; X = sm.add_constant(X); model = sm.OLS(y, X)` 
            # 意味着输入特征必须是数值型的。
            # TreeModelStrategy 明确处理了编码。
            # linear.py 中的 LinearRegressionStrategy 暂时假设输入为数值型。
            # 如果不是，VIF 计算将失败。因此在此处我们同样假设输入为数值型，以保持一致。
            
            # 为计算 VIF 删除包含缺失值的行
            X = X.dropna()
            X = add_constant(X)
            
            vif_data = []
            for i, col in enumerate(X.columns):
                if col == 'const': continue
                # 处理 VIF 计算中的奇异矩阵或错误
                try:
                    val = variance_inflation_factor(X.values, i)
                    vif_data.append({
                        'variable': col,
                        'vif': ResultFormatter.format_float(val, 2) if not np.isinf(val) else 'Inf'
                    })
                except Exception:
                    vif_data.append({'variable': col, 'vif': 'Error'})
            
            return vif_data
        except Exception as e:
            print(f"VIF 计算失败: {e}")
            return []
