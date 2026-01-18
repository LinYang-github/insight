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
