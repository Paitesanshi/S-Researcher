"""
Questionnaire data structures for agent surveys.

This module defines the core data structures for creating and managing questionnaires
that can be administered to agents in simulations.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import json


class QuestionType(str, Enum):
    """问题类型枚举"""
    SINGLE_CHOICE = "single_choice"  # 单选题
    MULTIPLE_CHOICE = "multiple_choice"  # 多选题
    SCALE = "scale"  # 量表题(如1-5评分)
    TEXT = "text"  # 文本题
    BOOLEAN = "boolean"  # 是非题


@dataclass
class Question:
    """单个问题定义"""

    id: str  # 问题唯一ID
    text: str  # 问题文本
    question_type: QuestionType  # 问题类型
    options: Optional[List[str]] = None  # 选项列表(单选/多选题)
    scale_range: Optional[tuple] = None  # 量表范围(min, max)
    required: bool = True  # 是否必答
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据

    def __post_init__(self):
        """验证问题定义"""
        if self.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE]:
            if not self.options or len(self.options) < 2:
                raise ValueError(f"Question {self.id}: Choice questions must have at least 2 options")

        if self.question_type == QuestionType.SCALE:
            if not self.scale_range or len(self.scale_range) != 2:
                raise ValueError(f"Question {self.id}: Scale questions must have (min, max) range")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "text": self.text,
            "question_type": self.question_type.value,
            "options": self.options,
            "scale_range": self.scale_range,
            "required": self.required,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """从字典创建问题"""
        return cls(
            id=data["id"],
            text=data["text"],
            question_type=QuestionType(data["question_type"]),
            options=data.get("options"),
            scale_range=tuple(data["scale_range"]) if data.get("scale_range") else None,
            required=data.get("required", True),
            metadata=data.get("metadata", {})
        )


@dataclass
class Questionnaire:
    """问卷定义"""

    id: str  # 问卷唯一ID
    title: str  # 问卷标题
    description: str  # 问卷描述
    questions: List[Question]  # 问题列表
    target_agent_types: Optional[List[str]] = None  # 目标Agent类型,None表示所有类型
    created_at: float = field(default_factory=time.time)  # 创建时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据

    def __post_init__(self):
        """验证问卷定义"""
        if not self.questions:
            raise ValueError(f"Questionnaire {self.id} must have at least one question")

        # 检查问题ID唯一性
        question_ids = [q.id for q in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError(f"Questionnaire {self.id}: Question IDs must be unique")

    @property
    def formatted_created_time(self) -> str:
        """格式化创建时间"""
        return datetime.fromtimestamp(self.created_at).strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式(用于JSON导出)"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "questions": [q.to_dict() for q in self.questions],
            "target_agent_types": self.target_agent_types,
            "created_at": self.created_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Questionnaire':
        """从字典创建问卷"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            questions=[Question.from_dict(q) for q in data["questions"]],
            target_agent_types=data.get("target_agent_types"),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {})
        )

    def to_json(self, filepath: str) -> None:
        """导出为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, filepath: str) -> 'Questionnaire':
        """从JSON文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class Answer:
    """单个问题的答案"""

    question_id: str  # 问题ID
    value: Union[str, int, List[str], bool, None]  # 答案值
    reasoning: Optional[str] = None  # 推理过程(可选,LLM生成时有用)
    confidence: Optional[float] = None  # 置信度(可选,0-1之间)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "question_id": self.question_id,
            "value": self.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Answer':
        """从字典创建"""
        return cls(
            question_id=data["question_id"],
            value=data["value"],
            reasoning=data.get("reasoning"),
            confidence=data.get("confidence")
        )


@dataclass
class QuestionnaireResponse:
    """问卷响应(单个Agent的完整答卷)"""

    questionnaire_id: str  # 问卷ID
    agent_id: str  # Agent ID
    agent_type: str  # Agent类型
    answers: List[Answer]  # 答案列表
    completed_at: float = field(default_factory=time.time)  # 完成时间
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据

    @property
    def formatted_completed_time(self) -> str:
        """格式化完成时间"""
        return datetime.fromtimestamp(self.completed_at).strftime('%Y-%m-%d %H:%M:%S')

    def get_answer(self, question_id: str) -> Optional[Answer]:
        """获取指定问题的答案"""
        for answer in self.answers:
            if answer.question_id == question_id:
                return answer
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "questionnaire_id": self.questionnaire_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "answers": [a.to_dict() for a in self.answers],
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestionnaireResponse':
        """从字典创建"""
        return cls(
            questionnaire_id=data["questionnaire_id"],
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            answers=[Answer.from_dict(a) for a in data["answers"]],
            completed_at=data.get("completed_at", time.time()),
            metadata=data.get("metadata", {})
        )


@dataclass
class QuestionnaireResult:
    """问卷调查结果汇总"""

    questionnaire_id: str  # 问卷ID
    responses: List[QuestionnaireResponse]  # 所有响应
    collected_at: float = field(default_factory=time.time)  # 收集时间

    @property
    def response_count(self) -> int:
        """响应数量"""
        return len(self.responses)

    @property
    def agent_types(self) -> List[str]:
        """参与的Agent类型"""
        return list(set(r.agent_type for r in self.responses))

    @property
    def formatted_collected_time(self) -> str:
        """格式化收集时间"""
        return datetime.fromtimestamp(self.collected_at).strftime('%Y-%m-%d %H:%M:%S')

    def get_responses_by_agent_type(self, agent_type: str) -> List[QuestionnaireResponse]:
        """按Agent类型筛选响应"""
        return [r for r in self.responses if r.agent_type == agent_type]

    def get_question_statistics(self, question_id: str) -> Dict[str, Any]:
        """获取某个问题的统计数据"""
        answers = []
        for response in self.responses:
            answer = response.get_answer(question_id)
            if answer and answer.value is not None:
                answers.append(answer.value)

        if not answers:
            return {"count": 0, "values": []}

        stats = {"count": len(answers)}

        # 数值型数据统计
        if all(isinstance(a, (int, float)) for a in answers):
            stats["mean"] = sum(answers) / len(answers)
            stats["min"] = min(answers)
            stats["max"] = max(answers)
            stats["values"] = answers
        # 分类数据统计
        else:
            from collections import Counter
            value_counts = Counter(str(a) for a in answers)
            stats["distribution"] = dict(value_counts)
            stats["values"] = answers

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "questionnaire_id": self.questionnaire_id,
            "responses": [r.to_dict() for r in self.responses],
            "collected_at": self.collected_at,
            "statistics": {
                "response_count": self.response_count,
                "agent_types": self.agent_types
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestionnaireResult':
        """从字典创建"""
        return cls(
            questionnaire_id=data["questionnaire_id"],
            responses=[QuestionnaireResponse.from_dict(r) for r in data["responses"]],
            collected_at=data.get("collected_at", time.time())
        )

    def to_json(self, filepath: str) -> None:
        """导出结果为JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, filepath: str) -> 'QuestionnaireResult':
        """从JSON加载结果"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
