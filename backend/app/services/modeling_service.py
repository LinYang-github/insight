"""
app.services.modeling_service.py

负责核心统计模型的调度与执行。
包含数据完整性校验、策略模式的模型分发以及结果的标准化格式化。
"""

from app.services.data_service import DataService
from app.modeling.registry import ModelRegistry
from app.modeling.linear import LinearRegressionStrategy, LogisticRegressionStrategy
from app.modeling.survival import CoxStrategy
from app.modeling.tree import RandomForestStrategy, XGBoostStrategy
import numpy as np
import pandas as pd

# Register Strategies
ModelRegistry.register('linear', LinearRegressionStrategy)
ModelRegistry.register('logistic', LogisticRegressionStrategy)
ModelRegistry.register('cox', CoxStrategy)
ModelRegistry.register('random_forest', RandomForestStrategy)
ModelRegistry.register('xgboost', XGBoostStrategy)

class ModelingService:
    @staticmethod
    def check_data_integrity(df, features, target):
        """
        执行建模前的数据完整性校验。

        Args:
            df (pd.DataFrame): 输入的数据集。
            features (list): 协变量/特征变量列表。
            target (str|dict): 结局变量。线性/逻辑回归为字符串，Cox回归为字典 {'time': str, 'event': str}。

        Raises:
            ValueError: 当数据包含缺失值、无穷大或变量为常数（零方差）时抛出，
                        这些情况会导致统计模型（如矩阵求逆）失败。
        """
        # 1. 缺失值校验：
        # 统计模型（特别是 OLS/Logit）默认不支持缺失值。
        # 虽然底层库可能有处理，但在 Service 层拦截能提供更友好的界面提示。
        if df[features].isnull().any().any():
            missing_cols = df[features].columns[df[features].isnull().any()].tolist()
            raise ValueError(f"特征变量中包含缺失值 (NaN): {', '.join(missing_cols)}。请先在‘数据清洗’中进行填补。")
            
        # 2. 无穷大校验：
        # 处理异常数据，防止数值计算溢出。
        if np.isinf(df[features].select_dtypes(include=np.number)).values.any():
             raise ValueError("特征变量中包含无穷大数值。请检查原始数据。")
             
        # 3. 零方差/常数项校验：
        # 如果一个变量的所有值都相同，它在回归中无法解释结局变量的变异，
        # 且会导致回归矩阵出现奇异（Singular Matrix）。
        for col in features:
            if df[col].nunique() <= 1:
                raise ValueError(f"变量 '{col}' 是常数（方差为0），无法用于建模。")

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
        Run statistical or ML model using Strategy Pattern.
        """
        model_params = model_params or {}
        
        # 1. Integrity Check
        ModelingService.check_data_integrity(df, features, target)
        
        # 2. Get Strategy
        try:
            strategy = ModelRegistry.get_strategy(model_type)
        except ValueError as e:
            raise ValueError(f"Unknown model type: {model_type}")
            
        # 3. Execute
        try:
            # Extract ref_levels from model_params if available
            ref_levels = model_params.get('ref_levels', None)
            
            # Add Robust Preprocessing for Matrix-based methods (all strategies here)
            # This ensures string/object columns are One-Hot Encoded
            # And respects Reference Level if provided
            df_processed, new_features = DataService.preprocess_for_matrix(df, features, ref_levels=ref_levels)
            
            # --- Robust Target Encoding ---
            # Statsmodels requires numeric target.
            if model_type == 'logistic':
                col = target
                if df_processed[col].dtype == 'object' or str(df_processed[col].dtype) == 'category':
                    # Auto-encode: sort=True ensures consistent mapping (e.g. No=0, Yes=1)
                    codes, uniques = pd.factorize(df_processed[col], sort=True)
                    df_processed[col] = codes
            elif model_type == 'cox':
                # Encode Event column
                event_col = target['event']
                if df_processed[event_col].dtype == 'object' or str(df_processed[event_col].dtype) == 'category':
                    codes, uniques = pd.factorize(df_processed[event_col], sort=True)
                    df_processed[event_col] = codes
            # -------------------------------
            
            results = strategy.fit(df_processed, target, new_features, model_params)
        except np.linalg.LinAlgError:
            # Diagnose the issue
            diagnosis = ModelingService._diagnose_singularity(df_processed, new_features)
            raise ValueError(diagnosis)
        except Exception as e:
            if isinstance(e, ValueError): raise e
            raise RuntimeError(f"Model execution failed: {str(e)}")

        return DataService.sanitize_for_json(results)

    @staticmethod
    def _diagnose_singularity(df, features):
        """
        Diagnose why the matrix is singular (usually high correlation).
        Returns a user-friendly error message.
        """
        # Calculate correlation matrix
        try:
            # Select numeric features only
            numeric_df = df[features].select_dtypes(include=[np.number])
            if numeric_df.empty or numeric_df.shape[1] < 2:
                return "Singular matrix detected. Please check if your data contains enough variance or if sample size is too small."
            
            corr_matrix = numeric_df.corr().abs()
            
            # Find pairs with high correlation (>0.95)
            # Iterate upper triangle
            high_corr_pairs = []
            cols = corr_matrix.columns
            for i in range(len(cols)):
                for j in range(i+1, len(cols)):
                    if corr_matrix.iloc[i, j] > 0.95:
                        high_corr_pairs.append(f"{cols[i]} & {cols[j]} (r={corr_matrix.iloc[i, j]:.2f})")
            
            if high_corr_pairs:
                return (
                    f"模型计算失败：检测到严重的多重共线性 (Singular Matrix)。\n"
                    f"以下变量高度相关，导致信息冗余：\n"
                    f"{', '.join(high_corr_pairs[:3])}" 
                    f"{' 等' if len(high_corr_pairs) > 3 else ''}。\n"
                    f"建议：移除其中一个相关变量后重试。"
                )
            
            # 2. VIF Diagnosis (For Multi-variable Collinearity)
            try:
                from app.utils.diagnostics import ModelDiagnostics
                # VIF requires constant, and needs to handle NaNs/Infs
                vif_data = ModelDiagnostics.calculate_vif(numeric_df, numeric_df.columns.tolist())
                high_vif = [item['variable'] for item in vif_data if item['vif'] == 'inf' or (isinstance(item['vif'], (int, float)) and item['vif'] > 10)]
                
                if high_vif:
                     return (
                        f"模型计算失败：检测到隐蔽的多重共线性 (Singular Matrix)。\n"
                        f"虽然变量间两两相关性不高，但存在多变量线性组合。以下变量 VIF 过高：\n"
                        f"{', '.join(high_vif[:3])}...\n"
                        f"建议：尝试移除 VIF 最高的变量。"
                     )
            except Exception:
                pass
            
            return "模型计算失败：检测到奇异矩阵 (Singular Matrix)。可能是因为变量间存在完全线性关系或样本量不足。"
        except Exception:
            return "模型计算失败：检测到奇异矩阵 (Singular Matrix)。请检查数据是否存在重复变量。"
