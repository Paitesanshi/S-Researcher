"""
Executor for Deep Research Module
Adapted from OnePage/deep_research_agent with loguru logging
"""

import json
from typing import Any, Dict, List, Set, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from .schemas import DAGPlan, CompressedResult, ToolOutputSchema, DAGNode
from .config import get_settings


class Executor:
    """
    DAG 执行器 - 流式执行 + 条件分支

    核心设计哲学:
    1. 基于入度的拓扑排序
    2. 真正的流式执行: 完成1个 → 立即释放后继
    3. 条件执行: 节点可以有condition字段
    4. 并发执行: 所有入度为0的节点并发执行
    """

    def __init__(
        self,
        tools_registry: Dict[str, Any],
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        初始化执行器

        Args:
            tools_registry: 工具名称 -> 工具实例的映射
            progress_callback: 可选的进度回调
        """
        logger.info("Executor: Initialized with streaming execution")
        self.tools_registry = tools_registry
        self._progress_callback = progress_callback
        settings = get_settings()
        self.max_workers = settings.max_workers

        # 执行状态
        self.completed_nodes: Set[str] = set()
        self.skipped_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        self.results: Dict[str, Any] = {}

    def _emit_progress(self, message: str) -> None:
        """向外部发送进度信息"""
        if not self._progress_callback:
            return
        try:
            self._progress_callback(message)
        except Exception:
            pass

    def execute_dag(self, plan: DAGPlan, initial_input: Any = None) -> CompressedResult:
        """
        执行DAG计划 (流式执行 + 条件分支)
        """
        logger.info("=" * 60)
        logger.info(f"Executor: Starting DAG execution")
        logger.info(f"Total nodes: {len(plan.nodes)}")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info("=" * 60)

        # 构建节点映射
        node_map = {node.node_id: node for node in plan.nodes}

        # 1. 计算入度
        in_degree = {node_id: len(node.dependencies) for node_id, node in node_map.items()}

        # 2. 构建反向图
        successors: Dict[str, List[str]] = {node_id: [] for node_id in node_map}
        for node_id, node in node_map.items():
            for dep in node.dependencies:
                if dep in successors:
                    successors[dep].append(node_id)

        # 3. 流式执行循环
        total_nodes = len(plan.nodes)
        processed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交初始就绪节点
            futures = {}
            for node_id, degree in in_degree.items():
                if degree == 0:
                    node = node_map[node_id]
                    future = executor.submit(self.execute_single_node, node)
                    futures[future] = node

            # 处理完成的任务
            while futures:
                for completed_future in as_completed(futures):
                    node = futures.pop(completed_future)
                    processed_count += 1

                    try:
                        result = completed_future.result()

                        if result is None:
                            self.skipped_nodes.add(node.node_id)
                            logger.info(f"[{processed_count}/{total_nodes}] ⏭️  Skipped: {node.node_id}")
                        else:
                            self.completed_nodes.add(node.node_id)
                            self.results[node.node_id] = {
                                "status": "success",
                                "result": result,
                                "task": node.task
                            }
                            logger.info(f"[{processed_count}/{total_nodes}] ✅ Completed: {node.node_id}")

                    except Exception as e:
                        self.failed_nodes.add(node.node_id)
                        self.results[node.node_id] = {
                            "status": "failed",
                            "error": str(e),
                            "task": node.task
                        }
                        logger.error(f"[{processed_count}/{total_nodes}] ❌ Failed: {node.node_id} - {str(e)[:80]}")

                        if node.node_type == "required" and node.tool == "paper_search":
                            logger.error(f"Critical search node failed: {node.node_id}")
                            return self._generate_error_result(node.node_id, str(e))
                        else:
                            logger.info("   ℹ️  Non-critical failure, continuing...")

                    # 更新后继节点的入度
                    for successor_id in successors.get(node.node_id, []):
                        in_degree[successor_id] -= 1

                        if in_degree[successor_id] == 0:
                            successor_node = node_map[successor_id]
                            future = executor.submit(self.execute_single_node, successor_node)
                            futures[future] = successor_node
                            logger.debug(f"   ↳ Queued successor: {successor_id}")

        logger.info("=" * 60)
        logger.info(
            f"Executor: completed. "
            f"Completed: {len(self.completed_nodes)}, "
            f"Skipped: {len(self.skipped_nodes)}, "
            f"Failed: {len(self.failed_nodes)}"
        )
        logger.info("=" * 60)

        return self._extract_final_result(plan)

    def execute_single_node(self, node: DAGNode) -> Any:
        """执行单个节点"""
        logger.debug(f"▶️  Executing node: {node.node_id} (tool: {node.tool})")

        # 1. 检查执行条件
        if node.condition:
            if not self._check_condition(node.condition):
                logger.debug(f"   ⏸️  Condition not met, skipping: {node.node_id}")
                return None

        # 2. 获取工具
        tool = self.tools_registry.get(node.tool)
        if not tool:
            raise ValueError(f"Unknown tool: {node.tool}")

        # 3. 解析输入参数
        try:
            resolved_inputs = self._resolve_tool_inputs(node.tool_inputs)
        except Exception as e:
            raise RuntimeError(f"Failed to resolve inputs for {node.node_id}: {e}") from e

        # 4. 执行工具
        try:
            result = tool.run(**resolved_inputs)
            return result
        except Exception as e:
            raise RuntimeError(f"Tool {node.tool} failed: {e}") from e

    def _check_condition(self, condition: Dict[str, Any]) -> bool:
        """检查节点执行条件"""
        cond_type = condition.get("type")

        if cond_type == "check_decision":
            node_id = condition.get("node")
            expected = condition.get("expected")

            if node_id not in self.results:
                return False

            if self.results[node_id]["status"] != "success":
                return False

            result_data = self._extract_result_data(self.results[node_id]["result"])
            actual_decision = result_data.get("decision")

            return actual_decision == expected

        elif cond_type == "check_count":
            node_id = condition.get("node")
            min_count = condition.get("min", 0)

            if node_id not in self.results or self.results[node_id]["status"] != "success":
                return False

            result_data = self._extract_result_data(self.results[node_id]["result"])
            actual_count = result_data.get("total_results", 0)

            return actual_count >= min_count

        return True

    def _resolve_tool_inputs(self, tool_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """解析工具输入参数"""
        def resolve_value(value: Any) -> Any:
            if isinstance(value, dict) and "from_node" in value:
                ref_node_id = value["from_node"]

                if ref_node_id not in self.results:
                    logger.warning(f"Dependency node '{ref_node_id}' not found")
                    return None

                ref_entry = self.results[ref_node_id]

                if ref_entry["status"] != "success":
                    return None

                return ref_entry["result"]

            if isinstance(value, list):
                resolved_list = [resolve_value(v) for v in value]
                return [r for r in resolved_list if r is not None]

            return value

        return {k: resolve_value(v) for k, v in (tool_inputs or {}).items()}

    def _extract_result_data(self, result: Any) -> Dict[str, Any]:
        """从工具输出中提取数据"""
        if hasattr(result, "raw_json"):
            return json.loads(result.raw_json)
        elif isinstance(result, dict) and "raw_json" in result:
            return json.loads(result["raw_json"])
        elif isinstance(result, dict):
            return result
        else:
            return {}

    def _extract_final_result(self, plan: DAGPlan) -> CompressedResult:
        """从执行结果中提取最终输出"""
        if not plan.nodes:
            return CompressedResult(summary="No nodes in DAG plan", key_findings=[])

        final_node = plan.nodes[-1]
        final_node_id = final_node.node_id

        if final_node_id not in self.completed_nodes:
            for node in reversed(plan.nodes):
                if node.node_id in self.completed_nodes:
                    final_node_id = node.node_id
                    break
            else:
                return CompressedResult(summary="No nodes completed", key_findings=[])

        final_result = self.results[final_node_id]["result"]

        if isinstance(final_result, CompressedResult):
            return final_result

        if isinstance(final_result, ToolOutputSchema):
            try:
                result_dict = json.loads(final_result.raw_json)
                return CompressedResult(
                    summary=result_dict.get("summary", ""),
                    key_findings=result_dict.get("key_findings", [])
                )
            except Exception:
                pass

        return CompressedResult(
            summary=f"Execution completed. Final node: {final_node_id}",
            key_findings=[f"Processed {len(self.completed_nodes)} nodes"]
        )

    def _generate_error_result(self, failed_node_id: str, error_msg: str) -> CompressedResult:
        """生成错误结果"""
        return CompressedResult(
            summary=f"DAG execution failed at node: {failed_node_id}",
            key_findings=[
                f"Error: {error_msg[:200]}",
                f"Completed nodes: {len(self.completed_nodes)}"
            ]
        )
