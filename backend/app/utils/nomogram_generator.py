import numpy as np
import pandas as pd

class NomogramGenerator:
    """
    根据拟合的 Cox 模型生成可视化所需的列线图 (Nomogram) 配置规格。
    遵循 RMS (回归建模策略) 原则。
    """
    
    @staticmethod
    def generate_counts(df, features, target_event_col):
        """
        为变量范围生成原始计数/分布特征。
        """
        # 变量到最小值、最大值或类别的映射字典
        pass 

    @staticmethod
    def generate_spec(cph_model, df, features, time_points):
        """
        Args:
            cph_model: 拟合好的 lifelines CoxPHFitter 模型
            df: 原始 DataFrame (One-Hot 编码前，用于获取变量范围)
            features: 所使用的特征变量列表 (One-Hot 编码前)
            time_points: 预测的时间点列表 [12, 36, 60]
            
        Returns:
            dict: 列线图规格配置 (Nomogram Specification)
        """
        # 1. 解析系数并按原始变量分组
        # Lifelines 的参数索引为：连续型 (Age), 哑变量 (Sex_Male, Race_Black...)
        params = cph_model.params_
        summary = cph_model.summary 
        
        # 我们需要将模型系数映射回特征规格
        # 结构示例：
        # {
        #   'Age': { type: 'continuous', min: 20, max: 80, coef: 0.05 },
        #   'Sex': { type: 'categorical', levels: [ {label: 'F', coef:0}, {label: 'M', coef: 0.5} ] }
        # }
        
        var_specs = {}
        
        # 助手函数：判定参数是否来自某分类特征
        # 我们初步假设 'features' 列表中的特征即为键
        # 如果是连续变量，则按原名出现
        # 如果是分类变量，通常以 {特征名}_{水平名} 形式出现 (如果手动执行了 get_dummies)
        # 需要进行鲁棒性映射。
        
        # 更好的方法：迭代用户指定的特征
        for feat in features:
            if feat in df.columns:
                is_cat = df[feat].dtype == 'object' or str(df[feat].dtype) == 'category' or df[feat].nunique() < 10 # 启发式判定
                
                # 情况 1：该特征直接出现在参数中 (连续型)
                if feat in params.index:
                    # 连续型
                    min_val = df[feat].min()
                    max_val = df[feat].max()
                    coef = params[feat]
                    
                    var_specs[feat] = {
                        'type': 'continuous',
                        'min': float(min_val),
                        'max': float(max_val),
                        'coef': float(coef),
                        'effect_range': abs(coef * (max_val - min_val))
                    }
                    
                else:
                    # 情况 2：是否存在以该特征名为前缀的哑变量？
                    # 这依赖于 DataService (pd.get_dummies) 的命名习惯
                    # 规范为："{特征名}_{水平名}"
                    dummies = [p for p in params.index if p.startswith(f"{feat}_")]
                    
                    if dummies:
                        levels = []
                        # 参考水平 (Reference Level) 的处理比较棘手，因为它是隐式的 (coef=0)
                        # 我们需要从原始数据框中寻找所有水平以标识参考组
                        all_levels = sorted(df[feat].unique().tolist())
                        
                        # 寻找哪个水平不在哑变量列表中 -> 该水平即为参考组
                        # 假设：水平名称是后缀
                        dummy_suffixes = [d.replace(f"{feat}_", "") for d in dummies]
                        
                        # 计算效应范围 (最大系数 - 最小系数)
                        # 参考组的系数为 0
                        coefs = [0.0] # 从参考组开始
                        for d in dummies:
                            coefs.append(params[d])
                        
                        min_coef = min(coefs)
                        max_coef = max(coefs)
                        
                        # 构建水平规格 (Level Specs)
                        # 我们迭代数据中的所有水平，以确保顺序和包含关系正确
                        level_specs = []
                        for level in all_levels:
                            level_str = str(level)
                            # 寻找匹配的哑变量
                            # 注意：pandas get_dummies 可能会修改字符串 (例如将空格转换为 _)
                            # 简单的匹配检查
                            dummy_match = None
                            for d in dummies:
                                if d == f"{feat}_{level_str}": 
                                    dummy_match = d
                                    break
                            
                            coef = 0.0
                            if dummy_match:
                                coef = params[dummy_match]
                            
                            level_specs.append({
                                'label': level_str,
                                'coef': float(coef)
                            })
                            
                        var_specs[feat] = {
                            'type': 'categorical',
                            'levels': level_specs,
                            'effect_range': max_coef - min_coef
                        }

        # 2. 归一化到 100 分
        # 寻找效应范围 (effect_range) 最大的变量
        if not var_specs:
            return None
            
        max_effect_var = max(var_specs.items(), key=lambda x: x[1]['effect_range'])
        max_effect_val = max_effect_var[1]['effect_range']
        
        if max_effect_val == 0:
            points_per_unit = 0 # 奇异模型？
        else:
            points_per_unit = 100.0 / max_effect_val
            
        # 3. 构建坐标轴数据 (Value -> Points 的映射)
        axes = []
        
        # 同时追踪总分范围
        min_total_points = 0
        max_total_points = 0
        
        for name, spec in var_specs.items():
            if spec['type'] == 'continuous':
                # 线性比例
                # 分值 = |系数 * (值 - 基准)| * 缩放比例？
                # 通常我们将“0 分”对齐到产生最小效应的值，或者直接对齐到最小值。
                # 让我们将最小值对齐到 0 分贡献？
                # 不，贡献值 = 系数 * 值。
                # 我们将 (系数 * 值) 映射为分值。
                # 相对于什么？通常我们进行偏移以使最小贡献值为 0。
                
                contributions = [spec['min'] * spec['coef'], spec['max'] * spec['coef']]
                min_contrib = min(contributions)
                max_contrib = max(contributions)
                
                # 将贡献值范围转换为分值
                # 分值 = (贡献值 - 全局基准?) * 缩放比例
                # 标准列线图：对于每个变量，我们在局部定义一个“0 分”基准。
                # 局部得分 = (贡献值 - 局部最小贡献值) * points_per_unit
                
                spec['points_at_min'] = 0
                spec['points_at_max'] = (max_contrib - min_contrib) * points_per_unit
                
                # 累加到最大总分范围
                max_total_points += spec['points_at_max']
                
                axes.append({
                    'name': name,
                    'type': 'continuous',
                    'min': spec['min'],
                    'max': spec['max'],
                    'ticks': [spec['min'], spec['max']], # 起点/终点
                    # 计算最小值和最大值的分数
                    # 如果系数 > 0: 最小值 -> 0 分, 最大值 -> N 分
                    # 如果系数 < 0: 最大值 -> 0 分, 最小值 -> N 分
                    'points': {
                        str(spec['min']): 0 if spec['coef'] > 0 else spec['points_at_max'],
                        str(spec['max']): spec['points_at_max'] if spec['coef'] > 0 else 0
                    }
                })
                
            elif spec['type'] == 'categorical':
                # 局部得分 = (系数 - 最小系数) * points_per_unit
                coefs = [l['coef'] for l in spec['levels']]
                min_c = min(coefs)
                max_c = max(coefs)
                
                local_max_points = (max_c - min_c) * points_per_unit
                max_total_points += local_max_points
                
                levels_visual = []
                for l in spec['levels']:
                    p = (l['coef'] - min_c) * points_per_unit
                    levels_visual.append({
                        'label': l['label'],
                        'points': p,
                        'coef': l['coef']
                    })
                    
                axes.append({
                    'name': name,
                    'type': 'categorical',
                    'levels': levels_visual
                })

        # 4. 总分到生存概率的映射
        # 公式: S(t|x) = S0(t) ^ exp(LP)
        # LP = Sum(Coef * X)  [线性预测值]
        # TotalPoints = Sum(LocalPoints)
        # 我们需要建立 LP 和 TotalPoints 之间的关系。
        # LocalPoints_i = (Coef_i * X_i - MinContrib_i) * Scale
        # Sum(LocalPoints) = Scale * (Sum(Coef*X) - Sum(MinContrib))
        # Sum(LocalPoints) = Scale * (LP - Constant_Offset)
        # LP = (TotalPoints / Scale) + Constant_Offset
        # Constant_Offset = Sum(所有变量的最小贡献值 MinContrib_i) 
        
        sum_min_contrib = 0
        for name, spec in var_specs.items():
            if spec['type'] == 'continuous':
                contribs = [spec['min'] * spec['coef'], spec['max'] * spec['coef']]
                sum_min_contrib += min(contribs)
            elif spec['type'] == 'categorical':
                 coefs = [l['coef'] for l in spec['levels']]
                 sum_min_contrib += min(coefs)
                 
        # 预计算基准生存概率 S0(t)
        baseline_survival = cph_model.baseline_survival_
        # baseline_survival 的索引为时间，值为 S0(t)
        
        survival_scales = []
        for t in time_points:
            # 寻找 S0(t)
            # 寻找最接近的索引
            idx = baseline_survival.index.get_indexer([t], method='nearest')[0]
            s0_t = baseline_survival.iloc[idx, 0]
            
            # 为可视化轴生成映射表
            # 总分：0 到 max_total_points (例如 200)
            # 步长设为 10
            ticks = []
            steps = 20
            step_size = max_total_points / steps
            
            for i in range(steps + 1):
                pt = i * step_size
                # 转换 Pt -> LP
                # LP = (Pt / Scale) + Offset
                lp = (pt / points_per_unit) + sum_min_contrib
                # S(t) = S0(t) ^ exp(LP)
                surv = s0_t ** np.exp(lp)
                
                ticks.append({
                    'points': pt,
                    'survival': surv
                })
                
            survival_scales.append({
                'time': t,
                'ticks': ticks
            })
            
        return {
            'axes': axes,
            'total_points': {
                'min': 0,
                'max': max_total_points
            },
            'survival_scales': survival_scales,
            'base_survivals': { t: baseline_survival.iloc[baseline_survival.index.get_indexer([t], method='nearest')[0], 0] for t in time_points },
            'formula_params': {
                'points_per_unit': points_per_unit,
                'constant_offset': sum_min_contrib
            }
        }
