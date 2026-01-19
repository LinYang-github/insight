import json
import re
from openai import OpenAI

class AIService:
    @staticmethod
    def suggest_variable_roles(model_type, variables, api_key, api_base=None, model="gpt-4o"):
        """
        使用 LLM 为变量推荐角色。
        """
        if not api_key:
            raise ValueError("未配置 AI API Key，请前往‘系统设置’配置。")

        # 确保 api_base 正确结尾
        if api_base and not api_base.endswith('/v1') and not api_base.endswith('/v1/'):
            # 兼容有些用户填写的 base 可能没带 v1 的情况
            if not api_base.endswith('/'):
                api_base += '/'
            if 'api.siliconflow.cn' in api_base and 'v1' not in api_base:
                api_base += 'v1'

        client = OpenAI(api_key=api_key, base_url=api_base)
        
        var_desc = "\n".join([f"- {v['name']} ({v['type']})" for v in variables])
        
        system_prompt = """你是一个医学统计专家。你的任务是根据提供的数据集变量列表和用户选择的模型类型，推荐变量在模型中的角色。
你必须返回一个合法的 JSON 对象，不要包含任何额外的解释文字，也不要使用 Markdown 代码块。

通用 JSON 字段：
- target: 结局变量名称（如 eGFR, Death, Status）
- reasoning: 简短的推荐理由

针对不同模型类型的特定字段：

1. **cox** / **km** / **competing_risk**:
   - time: 时间变量 (Time to event)
   - event: 事件变量 (Status, 0=Censor, 1=Event)
   - features: 协变量列表 (Covariates)

2. **clinical_egfr**:
   - scr: 血肌酐 (Serum Creatinine, e.g. Scr, Creatinine, Cr)
   - age: 年龄 (Age)
   - sex: 性别 (Sex/Gender)
   - race: 种族 (Black/Non-Black, 可为 null)
   - height: 身高 (Height/cm, 仅 bedsite schwartz 需要, 可为 null)

3. **clinical_staging**:
   - egfr: 肾小球滤过率 (eGFR)
   - acr: 尿白蛋白肌酐比 (ACR, mg/g, 可为 null)

4. **clinical_slope**:
   - id_col: 病人ID (Patient ID)
   - time_col: 时间变量 (Time/Month/Year)
   - value_col: 数值变量 (Value/eGFR/Measure)

注意：
1. 你的识别必须基于变量名和类型进行推断。
2. 对于 eGFR 计算，优先识别 "Scr", "Cr", "Creatinine", "肌酐"。
3. 对于性别，优先识别 "Sex", "Gender", "Male", "Female"。
"""

        user_prompt = f"""模型类型: {model_type}
变量列表:
{var_desc}

请按照要求的 JSON 结构给出推荐角色。"""

        try:
            # 很多兼容 OpenAI 的接口并不支持 response_format={"type": "json_object"}
            # 为了最大化兼容性（如 SiliconFlow, DeepSeek 旧版本），我们不强制开启此选项
            # 而是通过 Prompt 约束，并在解析时清理 Markdown 标记
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3 # 降低随机性
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理 Markdown 代码块包裹 (```json ... ```)
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            # 找到第一个 { 和最后一个 } 之间的内容，防御可能的杂质内容
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            result = json.loads(content)
            return result
        except Exception as e:
            raise Exception(f"AI 推荐请求失败: {str(e)}")

    @staticmethod
    def suggest_advanced_roles(analysis_type, variables, api_key, api_base=None, model="gpt-4o"):
        """
        为高级模型（RCS, Subgroup, CIF, Nomogram）推荐变量角色。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        var_desc = "\n".join([f"- {v['name']} ({v['type']})" for v in variables])
        
        type_prompts = {
            "rcs": """角色定义：
- target: 结局变量（如果是生存分析，选择时间列）
- event_col: 事件状态（仅生存分析需要，0/1）
- exposure: 核心暴露变量（必须是连续型变量，用于探索非线性）
- covariates: 其他推荐校正的协变量
""",
            "subgroup": """角色定义：
- target: 结局变量（如果是生存分析，选择时间列）
- event_col: 事件状态（仅生存分析需要，0/1）
- exposure: 主要干预/暴露因素
- subgroups: 推荐进行分层的亚组变量（通常为分类变量，如性别、是否有糖尿病）
- covariates: 其他推荐校正的协变量
""",
            "cif": """角色定义：
