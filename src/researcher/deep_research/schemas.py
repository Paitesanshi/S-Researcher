"""
Schemas for Deep Research Module
Adapted from OnePage/deep_research_agent
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


class DAGNode(BaseModel):
    """
    定义DAG中的一个节点。
    显式分离了"调度依赖"和"数据流依赖"。
    """
    
    node_id: str = Field(..., description="节点的唯一ID")
    task: str = Field(..., description="该节点要执行的具体任务描述")
    tool: str = Field(..., description="要调用的工具名称")
    
    # 调度/控制流 (Control Flow)
    dependencies: List[str] = Field(
        default_factory=list, 
        description="此节点显式依赖的 node_id 列表"
    )
    
    # 数据流 (Data Flow)
    tool_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="工具的静态输入参数"
    )

    # 元数据 (Metadata)
    node_type: Literal["required", "optional"] = Field(
        default="required",
        description="节点类型：required=关键节点，optional=可选节点"
    )

    info_type: Literal["fact", "analysis", "synthesis", "evaluation"] = Field(
        default="fact",
        description="信息类型：fact=事实, analysis=分析, synthesis=综合, evaluation=评估"
    )

    # 条件执行 (Conditional Execution)
    condition: Dict[str, Any] | None = Field(
        default=None,
        description="节点执行条件"
    )

    fallback_nodes: List[str] = Field(
        default_factory=list,
        description="如果条件不满足,执行这些回退节点的ID列表"
    )


class DAGPlan(BaseModel):
    """
    定义一个完整的执行计划 (DAG)
    """
    start_node_id: str = Field(
        "start_node", 
        description="起始节点的ID"
    )
    
    nodes: List[DAGNode] = Field(..., description="DAG中所有节点的列表")


class ToolOutputSchema(BaseModel):
    """定义工具返回的原始输出结构"""
    
    raw_json: str = Field(..., description="工具的原始JSON输出")


class CompressedResult(BaseModel):
    """定义压缩器返回的结构化摘要"""

    summary: str
    key_findings: List[str] = Field(default_factory=list)


class TreeNode(BaseModel):
    """
    树形节点 - 表达递归拆解结构
    """

    id: str = Field(..., description="节点唯一ID")
    type: Literal["concept", "executable"] = Field(
        ...,
        description="节点类型：concept=需继续拆解，executable=可执行的搜索query"
    )

    # concept 节点的字段
    question: str | None = Field(None, description="概念节点的问题描述")
    reasoning: str | None = Field(None, description="为什么需要这个维度")
    children: List[TreeNode] | None = Field(None, description="子节点列表")

    # executable 节点的字段
    query: str | None = Field(None, description="可执行的搜索关键词（英文）")
    source: str = Field("openalex", description="搜索源：openalex 或 semantic_scholar")
