"""
LLM-based questionnaire generator.

This module provides functionality to automatically generate questionnaires
using LLM based on research topics and agent profiles.
"""

from typing import Dict, List, Any, Optional
import json
from loguru import logger

from .questionnaire import Questionnaire, Question, QuestionType


class QuestionnaireGenerator:
    """LLM驱动的问卷生成器"""

    def __init__(self, model_manager=None):
        """
        初始化生成器

        Args:
            model_manager: 模型管理器,用于调用LLM
        """
        self.model_manager = model_manager

    def set_model_manager(self, model_manager):
        """设置模型管理器"""
        self.model_manager = model_manager

    async def generate_questionnaire(
        self,
        topic: str,
        description: str,
        num_questions: int = 10,
        question_types: Optional[List[str]] = None,
        agent_context: Optional[Dict[str, Any]] = None
    ) -> Questionnaire:
        """
        基于主题生成问卷

        Args:
            topic: 问卷主题
            description: 问卷描述
            num_questions: 生成问题数量
            question_types: 允许的问题类型列表
            agent_context: Agent上下文信息(用于生成更相关的问题)

        Returns:
            生成的问卷对象
        """
        if not self.model_manager:
            raise RuntimeError("未设置model_manager,无法生成问卷")

        # 构建生成提示词
        prompt = self._build_generation_prompt(
            topic, description, num_questions, question_types, agent_context
        )

        # 调用LLM生成
        messages = [{"role": "user", "content": prompt}]

        response = await self.model_manager.atext_request(
            messages=messages,
            response_format="json_object"
        )

        # 解析响应并创建问卷
        questionnaire_data = self._parse_generated_questionnaire(response, topic, description)

        return Questionnaire.from_dict(questionnaire_data)

    def _build_generation_prompt(
        self,
        topic: str,
        description: str,
        num_questions: int,
        question_types: Optional[List[str]],
        agent_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        构建问卷生成提示词

        Args:
            topic: 主题
            description: 描述
            num_questions: 问题数量
            question_types: 问题类型
            agent_context: Agent上下文

        Returns:
            提示词字符串
        """
        # 默认问题类型
        if not question_types:
            question_types = [t.value for t in QuestionType]

        prompt_parts = [
            "你是一位专业的问卷设计专家。请根据以下信息设计一份结构化问卷。",
            "",
            f"问卷主题: {topic}",
            f"问卷描述: {description}",
            f"问题数量: {num_questions}",
            f"允许的问题类型: {', '.join(question_types)}",
        ]

        # 添加Agent上下文
        if agent_context:
            prompt_parts.extend([
                "",
                "Agent背景信息:",
                json.dumps(agent_context, ensure_ascii=False, indent=2)
            ])

        # 添加输出格式说明
        prompt_parts.extend([
            "",
            "请以JSON格式输出问卷,格式如下:",
            json.dumps({
                "id": "questionnaire_id",
                "title": "问卷标题",
                "description": "问卷描述",
                "questions": [
                    {
                        "id": "1",
                        "text": "问题文本",
                        "question_type": "single_choice",
                        "options": ["选项1", "选项2", "选项3"],
                        "required": True
                    },
                    {
                        "id": "2",
                        "text": "问题文本",
                        "question_type": "scale",
                        "scale_range": [1, 5],
                        "required": True
                    }
                ],
                "target_agent_types": ["agent_type1"]
            }, ensure_ascii=False, indent=2),
            "",
            "注意事项:",
            "1. 问题ID必须唯一",
            "2. 单选题和多选题必须提供options列表",
            "3. 量表题必须提供scale_range (例如[1, 5])",
            "4. 问题类型必须是: " + ", ".join(question_types),
            "5. 问题应当清晰、无歧义、与主题相关",
            "6. 考虑问题的逻辑顺序和渐进性"
        ])

        return "\n".join(prompt_parts)

    def _parse_generated_questionnaire(
        self,
        response: str,
        topic: str,
        description: str
    ) -> Dict[str, Any]:
        """
        解析LLM生成的问卷JSON

        Args:
            response: LLM响应
            topic: 主题(用于fallback)
            description: 描述(用于fallback)

        Returns:
            问卷字典数据
        """
        try:
            data = json.loads(response)

            # 验证必需字段
            required_fields = ["id", "title", "description", "questions"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"生成的问卷缺少必需字段: {field}")

            # 验证问题格式
            if not isinstance(data["questions"], list) or len(data["questions"]) == 0:
                raise ValueError("问卷必须包含至少一个问题")

            for idx, q in enumerate(data["questions"]):
                # 确保问题有ID
                if "id" not in q:
                    q["id"] = f"q{idx + 1}"

                # 验证问题类型
                if "question_type" not in q:
                    raise ValueError(f"问题 {q.get('id', idx)} 缺少question_type")

                # 补充默认值
                q.setdefault("required", True)

            # 补充问卷默认值
            data.setdefault("target_agent_types", None)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"解析生成的问卷JSON失败: {e}\n响应内容: {response}")
            raise ValueError(f"LLM响应不是有效的JSON格式: {e}")
        except Exception as e:
            logger.error(f"处理生成的问卷失败: {e}")
            raise

    async def generate_questions_for_metric(
        self,
        metric_name: str,
        metric_description: str,
        num_questions: int = 3
    ) -> List[Question]:
        """
        为特定指标生成相关问题

        Args:
            metric_name: 指标名称
            metric_description: 指标描述
            num_questions: 生成问题数量

        Returns:
            问题列表
        """
        if not self.model_manager:
            raise RuntimeError("未设置model_manager,无法生成问题")

        prompt = self._build_metric_question_prompt(
            metric_name, metric_description, num_questions
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self.model_manager.atext_request(
            messages=messages,
            response_format="json_object"
        )

        # 解析问题
        questions_data = self._parse_generated_questions(response)

        return [Question.from_dict(q) for q in questions_data]

    def _build_metric_question_prompt(
        self,
        metric_name: str,
        metric_description: str,
        num_questions: int
    ) -> str:
        """构建指标相关问题的生成提示词"""
        prompt_parts = [
            f"请为以下指标设计 {num_questions} 个调查问题:",
            "",
            f"指标名称: {metric_name}",
            f"指标描述: {metric_description}",
            "",
            "请以JSON格式输出问题列表:",
            json.dumps({
                "questions": [
                    {
                        "id": "q1",
                        "text": "问题文本",
                        "question_type": "single_choice",
                        "options": ["选项1", "选项2"],
                        "required": True
                    }
                ]
            }, ensure_ascii=False, indent=2),
            "",
            "问题类型可以是: single_choice, multiple_choice, scale, text, boolean"
        ]

        return "\n".join(prompt_parts)

    def _parse_generated_questions(self, response: str) -> List[Dict[str, Any]]:
        """解析生成的问题列表"""
        try:
            data = json.loads(response)

            if "questions" not in data or not isinstance(data["questions"], list):
                raise ValueError("响应必须包含questions数组")

            questions = data["questions"]

            for idx, q in enumerate(questions):
                if "id" not in q:
                    q["id"] = f"q{idx + 1}"

                q.setdefault("required", True)

            return questions

        except json.JSONDecodeError as e:
            logger.error(f"解析生成的问题JSON失败: {e}")
            raise ValueError(f"LLM响应不是有效的JSON: {e}")


# 便捷工具函数
async def generate_questionnaire_from_llm(
    model_manager,
    topic: str,
    description: str,
    num_questions: int = 10,
    **kwargs
) -> Questionnaire:
    """
    便捷函数:使用LLM生成问卷

    Args:
        model_manager: 模型管理器
        topic: 问卷主题
        description: 问卷描述
        num_questions: 问题数量
        **kwargs: 其他参数传递给generate_questionnaire

    Returns:
        生成的问卷
    """
    generator = QuestionnaireGenerator(model_manager)
    return await generator.generate_questionnaire(
        topic=topic,
        description=description,
        num_questions=num_questions,
        **kwargs
    )