- time_col: 随访时间
- event_col: 竞争风险事件（识别包含 0, 1, 2 等多分类的事件列）
- group_col: 推荐的分组对比变量
""",
            "nomogram": """角色定义：
- target: 结局变量
- event_col: 事件状态（仅生存分析需要）
- predictors: 推荐纳入评分系统的核心预测因子
""",
            "comparison": """角色定义：
- target: 结局变量
- event_col: 事件状态（仅生存分析需要）
- models: 推荐对比的模型列表（例如：[{"name": "基础模型", "features": ["年级", "性别"]}, {"name": "全模型", "features": ["年龄", "性别", "基因因子"]}]）
""",
            "table1": """角色定义：
- groupBy: 推荐的分组变量（通常是分类变量，如干预组/对照组）
- variables: 推荐纳入基线特征表的所有核心临床变量
""",
            "km": """角色定义：
- time: 随访时间变量
- event: 事件状态（1=发生，0=删失）
- group: 推荐的分组对比变量
""",
            "psm": """角色定义：
- treatment: 处理变量/干预变量（0/1）
- covariates: 需要进行匹配的所有均衡协变量
""",
            "iptw": """角色定义：
- treatment: 处理变量/干预变量（0/1）
- covariates: 用于计算倾向性评分的协变量
""",
            "longitudinal": """角色定义：
- id_col: 个体唯一标识变量 (Subject ID)
- time_col: 时间/随访序号变量 (Time)
- outcome_col: 纵向观测的结局指标 (Outcome)
- fixed_effects: 推荐纳入混合效应模型的固定效应协变量
"""
        }
        
        specific_inst = type_prompts.get(analysis_type, "")
        
        system_prompt = f"""你是一个高级医学统计专家。你的任务是根据变量列表，为指定的分析模型 "{analysis_type}" 推荐最合适的变量角色。
{specific_inst}

你必须返回一个合法的 JSON 对象。不要包含 Markdown 代码块。
JSON 字段应与上述“角色定义”中的字段名完全一致。
多选字段请返回数组。同时包含一个 "reason" 字段解释推荐逻辑。
"""

        user_prompt = f"分析类型: {analysis_type}\n变量列表:\n{var_desc}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            content = response.choices[0].message.content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            return json.loads(content)
        except Exception as e:
            raise Exception(f"AI 角色推荐失败: {str(e)}")
    @staticmethod
    def interpret_results(model_type, summary, metrics, api_key, api_base=None, model="gpt-4o"):
        """
        使用 LLM 对统计模型结果进行医学解读。
        """
        if not api_key:
            raise ValueError("未配置 AI API Key，请前往‘系统设置’配置。")

        # 确保 api_base 正确结尾
        if api_base and not api_base.endswith('/v1') and not api_base.endswith('/v1/'):
            if not api_base.endswith('/'):
                api_base += '/'
            if 'api.siliconflow.cn' in api_base and 'v1' not in api_base:
                api_base += 'v1'

        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # 格式化系数表
        summary_lines = []
        for v in summary:
            # 基础信息
            line = f"- {v['variable']}: Coef={v.get('coef', 'N/A'):.4f}, P={v.get('p_value', 'N/A'):.4f}"
            # 附加比率信息
            if 'or' in v: line += f", OR={v['or']:.2f} ({v.get('or_ci_lower', 0):.2f}-{v.get('or_ci_upper', 0):.2f})"
            if 'hr' in v: line += f", HR={v['hr']:.2f} ({v.get('hr_ci_lower', 0):.2f}-{v.get('hr_ci_upper', 0):.2f})"
            summary_lines.append(line)
        
        summary_text = "\n".join(summary_lines)
        metrics_text = json.dumps(metrics, indent=2)

        system_prompt = """你是一个专业的医学统计学家和临床专家。
你的任务是根据提供的统计模型结果（回归系数、P值、OR/HR值等）和模型评估指标，生成一份严谨且具有临床价值的医学解读报告。

