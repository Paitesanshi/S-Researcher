import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# 兼容包导入（优先绝对导入，失败时使用相对）
try:
    from researcher.analysis.agent.llm.agent_client import SimpleChatLLM
    from researcher.analysis.agent.data_analysis.method_chooser_agent import MethodChooserAgent
    from researcher.analysis.agent.utils.tool_registry import TOOLS
except Exception:
    try:
        from ..llm.agent_client import SimpleChatLLM  # 当作为包运行时
        from .method_chooser_agent import MethodChooserAgent
        from ..utils.tool_registry import TOOLS
    except Exception as e:
        raise RuntimeError(f"Failed to import SimpleChatLLM or MethodChooserAgent: {e}")

def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def _find_project_root() -> Path:
    """
    推断仓库根目录：当前文件位于 src/researcher/analysis/agent 下，
    根目录是向上 4 层（agent -> analysis -> researcher -> src -> ROOT）
    """
    here = Path(__file__).resolve()
    # parents[0]=agent, [1]=analysis, [2]=researcher, [3]=src, [4]=ROOT
    return here.parents[4]

def _resolve_project_dir(project_arg: str) -> Path:
    """
    支持传入：
    - 'social_dynamics'
    - 'projects/social_dynamics'
    - 绝对路径
    """
    if not project_arg:
        raise ValueError("project 参数不能为空")

    if os.path.isabs(project_arg) and os.path.isdir(project_arg):
        return Path(project_arg)

    root = _find_project_root()

    # 候选路径
    candidates = [
        root / project_arg,  # e.g., ROOT/social_dynamics
        root / Path(project_arg.strip("/")),  # e.g., ROOT/projects/social_dynamics
        root / "projects" / project_arg,  # e.g., ROOT/projects/social_dynamics
    ]
    for c in candidates:
        if c.is_dir():
            return c

    # 最后兜底：如果传入 'projects/social_dynamics' 但真实在 'social_dynamics'
    if "projects/" in project_arg:
        maybe = root / project_arg.split("projects/", 1)[1]
        if maybe.is_dir():
            return maybe

    raise FileNotFoundError(f"无法解析项目目录: {project_arg}")

def _extract_groups(project_summary: Optional[Dict[str, Any]], workflow_state: Optional[Dict[str, Any]]) -> List[str]:
    groups: List[str] = []
    # 优先从 experiment_design.group_details
    try:
        details = (project_summary or {}).get("experiment_design", {}).get("group_details", [])
        for d in details:
            gid = d.get("group_id")
            if isinstance(gid, str):
                groups.append(gid)
    except Exception:
        pass

    # 次选从 workflow_state.simulation_results.simulation_results.simulation_details 的键
    if not groups and isinstance(workflow_state, dict):
        try:
            sim_details = workflow_state.get("simulation_results", {}).get("simulation_results", {}).get("simulation_details", {})
            if isinstance(sim_details, dict):
                groups = list(sim_details.keys())
        except Exception:
            pass

    return groups

def _extract_dependent_variable(scene_info: Optional[Dict[str, Any]], research_question: Optional[str]) -> str:
    # 优先 scene_info.dependent_variable
    try:
        dv = (scene_info or {}).get("dependent_variable")
        if isinstance(dv, str) and dv.strip():
            return dv.strip()
    except Exception:
        pass

    # 从研究问题中简单解析（示例中为 "number of cultural regions"）
    if isinstance(research_question, str):
        # 常见度量短语捕获
        m = re.search(r"number of [A-Za-z ]+regions", research_question, flags=re.IGNORECASE)
        if m:
            return m.group(0)

        # 备选：Cultural Homogeneity Index
        if "homogeneity" in research_question.lower():
            return "Cultural Homogeneity Index"

    # 最后兜底
    return "number of cultural regions"

def _extract_independent_variables(research_question: Optional[str]) -> List[str]:
    vars_: List[str] = []
    if isinstance(research_question, str):
        # 抓取 "degree of X" 模式
        for m in re.finditer(r"degree of ([A-Za-z ]+)", research_question, flags=re.IGNORECASE):
            phrase = m.group(0).strip()
            if phrase not in vars_:
                vars_.append(phrase)

        # 额外补全：如果提到了 "information flow" 但没带 "degree of"
        if "information flow" in research_question.lower() and not any("information flow" in v.lower() for v in vars_):
            vars_.append("degree of information flow")

    # 兜底：至少有一个
    if not vars_:
        vars_.append("degree of openness")
    return vars_

