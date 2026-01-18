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