报告必须包含以下模块：
1. **核心发现 (Core Finding)**：一句话总结该模型最主要的临床价值。
2. **因子深度解读 (Factor Analysis)**：深入分析具有统计学显著性（P < 0.05）的变量。说明它们是危险因素还是保护因素，并解释其临床意义。
3. **模型稳健性评估 (Model Evaluation)**：根据 R2、AUC、C-index 等指标，客观评价该模型的预测效能。
4. **临床决策建议 (Clinical Insights)**：基于分析结果，为临床医生提供针对性的决策参考或下一步研究建议。

要求：
- 使用标准的医学统计学语言（如：独立关联、混杂因素、效应量等）。
- 逻辑清晰，使用 Markdown 格式排版。
- 语气专业且客观，避免过度解读。
- 长度控制在 300-500 字之间。
"""

        user_prompt = f"""模型类型: {model_type}
模型结果汇总:
{summary_text}

模型评价指标:
{metrics_text}

请根据以上数据生成专业的医学解读报告。"""

        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 解读请求失败: {str(e)}")

    @staticmethod
    def suggest_cleaning_strategies(variables, row_count, api_key, api_base=None, model="gpt-4o"):
        """
        使用 LLM 为缺失值处理和数据清洗提供智能建议。
        """
        if not api_key:
            raise ValueError("未配置 AI API Key")

        if api_base and not api_base.endswith('/v1') and not api_base.endswith('/v1/'):
            if not api_base.endswith('/'): api_base += '/'
            if 'api.siliconflow.cn' in api_base and 'v1' not in api_base: api_base += 'v1'

        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # 准备变量描述，包含缺失率
        var_lines = []
        for v in variables:
            missing_rate = (v.get('missing_count', 0) / row_count) * 100 if row_count > 0 else 0
            line = f"- {v['name']} ({v['type']}): 缺失值={v.get('missing_count',0)}, 缺失率={missing_rate:.1f}%, 唯一值={v.get('unique_count',0)}"
            var_lines.append(line)
        
        var_desc = "\n".join(var_lines)
        
        system_prompt = """你是一个高水平的数据科学家和医学统计专家。
你的任务是根据变量的名称、类型以及缺失情况，推荐最优的缺失值处理策略。
可选策略包括：
- ignore: 忽略（不处理）
- drop: 剔除缺失行（适用于缺失率极低或关键结局变量）
- mean: 均值填补（仅数值型，适用于正态分布）
- median: 中位数填补（仅数值型，适用于偏态分布）
- mode: 众数填补（适用于分类型变量）
- mice: 多重插补（适用于随机缺失且变量间有较强关联）

你需要返回一个 JSON 对象，结构如下：
{
  "strategies": {
    "变量名": "策略名",
    ...
  },
  "reasons": [
    "针对某些关键变量的处理理由..."
  ]
}
不要返回任何额外文字。
"""

        user_prompt = f"""样本量: {row_count}
变量列表:
{var_desc}

请给出智能清洗建议。"""

        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
                
            return json.loads(content)
        except Exception as e:
            raise Exception(f"AI 清洗建议请求失败: {str(e)}")

    @staticmethod
    def suggest_table1_analysis(table_data, group_by, api_key, api_base=None, model="gpt-4o"):
        """
        使用 LLM 对基线表 (Table 1) 进行全局均衡性评估和深度分析。
        """
        if not api_key:
            raise ValueError("未配置 AI API Key")

        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # 准备基线数据摘要
        table_summary = []
        for row in table_data:
            p_val = row.get('p_value')
            p_str = f"P={p_val:.4f}" if isinstance(p_val, (int, float)) else f"P={p_val}"
            table_summary.append(f"- {row['variable']}: {p_str} (Test: {row.get('test', 'N/A')})")
        
        summary_text = "\n".join(table_summary)
        
        system_prompt = f"""你是一个专业的医学统计学家和临床科研顾问。
你的任务是根据提供的基线表（Table 1）数据摘要，评估各组（分组变量为：{group_by}）之间的均衡性。

报告必须包含以下模块：
1. **组间均衡性总体评价 (Overall Balance)**：一句话总结各组之间在已知基线特征上是否基本平衡。
2. **显著不均衡变量分析 (Imbalanced Factors)**：识别显着不均衡（P < 0.05）的变量，并说明其对研究结论可能存在的潜在偏倚影响。
3. **统计建模建议 (Statistical Advice)**：给出后续在多因素建模时，哪些变量应该作为混杂因素（Confounders）进行强制校正或分层。
4. **临床结论暗示 (Clinical Implications)**：如果存在由于基线不均导致的临床解释陷阱，请予以指出。