def _find_data_file(project_dir: Path) -> Optional[str]:
    """
    优先返回“处理后的分组数据”的相对路径，示例：
    analysis/data/processed/Cultural_Homogeneity_Index_all_groups.json
    如果没有找到，则返回 None（不再回退到 data_analysis.json）。
    """
    root = _find_project_root()

    # 首选：collection_summary_all_groups.json（若存在）
    coll_path = project_dir / "analysis" / "data" / "collection_summary_all_groups.json"
    if coll_path.exists():
        try:
            payload = _read_json(coll_path) or {}
            data_file = payload.get("data_file")
            if isinstance(data_file, str) and data_file.strip():
                return data_file.strip()
        except Exception:
            pass

    # 备选：常见的 processed 路径
    candidates = [
        project_dir / "analysis" / "data" / "processed" / "Cultural_Homogeneity_Index_all_groups.json",
        project_dir / "analysis" / "data" / "processed" / "Cultural_Homogeneity_Index.json",
        project_dir / "analysis" / "data" / "Cultural_Homogeneity_Index_all_groups.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                return str(p.relative_to(root))
            except Exception:
                return str(p)

    # 通配搜索 *_all_groups.json
    try:
        for p in (project_dir / "analysis").rglob("*_all_groups.json"):
            if p.is_file():
                try:
                    return str(p.relative_to(root))
                except Exception:
                    return str(p)
    except Exception:
        pass

    # 不再回退到 data_analysis.json，返回 None
    return None

def build_context(project_dir: Path) -> Dict[str, Any]:
    root = _find_project_root()

    # 读取文件
    workflow_state = _read_json(project_dir / "workflow_state.json") or {}
    project_summary = _read_json(project_dir / "project_summary.json") or {}
    scene_info = _read_json(project_dir / "analysis" / "data" / "scene_info.json")  # 可能不存在

    research_paradigm = workflow_state.get("research_paradigm")
    research_question = workflow_state.get("research_question")

    groups = _extract_groups(project_summary, workflow_state)
    dependent_variable = _extract_dependent_variable(scene_info, research_question)
    data_file = _find_data_file(project_dir)

    # category：若 scene_info 有指标说明则用其名称，否则用 dependent_variable
    category = None
    try:
        category = (scene_info or {}).get("metric_name") or (scene_info or {}).get("category")
    except Exception:
        category = None
    if not category:
        category = dependent_variable

    # 构造 context（按你示例），并补充 dependent_variable
    context: Dict[str, Any] = {
        "research_paradigm": research_paradigm,
        "research_question": research_question,
        "category": category,
        "data_file": data_file,
        "groups": groups,
        "dependent_variable": dependent_variable,  # 新增
    }
    return context

def compose_system_prompt() -> str:
    return (
        "Return ONLY valid JSON with keys:\n"
        "- model_name (statistical test to apply, e.g., ANOVA, t-test, regression)\n"
        "- data_path (relative path to input file)\n"
        "- research_purpose (from research_question)\n"
        "- groups (list of experimental groups)\n"
        "- dependent_variable (metric under study)\n"
        "- independent_variables (list of factors from research_question)\n"
        "- methods (AT LEAST 3). Each method MUST include:\n"
        "    - name (e.g., one_way_anova, pairwise_t_tests, ols_regression)\n"
        "    - apply_to (which subset of data to use; reference the data_path)\n"
        "    - params (key parameters, e.g., alpha, correction, formula)\n"
        "    - description (a brief description of what this method examines in context)\n"
        "\n"
        "IMPORTANT VARIABLE NAMING RULES:\n"
        "- Processed data files have structure: {'data': [{'group_name': ..., 'step': ..., 'data': value, ...}]}\n"
        "- The actual metric values are in the 'data' column of the DataFrame\n"
        "- For OLS regression formulas, use 'data' as the dependent variable name\n"
        "- Independent variables should match actual DataFrame columns (e.g., 'group_name', 'step')\n"
        "- Example correct formula: 'data ~ C(group_name)' NOT 'number_of_cultural_regions ~ ...'\n"
        "\n"
        "If 'data_file' is present in the input context, use it as 'data_path'. If not, propose a reasonable processed file path like 'analysis/data/processed/Cultural_Homogeneity_Index_all_groups.json'."
    )

def plan_analysis_request(context: Dict[str, Any], llm: SimpleChatLLM, temperature: float = 0.7) -> Dict[str, Any]:
    system_prompt = compose_system_prompt()
    user_query = json.dumps(context, ensure_ascii=False)

    # 尝试从 LLM 获取基础字段，但不再因校验失败直接回退；我们统一用 MethodChooserAgent 生成 methods
    base: Dict[str, Any] = {}
    try:
        llm_resp = llm.chat_json(
            user_query=user_query,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        # 取用可能存在的字段，否则后续补齐
        base = llm_resp if isinstance(llm_resp, dict) else {}
    except Exception:
        base = {}

    # 从 context 补齐关键字段
    rq = context.get("research_question") or ""
    indeps = _extract_independent_variables(rq)
    groups = context.get("groups") or []
    dv = context.get("dependent_variable") or (context.get("category") or "metric")
    data_file = context.get("data_file")
    suggested_path = "analysis/data/processed/Cultural_Homogeneity_Index_all_groups.json"

    # 简单模型名称选择（与原逻辑一致）
    if isinstance(groups, list) and len(groups) > 2:
        model_name = "ANOVA"
    elif isinstance(groups, list) and len(groups) == 2:
        model_name = "t-test"
    else:
        model_name = "regression"

    analysis_request: Dict[str, Any] = {
        "model_name": base.get("model_name") or model_name,
        "data_path": base.get("data_path") or (data_file or suggested_path),
        "research_purpose": base.get("research_purpose") or rq,
        "groups": base.get("groups") or groups,
        "dependent_variable": base.get("dependent_variable") or dv,
        "independent_variables": base.get("independent_variables") or indeps or [],
        # methods 由 MethodChooserAgent 生成并填充完整结构
    }

    # 使用 MethodChooserAgent 生成 methods（严格来自 tool_registry）
    chooser = MethodChooserAgent(llm=llm)
    chosen = chooser.choose_analysis_methods(
        research_paradigm=context.get("research_paradigm"),
        research_question=rq,
        category=context.get("category"),
        time_field="step",            # 与数据规范保持一致
        value_field="data",           # 依从 stage3 说明：DV 用 'data' 列名
        group_fields=["group_name"],  # 典型分组列
        max_methods=3,
        temperature=0.3,
    )

    # 临时日志：打印选择到的方法数量
    methods_len = len(chosen.get("methods") or [])
    logging.info(f"[data_planner] MethodChooserAgent returned {methods_len} methods")

    methods_out = []
    for m in (chosen.get("methods") or []):
        name = m.get("name")
        params = m.get("params") or {}
        desc = TOOLS.get(name, {}).get("description", f"Selected method: {name}")
        methods_out.append({
            "name": name,
            "apply_to": {
                "data": (data_file or suggested_path),
                "groups": groups,
                "target": dv,
            },
            "params": params,
            "description": desc,
        })

    # 若 LLM 或选择器异常，兜底不为空
    if not methods_out:
        methods_out = [
            {
                "name": "time_series_correlation",
                "apply_to": {
                    "data": (data_file or suggested_path),
                    "groups": groups,
                    "target": dv,
                },
                "params": {"x": "step", "y": "data"},
                "description": TOOLS.get("time_series_correlation", {}).get("description", "Correlation between step and data"),
            }
        ]

    analysis_request["methods"] = methods_out
    return analysis_request

def save_analysis_request(project_dir: Path, analysis_request: Dict[str, Any], output_path: Optional[str] = None) -> Path:
    """
    默认保存到：{project_dir}/analysis/data/analysis_request.json
    若指定 output_path 则使用该路径（相对或绝对）。
    """
    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = _find_project_root() / out
    else:
        out = project_dir / "analysis" / "data" / "analysis_request.json"

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(analysis_request, f, ensure_ascii=False, indent=2)
    return out

def main():
    parser = argparse.ArgumentParser(
        description="Generate an analysis_request.json plan."
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name or path",
    )
    parser.add_argument(
        "--config-name",
        type=str,
        default="default-chat",
        help="Model configuration name",
    )
    parser.add_argument(
        "--config-path",
        type=str,
        default="config/model_config.json",
        help="Model configuration file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output path",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Model temperature",
    )
    args = parser.parse_args()

    project_dir = _resolve_project_dir(args.project)

    # 构造 context
    context = build_context(project_dir)

    # 将 research_question 中的因素解析后补全给 LLM（作为 context 的辅助）
    # 这部分可以不改 context 的原始字段，直接供 LLM参考或回退使用
    # 这里保持最小偏置：仅在回退时使用
    # 初始化 LLM
    llm = SimpleChatLLM(config_name=args.config_name, config_path=args.config_path)

    # 生成 analysis_request
    analysis_request = plan_analysis_request(context, llm, temperature=args.temperature)

    # 保存输出
    out_path = save_analysis_request(project_dir, analysis_request, output_path=args.output)
    print(f"Analysis request saved to: {out_path}")

if __name__ == "__main__":
    main()

# 临时开启基础日志配置（INFO），确保能看到日志输出
logging.basicConfig(level=logging.INFO)
