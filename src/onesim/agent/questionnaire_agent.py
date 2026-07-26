from typing import Dict, List, Any, Optional
import re
import json
from loguru import logger

from onesim.models.core.message import Message
from onesim.models import JsonBlockParser
from .base import AgentBase


class QuestionnaireAgent(AgentBase):
    """基于场景生成调查问卷的Agent"""

    def __init__(
        self,
        model_config_name: str,
        sys_prompt: str = '',
    ):
        """
        初始化问卷生成Agent

        Args:
            model_config_name: 模型配置名称
            sys_prompt: 系统提示,默认为空
        """
        super().__init__(
            sys_prompt=sys_prompt or (
                "你是一个专门负责设计社会调查问卷的AI助手。"
                "你的任务是基于场景描述和Agent类型,生成有意义的调查问卷。"
                "问卷应该能够帮助研究者了解Agent的态度、行为、偏好和决策过程。"
            ),
            model_config_name=model_config_name,
        )
        self.parser = JsonBlockParser()
        self.question_types = ["single_choice", "multiple_choice", "scale", "text", "boolean"]

    def generate_questionnaires(
        self,
        scenario_description: str,
        agent_types: List[str],
        agent_profiles: Optional[Dict[str, Any]] = None,
        num_questionnaires: int = 1
    ) -> List[Dict]:
        """
        分析场景,生成适用的问卷列表

        Args:
            scenario_description: 场景描述
            agent_types: Agent类型列表
            agent_profiles: Agent画像信息 (可选)
            num_questionnaires: 生成问卷的数量

        Returns:
            问卷定义列表
        """
        if not scenario_description:
            logger.error("场景描述不能为空")
            return []

        if not agent_types:
            logger.error("代理类型列表不能为空")
            return []

        prompt = self._create_generation_prompt(
            scenario_description,
            agent_types,
            agent_profiles,
            num_questionnaires
        )

        # 使用模型获取响应
        prompt_message = self.model.format(
            Message("system", self.sys_prompt, role="system"),
            Message("user", prompt + self.parser.format_instruction, role="user")
        )

        response = self.model(prompt_message)

        # 解析响应,提取问卷定义
        try:
            result = self.parser.parse(response)
            questionnaires = result.parsed.get("questionnaires", [])
            logger.info(f"为场景生成了 {len(questionnaires)} 个问卷")

            return questionnaires
        except Exception as e:
            logger.error(f"解析问卷生成响应时出错: {str(e)}")
            # 尝试使用正则表达式提取JSON块
            try:
                json_pattern = r'```json\s*([\s\S]*?)\s*```'
                matches = re.findall(json_pattern, response)
                if matches:
                    questionnaires_data = json.loads(matches[0])
                    questionnaires = questionnaires_data.get("questionnaires", [])
                    logger.info(f"通过备用方法提取到 {len(questionnaires)} 个问卷")
                    return questionnaires
            except Exception as backup_error:
                logger.error(f"备用提取方法也失败: {str(backup_error)}")

            return []

    def _create_generation_prompt(
        self,
        scenario_description: str,
        agent_types: List[str],
        agent_profiles: Optional[Dict[str, Any]] = None,
        num_questionnaires: int = 1
    ) -> str:
        """
        创建用于生成问卷的提示

        Args:
            scenario_description: 场景描述
            agent_types: Agent类型列表
            agent_profiles: Agent画像信息
            num_questionnaires: 生成问卷的数量

        Returns:
            提示字符串
        """
        agent_profiles_str = ""
        if agent_profiles:
            agent_profiles_str = json.dumps(agent_profiles, indent=2, ensure_ascii=False)

        return f"""
Questionnaire Generation Task

Scenario Description:
```
{scenario_description}
```

Agent Types:
```
{", ".join(agent_types)}
```

Agent Profiles Information:
```json
{agent_profiles_str}
```

Task: Generate survey questionnaires that would be valuable for understanding agent behaviors, attitudes, and decision-making in this scenario.

Requirements:
1. Consider questionnaires that could reveal:
   - Agent attitudes and preferences
   - Decision-making processes
   - Behavioral patterns
   - Social relationships and interactions
   - Resource allocation strategies
   - Satisfaction and well-being

2. For each questionnaire, specify:
   - Unique ID
   - Descriptive title
   - Clear description of purpose
   - List of questions with appropriate types
   - Target agent types (which agents should answer)

3. Support these question types:
   - "single_choice": Single selection from options
   - "multiple_choice": Multiple selections from options
   - "scale": Numerical rating (e.g., 1-5, 1-10)
   - "text": Free-form text response
   - "boolean": Yes/No question

4. Question design guidelines:
   - Questions should be clear and unambiguous
   - Align questions with agent's profile and memory context
   - Consider agent's role and capabilities
   - Avoid questions that require information agents wouldn't have
   - Include reasoning prompts where appropriate

5. Each question should include:
   - Unique ID within the questionnaire
   - Question text
   - Question type
   - Options (for choice questions)
   - Scale range (for scale questions)
   - Whether the question is required
   - Optional metadata (dimension, category, etc.)

Output Format:
```json
{{
  "questionnaires": [
    {{
      "id": "questionnaire_id",
      "title": "Questionnaire Title",
      "description": "Purpose and focus of this questionnaire",
      "questions": [
        {{
          "id": "q1",
          "text": "Question text here?",
          "question_type": "single_choice|multiple_choice|scale|text|boolean",
          "options": ["Option 1", "Option 2", "Option 3"],  // For choice questions
          "scale_range": [1, 5],  // For scale questions
          "required": true,
          "metadata": {{
            "dimension": "attitude|behavior|satisfaction|preference",
            "category": "specific_category"
          }}
        }}
      ],
      "target_agent_types": ["agent_type1", "agent_type2"],
      "metadata": {{
        "version": "1.0",
        "frequency": "once|daily|weekly",
        "timing": "beginning|middle|end"
      }}
    }}
  ]
}}
```

Generate {num_questionnaires} questionnaire(s) that would be most valuable for understanding agent behaviors and outcomes in this scenario.
"""

    def format_questionnaires_for_export(self, questionnaires: List[Dict]) -> List[Dict]:
        """
        将生成的问卷格式化为导出格式

        Args:
            questionnaires: 原始问卷定义列表

        Returns:
            格式化后的问卷列表
        """
        formatted_questionnaires = []

        for questionnaire in questionnaires:
            # 确保ID格式正确
            questionnaire_id = questionnaire.get("id", f"questionnaire_{len(formatted_questionnaires)+1}")
            questionnaire_id = re.sub(r'[^\w\-_]', '_', questionnaire_id)

            formatted_questionnaire = {
                "id": questionnaire_id,
                "title": questionnaire.get("title", "未命名问卷"),
                "description": questionnaire.get("description", "无描述"),
                "questions": questionnaire.get("questions", []),
                "target_agent_types": questionnaire.get("target_agent_types", []),
                "metadata": questionnaire.get("metadata", {})
            }

            formatted_questionnaires.append(formatted_questionnaire)

        return formatted_questionnaires