要求：
- 使用标准的医学研究语言。
- 逻辑清晰，使用 Markdown 格式。
- 语气专业且客观。
"""

        user_prompt = f"""分组变量: {group_by}
基线变量摘要:
{summary_text}

请根据以上数据生成基线表深度洞察报告。"""

        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 生存分析请求失败: {str(e)}")

    @staticmethod
    def interpret_rcs(plot_data, model_type, exposure, target, p_non_linear, api_key, api_base=None, model="gpt-4o"):
        """
        解读限制性立方样条 (RCS) 结果，判断非线性趋势。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # 提取关键趋势点
        y_values = [d['y'] for d in plot_data]
        max_y = max(y_values)
        min_y = min(y_values)
        
        system_prompt = f"""你是一个高级医学统计专家。
你的任务是解读 RCS 曲线，该曲线展示了暴露变量 {exposure} 与结局 {target} 之间的关系（模型：{model_type}）。

请分析：
1. **非线性显著性**：基于非线性检验 P 值 ({p_non_linear}) 判断是否存在显著非线性（如 U 型、倒 U 型或 S 型）。
2. **趋势描述**：描述随 {exposure} 增加，{target} 的风险（HR/OR）如何变化。是否存在阈值效应或饱和效应？
3. **临床解读**：给出该趋势对临床预防或治疗的参考意义。

要求：使用专业医学术语，Markdown 格式，300字以内。
"""
        user_prompt = f"非线性检验 P 值: {p_non_linear}\n曲线 Y 轴范围: {min_y:.2f} 到 {max_y:.2f}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI RCS 解读失败: {str(e)}")

    @staticmethod
    def interpret_subgroup(forest_data, exposure, target, api_key, api_base=None, model="gpt-4o"):
        """
        解读亚组分析森林图，重点分析交互作用。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        summary = []
        for group in forest_data:
            summary.append(f"亚组变量 {group['variable']}: P-interaction = {group['p_interaction']}")
            for sub in group['subgroups']:
                if sub.get('est'):
                    summary.append(f"  - {sub['level']}: HR/OR = {sub['est']:.2f}, 95%CI ({sub['lower']:.2f}-{sub['upper']:.2f}), P={sub['p']}")
        
        summary_text = "\n".join(summary)
        
        system_prompt = """你是一个临床研究方法学专家。
你的任务是解读亚组分析结果。

请分析：
1. **一致性评估**：处理效应在各亚组之间是否一致？
2. **交互作用识别**：识别出 P-interaction < 0.05 的变量，并解释其临床含义（效应修饰作用）。
3. **优势人群建议**：哪类人群获益更为显著或风险更高？

要求：Markdown 格式，专业严谨。
"""
        user_prompt = f"暴露因素: {exposure}, 结局: {target}\n亚组结果摘要:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 亚组解读失败: {str(e)}")

    @staticmethod
    def interpret_nomogram(variables, model_type, target, api_key, api_base=None, model="gpt-4o"):
        """
        解读列线图及其背后模型的权重。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        var_importance = []
        for v in variables:
            # 这里的 m.pts 反映了重要性
            max_pts = max([m['pts'] for m in v['points_mapping']])
            var_importance.append(f"- {v['name']}: 最大得分贡献 {max_pts:.1f}")
        
        summary_text = "\n".join(var_importance)
        
        system_prompt = f"""你是一个临床辅助决策系统专家。
你的任务是解读列线图 (Nomogram) 模型（结局变量：{target}）。

请分析：
1. **权重分析**：哪些预测因子对风险预测的贡献最大？
2. **临床易用性评价**：评估该分值系统的集成逻辑。
3. **计算器应用指导**：如何根据得分进行风险分层。

要求：Markdown 格式，重点突出。
"""
        user_prompt = f"预测因子得分权重:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 列线图解读失败: {str(e)}")

    @staticmethod
    def interpret_cif(plot_data, time_col, event_col, api_key, api_base=None, model="gpt-4o"):
        """
        解读竞争风险累积发生率 (CIF) 结果。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        summary = []
        for g in plot_data:
            summary.append(f"组别 {g['group']} - 事件类型 {g['event_type']}: 最终发生率 = {g['cif_data'][-1]['y']:.1%}")
            
        summary_text = "\n".join(summary)
        
        system_prompt = f"""你是一个高级生存分析专家。
