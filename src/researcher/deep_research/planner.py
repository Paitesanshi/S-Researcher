"""
Planner for Deep Research Module
Adapted from OnePage/deep_research_agent with loguru logging
"""

import json
from typing import List, Dict
from loguru import logger

from .schemas import DAGPlan, DAGNode, TreeNode
from .llm import chat


class Planner:
    """
    动态深度拆解的研究计划生成器

    核心设计哲学：
    1. Layer 是"涌现"的，不是"预设"的
    2. 深度由"可执行性"判断决定
    3. LLM 生成树结构，代码自动计算 layer
    4. 树 → DAG 转换自动插入汇总节点
    """

    def __init__(self):
        logger.info("Planner: Initialized with dynamic depth decomposition")

    def generate_plan(self, query: str) -> DAGPlan:
        """
        智能生成执行计划

        流程：
        1. LLM 生成树形拆解（自己决定深度）
        2. 树 → DAG 转换（自动插入汇总节点）
        3. 自动计算 layer（基于拓扑关系）
        """
        logger.info(f"Planner: Generating plan for query: '{query[:100]}...'")

        # 第一步：生成树形拆解
        tree = self._generate_tree(query)
        if tree is None:
            logger.warning("Planner: Tree generation failed, using simple plan")
            return self._generate_simple_plan(query)

        # 第二步：树 → DAG 转换
        dag_plan = self._tree_to_dag(tree, query)

        # 第三步：验证
        if self._has_cycle(dag_plan.nodes):
            logger.warning("Planner: Cycle detected! Using simple plan.")
            return self._generate_simple_plan(query)

        logger.info(f"Planner: Generated DAG with {len(dag_plan.nodes)} nodes")
        for node in dag_plan.nodes:
            logger.debug(f" - {node.node_id}: {node.task} (deps: {node.dependencies})")
        return dag_plan

    def _generate_tree(self, query: str) -> TreeNode | None:
        """Use the LLM to decompose a question into a search tree."""
        prompt = f"""
You are an expert research planner. Decompose the following question into an
executable literature-search plan.

Question: {query}

**Required rules**:

1. **Executability**:
   A node is executable only if it:
   - contains specific English search terms;
   - includes precise technical concepts;
   - can be submitted directly to OpenAlex or Semantic Scholar; and
   - avoids vague terms such as "research" or "methods" without qualification.

   Examples:
   - "LLM-based cognitive agent architecture" is executable.
   - "multi-agent reinforcement learning" is executable.
   - "LLM agent technology research" is too vague and must be decomposed.
   - "social simulation methods" is too broad and must be decomposed.

2. **Recursive decomposition**:
   - Identify the core dimensions of the question.
   - Mark an insufficiently specific node as type="concept" and decompose it.
   - Mark a sufficiently specific leaf as type="executable".

3. **Dynamic depth**:
   - Simple questions may need only one or two levels.
   - Complex questions may need three to five levels.
   - Different branches may have different depths.

4. **Information independence**:
   - Nodes at the same level should overlap by less than 30 percent.
   - Avoid decompositions that produce substantially duplicate searches.

**Output format (tree-shaped JSON)**:
{{
  "id": "root",
  "type": "concept",
  "question": "{query}",
  "children": [
    {{
      "id": "dim_1",
      "type": "concept",
      "question": "dimension name",
      "reasoning": "why this dimension is necessary",
      "children": [
        {{
          "id": "query_1",
          "type": "executable",
          "query": "specific English search keywords",
          "source": "openalex"
        }}
      ]
    }}
  ]
}}

**Structural constraints**:
- Every type="concept" node must have children.
- A type="executable" node must not have children.
- Every leaf must contain an executable English search query.

{self._get_examples()}

Return the decomposition for the given question as JSON only.
"""

        try:
            response = chat(
                [{"role": "user", "content": prompt}],
                temperature=0.2
            )

            if not response or not response.strip():
                logger.warning("Planner: LLM returned empty response")
                return None
            
            # 尝试提取 JSON（处理可能的 markdown 代码块包装）
            response_stripped = response.strip()
            if response_stripped.startswith("```"):
                lines = response_stripped.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_stripped = "\n".join(lines)

            # 解析 JSON
            tree_data = json.loads(response_stripped)
            tree = TreeNode(**tree_data)

            logger.info(f"Planner: Tree generated with root type={tree.type}")
            logger.debug(f"Planner: Tree structure: {json.dumps(tree_data, indent=2, ensure_ascii=False)}")
            return tree

        except json.JSONDecodeError as e:
            logger.warning(f"Planner: JSON parse failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Planner: Tree generation failed: {e}")
            return None

    def _tree_to_dag(self, tree_root: TreeNode, original_query: str) -> DAGPlan:
        """Convert a search tree into a simplified execution DAG."""
        nodes: List[DAGNode] = []

        def traverse(node: TreeNode, path: List[str] = []) -> List[str]:
            """Recursively traverse the tree and create DAG nodes."""
            if node.type == "executable":
                # 搜索节点
                search_id = node.id
                search_node = DAGNode(
                    node_id=search_id,
                    task=f"Search papers: {node.query}",
                    tool="paper_search",
                    dependencies=[],
                    node_type="required",
                    info_type="fact",
                    tool_inputs={
                        "query": node.query,
                        "source": node.source
                    }
                )
                nodes.append(search_node)

                # 压缩节点 (直接依赖搜索)
                compress_id = f"{search_id}_compress"
                compress_node = DAGNode(
                    node_id=compress_id,
                    task=f"Summarize results: {node.query}",
                    tool="compressor",
                    dependencies=[search_id],
                    node_type="required",
                    info_type="analysis",
                    tool_inputs={
                        "raw_output": {"from_node": search_id},
                        "context": node.query
                    }
                )
                nodes.append(compress_node)

                return [compress_id]

            elif node.type == "concept":
                # 概念节点 → 先处理 children，再创建汇总节点
                child_branch_ids: List[str] = []
                for child in node.children or []:
                    child_branch_ids.extend(traverse(child, path + [node.id]))

                if not child_branch_ids:
                    logger.warning(f"Planner: concept node {node.id} has no children")
                    return []

                # 为这个 concept 创建汇总节点
                summary_id = f"{node.id}_summary"
                summary_node = DAGNode(
                    node_id=summary_id,
                    task=f"Synthesize analysis: {node.question}",
                    tool="compressor",
                    dependencies=child_branch_ids,
                    node_type="required",
                    info_type="synthesis" if len(child_branch_ids) > 1 else "analysis",
                    tool_inputs={
                        "raw_outputs": [{"from_node": cid} for cid in child_branch_ids],
                        "context": node.question
                    }
                )
                nodes.append(summary_node)
                return [summary_id]

            return []

        # 遍历整棵树
        final_node_ids = traverse(tree_root)

        if not nodes:
            logger.warning("Planner: No nodes generated from tree")
            return self._generate_simple_plan(original_query)

        # 创建最终汇总节点（如果有多个顶层节点）
        if len(final_node_ids) > 1:
            final_summary = DAGNode(
                node_id="final_summary",
                task=f"Final synthesis: {original_query}",
                tool="compressor",
                dependencies=final_node_ids,
                node_type="required",
                info_type="evaluation",
                tool_inputs={
                    "raw_outputs": [{"from_node": cid} for cid in final_node_ids],
                    "context": original_query
                }
            )
            nodes.append(final_summary)

        return DAGPlan(
            start_node_id=nodes[0].node_id,
            nodes=nodes
        )

    def _generate_simple_plan(self, query: str) -> DAGPlan:
        """Create the minimal one-node search plan."""
        logger.info("Planner: Using simple plan (1 node)")

        nodes = [
            DAGNode(
                node_id="search_simple",
                task=f"Search relevant papers: {query}",
                tool="paper_search",
                dependencies=[],
                node_type="required",
                info_type="fact",
                tool_inputs={
                    "query": query,
                    "source": "openalex"
                }
            )
        ]

        return DAGPlan(start_node_id="search_simple", nodes=nodes)

    def _has_cycle(self, nodes: List[DAGNode]) -> bool:
        """Detect a cycle using Kahn's algorithm."""
        graph: Dict[str, List[str]] = {node.node_id: [] for node in nodes}
        in_degree: Dict[str, int] = {node.node_id: 0 for node in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep in graph:
                    graph[dep].append(node.node_id)
                    in_degree[node.node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_count = 0

        while queue:
            current = queue.pop(0)
            sorted_count += 1
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_count < len(nodes)

    def _get_examples(self) -> str:
        """Return few-shot decomposition examples."""
        return """
**Example 1: simple question (depth=2)**
Input: \"Transformer architecture\"
Output:
{
  "id": "root",
  "type": "concept",
  "question": "Transformer architecture",
  "children": [
    {
      "id": "q1",
      "type": "executable",
      "query": "Transformer neural network architecture",
      "source": "openalex"
    },
    {
      "id": "q2",
      "type": "executable",
      "query": "self-attention mechanism transformers",
      "source": "openalex"
    }
  ]
}

**Example 2: moderately complex question (depth=3)**
Input: \"Compare the architectural differences between GPT and BERT\"
Output:
{
  "id": "root",
  "type": "concept",
  "question": "Compare GPT and BERT",
  "children": [
    {
      "id": "gpt",
      "type": "concept",
      "question": "GPT architecture",
      "children": [
        {"id": "q1", "type": "executable", "query": "GPT autoregressive language model", "source": "openalex"},
        {"id": "q2", "type": "executable", "query": "GPT decoder-only architecture", "source": "openalex"}
      ]
    },
    {
      "id": "bert",
      "type": "concept",
      "question": "BERT architecture",
      "children": [
        {"id": "q3", "type": "executable", "query": "BERT bidirectional encoder representations", "source": "openalex"},
        {"id": "q4", "type": "executable", "query": "BERT masked language modeling", "source": "openalex"}
      ]
    }
  ]
}
"""
