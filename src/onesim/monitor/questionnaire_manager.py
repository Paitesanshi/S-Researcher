"""
Questionnaire manager for administering surveys to agents.

This module provides the QuestionnaireManager class which handles:
- Registering and managing questionnaires
- Administering questionnaires to agents
- Collecting and analyzing responses
- LLM-based questionnaire generation
"""

from typing import Dict, List, Any, Optional, Callable
import asyncio
from loguru import logger
import json

from .questionnaire import (
    Questionnaire,
    Question,
    QuestionType,
    Answer,
    QuestionnaireResponse,
    QuestionnaireResult
)


class QuestionnaireManager:
    """问卷管理器,负责问卷的创建、分发和收集"""

    def __init__(self):
        # 存储所有注册的问卷
        self.questionnaires: Dict[str, Questionnaire] = {}

        # 存储问卷结果
        self.results: Dict[str, QuestionnaireResult] = {}

        # 环境引用
        self.env = None

        # 异步锁
        self.lock = asyncio.Lock()

    def setup(self, env: Any):
        """
        设置问卷管理器,关联环境对象

        Args:
            env: 环境对象
        """
        self.env = env
        logger.info("QuestionnaireManager已关联环境对象")
        return self

    def register_questionnaire(self, questionnaire: Questionnaire) -> None:
        """
        注册问卷

        Args:
            questionnaire: 问卷定义
        """
        if questionnaire.id in self.questionnaires:
            logger.warning(f"问卷 {questionnaire.id} 已存在,将被覆盖")

        self.questionnaires[questionnaire.id] = questionnaire
        logger.info(f"问卷 '{questionnaire.title}' (ID: {questionnaire.id}) 已注册")

    def unregister_questionnaire(self, questionnaire_id: str) -> None:
        """
        注销问卷

        Args:
            questionnaire_id: 问卷ID
        """
        if questionnaire_id in self.questionnaires:
            del self.questionnaires[questionnaire_id]
            logger.info(f"问卷 {questionnaire_id} 已注销")
        else:
            logger.warning(f"问卷 {questionnaire_id} 不存在")

    def load_questionnaire_from_json(self, filepath: str) -> Questionnaire:
        """
        从JSON文件加载问卷并注册

        Args:
            filepath: JSON文件路径

        Returns:
            加载的问卷对象
        """
        questionnaire = Questionnaire.from_json(filepath)
        self.register_questionnaire(questionnaire)
        logger.info(f"从文件加载并注册问卷: {filepath}")
        return questionnaire

    def export_questionnaire_to_json(self, questionnaire_id: str, filepath: str) -> None:
        """
        导出问卷为JSON文件

        Args:
            questionnaire_id: 问卷ID
            filepath: 导出文件路径
        """
        if questionnaire_id not in self.questionnaires:
            raise ValueError(f"问卷 {questionnaire_id} 不存在")

        questionnaire = self.questionnaires[questionnaire_id]
        questionnaire.to_json(filepath)
        logger.info(f"问卷已导出到: {filepath}")

    async def administer_questionnaire(
        self,
        questionnaire_id: str,
        agent_ids: Optional[List[str]] = None,
        agent_types: Optional[List[str]] = None,
        batch_size: int = 5
    ) -> QuestionnaireResult:
        """
        向指定Agent发放问卷并收集响应

        Args:
            questionnaire_id: 问卷ID
            agent_ids: 指定的Agent ID列表,None表示所有Agent
            agent_types: 指定的Agent类型列表,None表示所有类型
            batch_size: 批量询问的问题数量,默认5个问题一批

        Returns:
            问卷结果
        """
        if not self.env:
            raise RuntimeError("环境对象未设置,请先调用setup()")

        if questionnaire_id not in self.questionnaires:
            raise ValueError(f"问卷 {questionnaire_id} 不存在")

        questionnaire = self.questionnaires[questionnaire_id]

        # 确定目标Agent类型
        target_types = agent_types or questionnaire.target_agent_types

        # 获取目标Agents
        target_agents = await self._get_target_agents(agent_ids, target_types)

        if not target_agents:
            logger.warning(f"没有找到符合条件的Agent来完成问卷 {questionnaire_id}")
            return QuestionnaireResult(questionnaire_id=questionnaire_id, responses=[])

        logger.info(f"开始向 {len(target_agents)} 个Agent发放问卷 '{questionnaire.title}'")

        # 收集响应
        responses = []
        async with self.lock:
            for agent in target_agents:
                try:
                    response = await self._collect_agent_response(agent, questionnaire, batch_size)
                    responses.append(response)
                except Exception as e:
                    logger.error(f"收集Agent {agent.agent_id} 的问卷响应失败: {e}")

        # 创建结果
        result = QuestionnaireResult(
            questionnaire_id=questionnaire_id,
            responses=responses
        )

        # 保存结果
        self.results[questionnaire_id] = result

        logger.info(f"问卷 '{questionnaire.title}' 收集完成,共 {len(responses)} 份响应")

        return result

    async def _get_target_agents(
        self,
        agent_ids: Optional[List[str]],
        agent_types: Optional[List[str]]
    ) -> List[Any]:
        """
        获取目标Agent列表

        Args:
            agent_ids: Agent ID列表
            agent_types: Agent类型列表

        Returns:
            Agent对象列表
        """
        if not hasattr(self.env, 'get_agents'):
            logger.error("环境对象缺少 get_agents 方法")
            return []

        all_agents = await self.env.get_agents()

        # 按ID筛选
        if agent_ids:
            all_agents = [a for a in all_agents if a.agent_id in agent_ids]

        # 按类型筛选
        if agent_types:
            all_agents = [a for a in all_agents if a.agent_type in agent_types]

        return all_agents

    async def _collect_agent_response(
        self,
        agent: Any,
        questionnaire: Questionnaire,
        batch_size: int = 5
    ) -> QuestionnaireResponse:
        """
        收集单个Agent的问卷响应

        Args:
            agent: Agent对象
            questionnaire: 问卷定义
            batch_size: 批量询问的问题数量

        Returns:
            问卷响应
        """
        answers = []
        questions = questionnaire.questions

        # 按batch_size分批处理问题
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]

            # 批量询问当前批次的问题
            batch_answers = await self._ask_agent_questions_batch(agent, batch, questionnaire)
            answers.extend(batch_answers)

        return QuestionnaireResponse(
            questionnaire_id=questionnaire.id,
            agent_id=agent.agent_id,
            agent_type=agent.agent_type,
            answers=answers
        )

    async def _ask_agent_questions_batch(
        self,
        agent: Any,
        questions: List[Question],
        questionnaire: Questionnaire
    ) -> List[Answer]:
        """
        批量向Agent询问多个问题 (基于Agent的profile和memory上下文)

        Args:
            agent: Agent对象
            questions: 问题列表
            questionnaire: 问卷定义

        Returns:
            答案列表
        """
        # 构建批量问题上下文
        observation = self._build_questions_batch_context(questions, questionnaire)

        # 构建批量回答指令
        instruction = self._build_questions_batch_instruction(questions)

        # 调用Agent的generate_reaction
        if not hasattr(agent, 'generate_reaction'):
            raise RuntimeError(f"Agent {agent.agent_id} 没有generate_reaction方法")

        try:
            # generate_reaction会自动整合profile、memory、planning
            reaction = await agent.generate_reaction(instruction, observation)

            # 解析批量回答
            answers = self._extract_answers_from_batch_reaction(reaction, questions)

            return answers

        except Exception as e:
            logger.error(f"Agent {agent.agent_id} 批量回答问题时出错: {e}")
            # 返回空答案列表
            return [Answer(question_id=q.id, value=None, reasoning=f"批量回答失败: {e}") for q in questions]

    async def _ask_agent_question(
        self,
        agent: Any,
        question: Question,
        questionnaire: Questionnaire
    ) -> Answer:
        """
        向Agent询问单个问题 (基于Agent的profile和memory上下文)

        Args:
            agent: Agent对象
            question: 问题定义
            questionnaire: 问卷定义

        Returns:
            答案
        """
        # 构建问卷上下文作为observation
        observation = self._build_question_context(question, questionnaire)

        # 构建instruction,要求JSON格式回答
        instruction = self._build_question_instruction(question)

        # 调用Agent的generate_reaction获取基于profile和memory的回答
        if not hasattr(agent, 'generate_reaction'):
            raise RuntimeError(f"Agent {agent.agent_id} 没有generate_reaction方法")

        try:
            # generate_reaction会自动整合profile、memory、planning
            reaction = await agent.generate_reaction(instruction, observation)

            # 解析reaction中的答案
            answer_data = self._extract_answer_from_reaction(reaction, question)

            return Answer(
                question_id=question.id,
                value=answer_data.get("value"),
                reasoning=answer_data.get("reasoning"),
                confidence=answer_data.get("confidence")
            )
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} 回答问题 {question.id} 时出错: {e}")
            raise

    def _build_question_context(self, question: Question, questionnaire: Questionnaire) -> str:
        """
        构建问题上下文(作为observation传递给generate_reaction)

        Args:
            question: 问题定义
            questionnaire: 问卷定义

        Returns:
            上下文字符串
        """
        context_parts = [
            f"问卷调查: {questionnaire.title}",
            f"问卷说明: {questionnaire.description}",
            "",
            f"当前问题: {question.text}"
        ]

        # 添加选项或范围信息
        if question.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            context_parts.append(f"可选选项: {', '.join(question.options)}")
        elif question.question_type == QuestionType.SCALE:
            context_parts.append(f"评分范围: {question.scale_range[0]} 到 {question.scale_range[1]}")
        elif question.question_type == QuestionType.BOOLEAN:
            context_parts.append("请回答: true 或 false")

        return "\n".join(context_parts)

    def _build_question_instruction(self, question: Question) -> str:
        """
        构建回答指令(作为instruction传递给generate_reaction)

        Args:
            question: 问题定义

        Returns:
            指令字符串
        """
        instruction_parts = [
            "请基于你的个人profile、记忆和当前处境,真实地回答这个问卷问题。",
            "",
            "回答要求:",
            "1. 从你的角色视角出发,结合你的性格、经历、价值观来回答",
            "2. 如果有相关记忆,参考你过去的经历",
            "3. 给出你的推理过程",
            "",
            "请以JSON格式回答,包含以下字段:",
            "- value: 你的答案"
        ]

        # 根据问题类型添加具体要求
        if question.question_type == QuestionType.SINGLE_CHOICE:
            instruction_parts.append(f"  (必须从以下选项中选择一个: {', '.join(question.options)})")
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            instruction_parts.append(f"  (可以从以下选项中选择多个,返回列表: {', '.join(question.options)})")
        elif question.question_type == QuestionType.SCALE:
            instruction_parts.append(f"  (必须是{question.scale_range[0]}到{question.scale_range[1]}之间的数字)")
        elif question.question_type == QuestionType.BOOLEAN:
            instruction_parts.append("  (必须是true或false)")

        instruction_parts.extend([
            "- reasoning: 你的推理过程(解释为什么这样回答)",
            "- confidence: 你对这个答案的确定程度(0-1之间的数字)",
            "",
            "示例格式:",
            json.dumps({
                "value": "你的答案",
                "reasoning": "基于我的经历和价值观...",
                "confidence": 0.8
            }, ensure_ascii=False, indent=2)
        ])

        return "\n".join(instruction_parts)

    def _extract_answer_from_reaction(self, reaction: Dict[str, Any], question: Question) -> Dict[str, Any]:
        """
        从Agent的reaction中提取问卷答案

        Args:
            reaction: Agent的reaction字典 (generate_reaction返回值)
            question: 问题定义

        Returns:
            解析后的答案数据
        """
        try:
            # reaction已经是dict,直接验证格式
            if not isinstance(reaction, dict):
                raise ValueError(f"Reaction必须是dict类型,实际类型: {type(reaction)}")

            # 验证必需字段
            if "value" not in reaction:
                raise ValueError("Reaction缺少 'value' 字段")

            # 类型验证和转换
            value = reaction["value"]

            if question.question_type == QuestionType.SCALE:
                value = float(value)
                min_val, max_val = question.scale_range
                if not (min_val <= value <= max_val):
                    logger.warning(f"量表答案 {value} 超出范围 [{min_val}, {max_val}]")

            elif question.question_type == QuestionType.BOOLEAN:
                value = bool(value)

            elif question.question_type == QuestionType.MULTIPLE_CHOICE:
                if not isinstance(value, list):
                    value = [value]

            # 构建答案数据
            answer_data = {
                "value": value,
                "reasoning": reaction.get("reasoning"),
                "confidence": reaction.get("confidence")
            }

            return answer_data

        except Exception as e:
            logger.error(f"从reaction提取答案失败: {e}\nReaction内容: {reaction}")
            return {"value": None, "reasoning": f"提取失败: {e}", "confidence": None}

    def _build_questions_batch_context(self, questions: List[Question], questionnaire: Questionnaire) -> str:
        """
        构建批量问题上下文

        Args:
            questions: 问题列表
            questionnaire: 问卷定义

        Returns:
            上下文字符串
        """
        context_parts = [
            f"问卷调查: {questionnaire.title}",
            f"问卷说明: {questionnaire.description}",
            "",
            f"请回答以下 {len(questions)} 个问题:"
        ]

        # 添加每个问题
        for idx, question in enumerate(questions, 1):
            context_parts.append(f"\n问题 {idx} (ID: {question.id}): {question.text}")

            # 添加选项或范围信息
            if question.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
                context_parts.append(f"  可选选项: {', '.join(question.options)}")
            elif question.question_type == QuestionType.SCALE:
                context_parts.append(f"  评分范围: {question.scale_range[0]} 到 {question.scale_range[1]}")
            elif question.question_type == QuestionType.BOOLEAN:
                context_parts.append("  请回答: true 或 false")

        return "\n".join(context_parts)

    def _build_questions_batch_instruction(self, questions: List[Question]) -> str:
        """
        构建批量回答指令

        Args:
            questions: 问题列表

        Returns:
            指令字符串
        """
        instruction_parts = [
            "请基于你的个人profile、记忆和当前处境,真实地回答这些问卷问题。",
            "",
            "回答要求:",
            "1. 从你的角色视角出发,结合你的性格、经历、价值观来回答",
            "2. 如果有相关记忆,参考你过去的经历",
            "3. 给出你的推理过程",
            "",
            "请以JSON格式回答,使用 'answers' 数组,每个问题一个对象:",
            json.dumps({
                "answers": [
                    {
                        "question_id": "q1",
                        "value": "你的答案",
                        "reasoning": "基于我的经历和价值观...",
                        "confidence": 0.8
                    },
                    {
                        "question_id": "q2",
                        "value": "另一个答案",
                        "reasoning": "我的思考过程...",
                        "confidence": 0.9
                    }
                ]
            }, ensure_ascii=False, indent=2),
            "",
            "注意事项:"
        ]

        # 为每个问题添加具体要求
        for question in questions:
            if question.question_type == QuestionType.SINGLE_CHOICE:
                instruction_parts.append(
                    f"- {question.id}: 从选项中选择一个: {', '.join(question.options)}"
                )
            elif question.question_type == QuestionType.MULTIPLE_CHOICE:
                instruction_parts.append(
                    f"- {question.id}: 可以选择多个选项,返回列表: {', '.join(question.options)}"
                )
            elif question.question_type == QuestionType.SCALE:
                instruction_parts.append(
                    f"- {question.id}: 必须是{question.scale_range[0]}到{question.scale_range[1]}之间的数字"
                )
            elif question.question_type == QuestionType.BOOLEAN:
                instruction_parts.append(f"- {question.id}: 必须是true或false")

        return "\n".join(instruction_parts)

    def _extract_answers_from_batch_reaction(
        self,
        reaction: Dict[str, Any],
        questions: List[Question]
    ) -> List[Answer]:
        """
        从批量reaction中提取答案列表

        Args:
            reaction: Agent的reaction字典
            questions: 问题列表

        Returns:
            答案列表
        """
        try:
            if not isinstance(reaction, dict):
                raise ValueError(f"Reaction必须是dict类型,实际类型: {type(reaction)}")

            # 检查是否有answers数组
            if "answers" not in reaction:
                raise ValueError("Reaction缺少 'answers' 字段")

            answers_data = reaction["answers"]
            if not isinstance(answers_data, list):
                raise ValueError(f"answers必须是list类型,实际类型: {type(answers_data)}")

            # 创建question_id到question的映射
            question_map = {q.id: q for q in questions}

            # 解析每个答案
            answers = []
            for answer_data in answers_data:
                if not isinstance(answer_data, dict):
                    logger.warning(f"跳过非dict类型的答案: {answer_data}")
                    continue

                question_id = answer_data.get("question_id")
                if not question_id or question_id not in question_map:
                    logger.warning(f"未知的question_id: {question_id}")
                    continue

                question = question_map[question_id]

                # 类型验证和转换
                value = answer_data.get("value")
                if value is not None:
                    if question.question_type == QuestionType.SCALE:
                        value = float(value)
                        min_val, max_val = question.scale_range
                        if not (min_val <= value <= max_val):
                            logger.warning(f"量表答案 {value} 超出范围 [{min_val}, {max_val}]")

                    elif question.question_type == QuestionType.BOOLEAN:
                        value = bool(value)

                    elif question.question_type == QuestionType.MULTIPLE_CHOICE:
                        if not isinstance(value, list):
                            value = [value]

                answers.append(Answer(
                    question_id=question_id,
                    value=value,
                    reasoning=answer_data.get("reasoning"),
                    confidence=answer_data.get("confidence")
                ))

            # 检查是否所有问题都有答案
            answered_ids = {a.question_id for a in answers}
            for question in questions:
                if question.id not in answered_ids:
                    logger.warning(f"问题 {question.id} 没有答案,添加空答案")
                    answers.append(Answer(
                        question_id=question.id,
                        value=None,
                        reasoning="Agent未提供答案"
                    ))

            return answers

        except Exception as e:
            logger.error(f"从批量reaction提取答案失败: {e}\nReaction内容: {reaction}")
            # 返回所有问题的空答案
            return [
                Answer(question_id=q.id, value=None, reasoning=f"批量提取失败: {e}")
                for q in questions
            ]

    def get_result(self, questionnaire_id: str) -> Optional[QuestionnaireResult]:
        """
        获取问卷结果

        Args:
            questionnaire_id: 问卷ID

        Returns:
            问卷结果,不存在则返回None
        """
        return self.results.get(questionnaire_id)

    def export_result_to_json(self, questionnaire_id: str, filepath: str) -> None:
        """
        导出问卷结果为JSON文件

        Args:
            questionnaire_id: 问卷ID
            filepath: 导出文件路径
        """
        if questionnaire_id not in self.results:
            raise ValueError(f"问卷结果 {questionnaire_id} 不存在")

        result = self.results[questionnaire_id]
        result.to_json(filepath)
        logger.info(f"问卷结果已导出到: {filepath}")

    def get_all_questionnaires(self) -> Dict[str, Questionnaire]:
        """获取所有已注册问卷"""
        return self.questionnaires.copy()

    def get_all_results(self) -> Dict[str, QuestionnaireResult]:
        """获取所有问卷结果"""
        return self.results.copy()

    def analyze_result(self, questionnaire_id: str) -> Dict[str, Any]:
        """
        分析问卷结果,生成统计数据

        Args:
            questionnaire_id: 问卷ID

        Returns:
            统计分析结果
        """
        if questionnaire_id not in self.results:
            raise ValueError(f"问卷结果 {questionnaire_id} 不存在")

        result = self.results[questionnaire_id]
        questionnaire = self.questionnaires[questionnaire_id]

        analysis = {
            "questionnaire_id": questionnaire_id,
            "questionnaire_title": questionnaire.title,
            "total_responses": result.response_count,
            "agent_types": result.agent_types,
            "questions": {}
        }

        # 分析每个问题
        for question in questionnaire.questions:
            stats = result.get_question_statistics(question.id)
            analysis["questions"][question.id] = {
                "text": question.text,
                "type": question.question_type.value,
                "statistics": stats
            }

        return analysis