你的任务是解读竞争风险累积发生率 (CIF) 曲线（时间变量：{time_col}，事件变量：{event_col}）。

请分析：
1. **主要事件 vs 竞争事件**：各组主要事件 (Event 1) 的发生率如何？
2. **竞争分析**：竞争事件 (Event 2) 的存在是否显著影响了对主要事件风险的判断？
3. **趋势对比**：不同分层组之间的发生率差异。

要求：Markdown 格式，专业医学视角。
"""
        user_prompt = f"CIF 结果摘要:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI CIF 解读失败: {str(e)}")

    @staticmethod
    def suggest_best_model(comparison_results, model_type, api_key, api_base=None, model="gpt-4o"):
        """
        根据多个模型的对比指标（AUC, AIC, NRI, IDI 等），智能推荐最优模型。
        """
        if not api_key: raise ValueError("未配置 AI API Key")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        model_summaries = []
        for r in comparison_results:
            m = r.get('metrics', {})
            # 此处如果是 Cox，可能包含多个时间段，取主要指标或最后一个点
            auc = m.get('auc')
            # 处理 Cox 时间依赖的情况
            if model_type == 'cox' and 'time_dependent' in m:
                # 取第一个有效的时间点作为概要
                t_points = list(m['time_dependent'].keys())
                if t_points:
                    tm = m['time_dependent'][t_points[0]]
                    auc = tm.get('auc')
            
            summary = (
                f"- 模型: {r['name']}\n"
                f"  AUC/C-index: {auc:.3f if isinstance(auc, (int, float)) else 'N/A'}\n"
                f"  AIC: {m.get('aic', 'N/A')}\n"
                f"  特征: {', '.join(r.get('features', []))}"
            )
            model_summaries.append(summary)
            
        summary_text = "\n".join(model_summaries)
        
        system_prompt = f"""你是一个顶级的临床预测模型专家。
你的任务是根据提供的多个模型指标，推荐出最具有临床潜力且统计稳健的“最优模型”。

请从以下维度进行选优分析：
1. **预测效能 (Predictive Performance)**：对比 AUC/C-index 是否有显著提升。
2. **模型简洁性 (Parsimony/AIC)**：是否新加的变量显著降低了 AIC，还是仅仅增加了复杂度？
3. **临床增量价值 (Incremental Value)**：如果提供了 NRI/IDI，请说明新模型是否在风险重分类上更有优势。
4. **最终推荐结论**：给出最推荐的模型并说明理由。

要求：使用 Markdown 格式，语言简洁专业，避免废话。
"""
        user_prompt = f"模型类型: {model_type}\n候选模型对比数据:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 模型选优失败: {str(e)}")

    @staticmethod
    def interpret_survival_analysis(plot_data, p_value, api_key, api_base=None, model="gpt-4o"):
        """
        使用 LLM 对 Kaplan-Meier 生存分析结果进行深度医学解读。
        """
        if not api_key:
            raise ValueError("未配置 AI API Key")

        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # 简化绘图数据用于 Prompt
        curves_summary = []
        for g in plot_data:
            times = g.get('times', [])
            probs = g.get('probs', [])
            if len(probs) > 0:
                median_idx = next((i for i, p in enumerate(probs) if p <= 0.5), None)
                median_time = times[median_idx] if median_idx is not None else "未达到 (Not reached)"
                last_prob = probs[-1]
                curves_summary.append(f"- {g['name']}: 中位生存时间={median_time}, 随访结束生存率={last_prob:.1%}")
        
        summary_text = "\n".join(curves_summary)
        
        system_prompt = """你是一个专业的肿瘤学和统计学专家。
你的任务是解读 Kaplan-Meier 生存曲线和 Log-rank 检验结果。

报告必须包含以下模块：
1. **生存特征总结 (Survival Summary)**：简述各组的生存概况。
2. **组间差异评价 (Inter-group Comparison)**：基于 Log-rank P 值判断差异是否具有统计学意义，并指出曲线在何时开始分离。
3. **临床价值分析 (Clinical Insights)**：解释这种差异对临床治疗方案选择或预后评估的意义。
4. **局限性提醒 (Caveats)**：提醒用户注意可能的删失比例或中位生存时间未达到等情况。

