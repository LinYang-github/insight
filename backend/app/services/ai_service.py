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
JSON 字段如下：
- target: 结局变量名称（如果是 Cox 模型，则设为 null）
- time: 时间变量名称（仅 Cox 模型需要，用于随访时间，否则为 null）
- event: 事件状态变量名称（仅 Cox 模型需要，0=删失/1=事件，否则为 null）
- features: 推荐纳入模型的特征变量列表（协变量，剔除 ID 和无意义变量）
- reason: 简短的推荐理由

注意：
1. 识别潜在的结局变量（如：死亡、复发、ESRD、Survival_Time 等）。
2. 在医学研究中，ID、姓名、日期等变量不应作为特征。
3. 如果模型是 Cox，必须识别出时间（Time）和事件状态（Event/Status）。
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
            raise Exception(f"AI 基线分析请求失败: {str(e)}")

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
