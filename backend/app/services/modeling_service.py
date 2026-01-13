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

# 注册建模策略
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
        
        # 4. 奇异性 / 多重共线性检查
        # 稳健临床级别要求：检测数值奇异性
        numeric_features = df[features].select_dtypes(include=[np.number])
        if not numeric_features.empty and numeric_features.shape[1] > 1:
            try:
                cond = np.linalg.cond(numeric_features)
                if cond > 1e10:
                    raise ValueError(f"特征矩阵是奇异的 (条件数 > 1e10)。检测到完美的共线性。")
            except np.linalg.LinAlgError:
                 raise ValueError("检测到奇异矩阵 (LinAlgError)。请检查是否存在完美的共线性。")
 
        # 校验结局变量
        if isinstance(target, str):
            if df[target].isnull().any():
                raise ValueError(f"结局变量 '{target}' 包含缺失值。")
        elif isinstance(target, dict): # Cox 时间/事件
            if df[target['time']].isnull().any() or df[target['event']].isnull().any():
                 raise ValueError("结局变量 (时间/事件) 包含缺失值。")

    @staticmethod
    def run_model(df: pd.DataFrame, model_type: str, target: "str | dict", features: list, model_params: dict = None) -> dict:
        """
        执行统计建模或机器学习任务 (Strategy Pattern Dispatcher)。

        负责协调数据预处理、策略选择和模型拟合。
        包含对不同模型类型的特定预处理逻辑（如 Logistic 回归的目标变量编码）。

        Args:
            df (pd.DataFrame): 原始数据集。
            model_type (str): 模型类型标识符 ('linear', 'logistic', 'cox', etc.)。
            target (str|dict): 结局变量。
            features (list): 纳入模型的特征变量列表。
            model_params (dict, optional): 模型超参数或配置（如 ref_levels）。

        Returns:
            dict: 包含 'summary' (系数表) 和 'metrics' (模型评价指标) 的标准结果字典。
            格式需符合 `DataService.sanitize_for_json` 要求以确保 JSON 序列化安全。

        Raises:
            ValueError: 当数据完整性校验失败或模型计算出现数学错误（如奇异矩阵）时抛出。
            RuntimeError: 其他未预期的运行时错误。
        """
        model_params = model_params or {}
        
        # 1. Integrity Check (数据完整性校验)
        ModelingService.check_data_integrity(df, features, target)
        
        # 2. 获取模型策略
        try:
            strategy = ModelRegistry.get_strategy(model_type)
        except ValueError as e:
            raise ValueError(f"未知的模型类型: {model_type}")
            
        # 3. 执行建模
        try:
            # 如果可用，从 model_params 中提取参考层级 (ref_levels)
            ref_levels = model_params.get('ref_levels', None)
            
            # 针对基于矩阵的方法进行稳健的预处理
            # NOTE: 显式进行 One-Hot 编码，确保 Pandas 由于版本差异导致的 dtype 问题不影响后续计算。
            df_processed, new_features = DataService.preprocess_for_matrix(df, features, ref_levels=ref_levels)
            
            # --- Robust Target Encoding (目标变量鲁棒性编码) ---
            # 统计模型（Statsmodels）通常需要纯数值型的 Y 向量。
            # 如果用户传入的是字符串（如 'Yes', 'No'），需要在此处统一转码。
            if model_type == 'logistic':
                col = target
                if df_processed[col].dtype == 'object' or str(df_processed[col].dtype) == 'category':
                    # Auto-encode: sort=True ensures consistent mapping (e.g. No=0, Yes=1)
                    # 确保 'No' -> 0, 'Yes' -> 1 的映射顺序
                    codes, uniques = pd.factorize(df_processed[col], sort=True)
                    df_processed[col] = codes
            elif model_type == 'cox':
                # 为事件列编码
                event_col = target['event']
                if df_processed[event_col].dtype == 'object' or str(df_processed[event_col].dtype) == 'category':
                    codes, uniques = pd.factorize(df_processed[event_col], sort=True)
                    df_processed[event_col] = codes
            # -------------------------------
            
            # 为高级可视化 (如列线图 Nomogram) 注入原始数据
            # 我们复制可视化所需的特定元数据，这些元数据在预处理过程中可能会丢失
            model_params['original_df'] = df
            model_params['original_features'] = features
            
            results = strategy.fit(df_processed, target, new_features, model_params)
            
            # --- 生成结果解读 (解耦) ---
            results['interpretation'] = ModelingService._generate_interpretation(model_type, results)
            
            # --- 生成方法学描述 (解耦) ---
            results['methodology'] = ModelingService._generate_methodology(model_type, model_params)

        except np.linalg.LinAlgError:
            # 奇异矩阵诊断
            diagnosis_msg = ModelingService._diagnose_singularity(df_processed, new_features)
            # 不直接抛出异常，而是返回带有诊断信息的“失败”结果
            results = {
                'status': 'failed',
                'error_type': 'singular_matrix',
                'message': diagnosis_msg,
                'summary': [],
                'metrics': {},
                'plots': {}
            }
            # 记录日志但不崩溃
            print(f"模型运行失败: {diagnosis_msg}")
            
        except Exception as e:
            # 对于其他错误，如果可能，我们仍希望返回一个干净的错误，
            # 但目前我们手动抛出的 ValueError 保持原样以提示用户错误。
            if isinstance(e, ValueError): raise e
            raise RuntimeError(f"模型执行失败: {str(e)}")

        return DataService.sanitize_for_json(results)

    @staticmethod
    def _generate_methodology(model_type, params):
        """
        生成适用于论文发表的“方法学”部分文本。
        """
        params = params or {}
        
        # 1. 模型类型
        type_text = ""
        if model_type == 'logistic': type_text = "使用多因素 Logistic 回归分析"
        elif model_type == 'linear': type_text = "使用多因素线性回归分析"
        elif model_type == 'cox': type_text = "使用多因素 Cox 比例风险回归分析"
        elif model_type == 'random_forest': type_text = "使用随机森林 (Random Forest) 机器学习模型"
        elif model_type == 'xgboost': type_text = "使用 XGBoost (极限梯度提升) 模型"
        else: type_text = "进行统计学分析"
        
        lines = [f"{type_text}以识别与结局变量相关的因素。"]
        
        # 2. 统计指标
        metric_text = ""
        if model_type in ['logistic', 'cox']:
            key = "优势比 (OR)" if model_type == 'logistic' else "风险比 (HR)"
            metric_text = f"分析结果以 {key} 及其 95% 置信区间 (95% CI) 表示。"
        elif model_type == 'linear':
            metric_text = "计算了回归系数 (Coef) 及其 95% 置信区间。"
        
        if metric_text: lines.append(metric_text)
        
        # 3. 显著性标准
        lines.append("以双侧 P 值 < 0.05 为差异具有统计学意义。")
        
        # 4. 软件工具
        lines.append("所有分析均使用 Insight 统计平台 (v1.0) 完成。")
        
        # 5. 参考层级 (对照组)
        ref_levels = params.get('ref_levels')
        if ref_levels:
            refs = [f"{key} 的参考组设为 {val}" for key, val in ref_levels.items()]
            if refs:
                lines.append(f"分类变量的参考组设置如下：{', '.join(refs)}。")
                
        return " ".join(lines)

    @staticmethod
    def _generate_interpretation(model_type: str, results: dict) -> dict:
        """
        为前端生成结构化的结论解读。
        """
        # 1. Machine Learning Models (RF, XGBoost)
        if model_type in ['random_forest', 'xgboost']:
            importance = results.get('importance')
            if not importance: return None
            
            # Top 3 features
            top_features = importance[:3]
            feat_names = ", ".join([f['feature'] for f in top_features])
            
            return {
                "text_template": "模型识别出的最重要的前 3 个特征变量为：{vars}。",
                "params": {
                    "vars": feat_names
                },
                "level": "info"
            }
            
        # 2. Statistical Models
        summary = results.get('summary')
        if not summary:
            return None
            
        # 筛选显著变量
        sig_vars = [row for row in summary if row.get('p_value') is not None and row['p_value'] < 0.05]
        
        if not sig_vars:
            return {
                "text_template": "未发现统计学显著 (P < 0.05) 的变量。目前的证据尚不足以证明存在统计学关联。",
                "params": {},
                "level": "info"
            }
            
        # 挑选解释力度最强的变量
        top_var = None
        if model_type == 'logistic':
            # Max OR
            top_var = max(sig_vars, key=lambda x: x.get('or', 0))
        elif model_type == 'cox':
            # Max HR
            top_var = max(sig_vars, key=lambda x: x.get('hr', 0))
        else: # 线性回归
            # 系数绝对值最大
            top_var = max(sig_vars, key=lambda x: abs(x.get('coef', 0)))
            
        # 构造解读信息
        var_name = top_var['variable']
        p_val_fmt = "< 0.001" if top_var['p_value'] < 0.001 else f"{top_var['p_value']:.3f}"
        
        if model_type == 'cox':
            hr = top_var['hr']
            direction = "增加" if hr > 1 else "降低"
            return {
                "text_template": "变量 {var} 风险{direction}显著 (HR={hr}, P={p})。",
                "params": {
                    "var": var_name,
                    "direction": direction,
                    "hr": hr,
                    "p": p_val_fmt
                },
                "level": "danger" if hr > 1 else "success"
            }
        elif model_type == 'logistic':
            or_val = top_var['or']
            direction = "增加" if or_val > 1 else "降低"
            return {
                "text_template": "变量 {var} 风险{direction}显著 (OR={or_val}, P={p})。",
                "params": {
                    "var": var_name,
                    "direction": direction,
                    "or_val": or_val,
                    "p": p_val_fmt
                },
                "level": "danger" if or_val > 1 else "success"
            }
        else: # Linear
            coef = top_var['coef']
            direction = "正相关" if coef > 0 else "负相关"
            return {
                "text_template": "变量 {var} 与结果呈显著{direction} (Coef={coef}, P={p})。",
                "params": {
                    "var": var_name,
                    "direction": direction,
                    "coef": coef,
                    "p": p_val_fmt
                },
                "level": "info"
            }

    @staticmethod
    def _diagnose_singularity(df, features):
        """
        诊断矩阵为何是奇异的（通常是因为高度相关性）。
        返回用户友好的错误消息。
        """
        # 计算相关矩阵
        try:
            # 仅选择数值型特征
            numeric_df = df[features].select_dtypes(include=[np.number])
            if numeric_df.empty or numeric_df.shape[1] < 2:
                return "检测到奇异矩阵。请检查数据是否包含足够的变异，或者样本量是否过小。"
            
            corr_matrix = numeric_df.corr().abs()
            
            # 寻找具有高度相关性 (>0.95) 的变量对
            # 迭代上三角矩阵
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
            
            # 2. VIF 诊断（针对多变量共线性）
            try:
                from app.utils.diagnostics import ModelDiagnostics
                # VIF 需要常数项，并且需要处理 NaN/Inf
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