要求：
- 使用 Markdown 格式。
- 语气专业。
- 长度约 300 字。
"""

        user_prompt = f"""Log-rank P 值: {p_value}
各组生存概况:
{summary_text}

请生成深度生存分析报告。"""

        try:
            response = client.chat.completions.create(
                model=model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"AI 生存分析请求失败: {str(e)}")

    @staticmethod
    def interpret_causal_inference(analysis_type, balance_data, n_matched=None, api_key=None, api_base=None, model="gpt-4o"):
        """
        对 PSM 或 IPTW 的均衡性进行医学统计学解读。
        """
        if not api_key:
            return "AI Key 未配置"
            
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        balance_desc = "\n".join([f"- {item['variable']}: 匹配前SMD={item['smd_pre']:.3f}, 匹配后SMD={item['smd_post']:.3f}" for item in balance_data])
        
        system_prompt = f"""你是一个临床流行病学专家制。你的任务是解读 "{analysis_type}" 分析后的协变量均衡性。
1. 评估整体均衡性（通常 SMD < 0.1 被认为平衡）。
2. 指出仍然不均衡的关键变量并分析原因。
3. 给出后续统计分析的建议（如：是否需要在回归模型中进一步校正该变量）。
使用中文，语言通俗专业。不要使用 Markdown 代码块。
"""
        user_prompt = f"分析类型: {analysis_type}\n匹配样本量: {n_matched}\n变量平衡详情:\n{balance_desc}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI 均衡性解读失败: {str(e)}"
    @staticmethod
    def interpret_lmm(results, target, time_col, api_key, api_base=None, model="gpt-4o"):
        """
        解读线性混合模型 (LMM) 的固定效应结果。
        """
        if not api_key: return "AI Key 未配置"
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # summary of fixed effects
        # results is a list of dicts: {term, estimate, stderr, z, p, lower, upper}
        fix_eff = []
        for r in results:
            fix_eff.append(f"- {r['term']}: Coef={r['estimate']:.3f} (95% CI: {r['lower']:.3f}, {r['upper']:.3f}), P={r['p']}")
            
        summary_text = "\n".join(fix_eff)
        
        system_prompt = f"""你是一个高级医学统计专家。
你的任务是解读线性混合模型 (LMM) 的固定效应结果（结局：{target}，时间变量：{time_col}）。

请分析：
1. **时间效应**：随时间推移，{target} 是增加、减少还是持平？
2. **协变量影响**：各协变量（如年龄、性别、治疗组）对基线水平或变化率是否有显著影响？
3. **交互作用**：如果存在 Time*Group 交互项，请重点解释不同组别的变化轨迹差异。

要求：Markdown 格式，专业严谨。
"""
        user_prompt = f"固定效应摘要:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI LMM 解读失败: {str(e)}"

    @staticmethod
    def interpret_clustering(cluster_centers, time_col, outcome_col, api_key, api_base=None, model="gpt-4o"):
        """
        解读纵向轨迹聚类结果。
        """
        if not api_key: return "AI Key 未配置"
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # cluster_centers: dict {cluster_id: {slope: float, intercept: float, n: int}}
        summary = []
        for cid, stats in cluster_centers.items():
            trend = "上升" if stats['slope'] > 0 else "下降"
            summary.append(f"- Cluster {cid} (N={stats['n']}): 截距={stats['intercept']:.2f}, 斜率={stats['slope']:.3f} ({outcome_col} 随 {time_col} {trend})")
            
        summary_text = "\n".join(summary)
        
        system_prompt = f"""你是一个临床数据挖掘专家。
你的任务是解读基于轨迹的聚类分析结果（结局：{outcome_col}）。

请分析：
1. **亚型定义**：基于斜率和截距，为每个 Cluster 命名（如“快速下降型”、“稳定型”、“高基线增长型”）。
2. **临床意义**：不同轨迹亚型可能暗示了什么不同的疾病进展机制或预后？

要求：Markdown 格式，生动直观。
"""
        user_prompt = f"聚类中心摘要:\n{summary_text}"
        
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI 聚类解读失败: {str(e)}"
