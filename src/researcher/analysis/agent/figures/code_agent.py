import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

from ..llm.agent_client import SimpleChatLLM


def _sanitize_code(text: str) -> str:
    """Remove markdown code fences like ```python and ``` from model outputs.
    Keep inner content intact and strip leading/trailing whitespace.
    """
    try:
        lines = text.splitlines()
    except Exception:
        return text
    out: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        out.append(line)
    cleaned = "\n".join(out).strip()
    return cleaned


class PlotCodeAgent:
    """
    High-level agent that leverages an LLM to generate and patch
    Python plotting scripts from a VisualizationSpec dict.

    The agent communicates natural-language prompts to the model and expects
    raw Python code (not JSON) in return. It is designed to be extensible:
    - Pluggable model configuration via config_name/config_path
    - Prompt templates are overridable through constructor args
    - Easy to extend with more channels (e.g., critique, explanation)
    """

    def __init__(
        self,
        config_name: str = "default-chat",
        config_path: str = "config/model_config.json",
        system_prompt: Optional[str] = None,
        gen_template: Optional[str] = None,
        patch_template: Optional[str] = None,
    ) -> None:
        cfg_name = os.environ.get("ANALYSIS_PLOT_MODEL_NAME") or os.environ.get("ONESIM_PLOT_MODEL_NAME") or os.environ.get("STAGE2_PLOT_MODEL_NAME") or os.environ.get("ONESIM_MODEL_NAME", config_name)
        cfg_path = os.environ.get("ONESIM_MODEL_CONFIG", config_path)
        self.llm = SimpleChatLLM(config_name=cfg_name, config_path=cfg_path)
        self.system_prompt = (
            system_prompt
            or """
You are PlotCodeAgent, an expert Python data visualization developer.
Your job is to generate runnable Python plotting scripts from a given VisualizationSpec.
Output ONLY Python code. Do not wrap code in markdown fences. Do not return JSON.
Prefer matplotlib or plotly depending on the spec, and import required libraries.
Fail gracefully with comments when fields are ambiguous.
For simulation or time-evolving metrics, treat 'step' (or 'time') as the default x-axis. Ensure x is strictly sorted ascending and include a legend for grouped series.
Always call plt.tight_layout() and plt.show() so headless runners can capture the figure.

Figure type decision policy (non-negotiable):
- Always decide chart type AFTER loading and aggregating data.
- Compute 'unique_steps' from parsed integer 'step_num'.
- If len(unique_steps) <= 1, you MUST override 'suggested_visualization_type' and use a categorical chart:
  - Use a grouped bar chart (preferred), or a single-marker scatter if categories are not applicable.
  - Do NOT use a line plot in single-step scenarios.
  - Use categorical x-axis (e.g., 'group_name' or the flattened category dimension like 'trait'/'role').
  - Add short annotation in the title or footnote indicating 'Single Step'.
- If len(unique_steps) == 2, prefer a scatter with markers rather than a line; annotate points.
- Use a line plot ONLY when len(unique_steps) >= 3.

Style and clarity:
- Write concise, readable, well-structured code.
- Import tick helpers explicitly: 'from matplotlib.ticker import MaxNLocator'. Do not use 'plt.MaxNLocator'.
- Guard legend creation: show a legend only when there is more than one group or series.
- Set xticks before setting xticklabels to avoid FixedFormatter/FixedLocator warnings.
- For categorical bar charts, sort groups alphabetically unless the spec provides a specific order; keep colors stable.

Top-level JSON container rule:
- After 'obj = json.load(f)', treat the loaded JSON as a container:
  - If 'isinstance(obj, dict)' and it contains a 'data' key, set 'records = obj.get("data", [])'.
  - If 'isinstance(obj, list)', set 'records = obj'.
  - Otherwise, set 'records = []'.
- Never iterate a dict expecting record rows; iterate 'records' only.

Type-safe record handling:
- Each record commonly has ['group_name', 'step', 'data'].
- If 'record["data"]' is a dict containing 'xAxis' and 'series', flatten into long-form rows:
  - category_dim: use DATA_JSON_STRUCTURE.flatten_recommendation.dimension if present; else 'trait' for ['Prosocial','Proself'], 'role' for ['Leader','Followers'], otherwise 'category'.
  - value: numeric value aligned to the xAxis label.
  - group_name: propagate if available; parse 'step' to 'step_num' as integer.
- If 'record["data"]' is numeric (int/float) or None, treat it as a scalar measurement:
  - Create rows with ['group_name', 'step_num', 'value'] (or use the spec aggregation field name such as 'contribution').
- Use 'isinstance' checks to branch; never assume one shape blindly.

Strict step/time ordering:
- Always convert 'step'/'time' labels to numeric indices (e.g., parse 'step_10' → 10).
- Sort the x-axis strictly in ascending numeric order; set an integer tick locator and verify ordering after aggregation.

Single-step policy:
- If there is only one unique x value (step/time) after aggregation, do NOT use a line plot. Use a bar chart or a single-marker scatter, and annotate that only one step is available.

Review-compliance checklist:
- Data checks: ensure non_empty_data; prefer loaded_real_data from a resolved file path; parse step/time to integers; validate value ranges (e.g., [0,1] for normalized metrics).
- Visual checks: ensure non_blank_image (plot at least one series); include axis labels and a clear title; provide sufficient ticks; include a legend when multiple groups OR add a short annotation when single series.
- Always create 'fig, ax = plt.subplots(figsize=(12, 6))' and track a 'plotted_any' flag. If no series can be plotted, add a thin gray fallback line and annotate 'No data' to avoid blank images.
- Add a small footnote via 'plt.figtext' indicating 'Source: <filename> · n=<rows_after_aggregation>' when real data is used.
""".strip()
        )

        self.gen_template = (
            gen_template
            or """
Given the following VisualizationSpec (a JSON-like dict string), generate a complete, runnable Python plotting script.

Requirements:
- Output raw Python (no markdown fences, no JSON).
- Include all necessary imports, including 'from matplotlib.ticker import MaxNLocator'.
- Prefer loading real data: if '_resolved_data_path' is present, load it; otherwise if 'source_reference' exists, resolve using spec.get('processed_dir') or the environment variable 'STAGE1_PROCESSED_DIR'.
- If a real dataset path resolves and the file is non-empty, you MUST use it. Do not fabricate sample data due to column mismatches; adapt the data (normalize/flatten) instead.
- Only when the resolved file is missing or empty may you create a minimal sample DataFrame.
- Do NOT introduce variables named 'spec' or 'viz_spec' in runtime code.

Top-level JSON container rule:
- After 'obj = json.load(f)', set 'records' as:
  - 'records = obj.get("data", [])' if 'obj' is a dict with 'data';
  - 'records = obj' if 'obj' is a list;
  - otherwise 'records = []'.
- Iterate over 'records' only.

Common processed schema and nested data:
- Many records contain keys like ['group_name', 'step', 'data'].
- Type branch:
  - If 'record["data"]' is a dict with 'xAxis' and 'series', flatten to long-form rows:
    ['group_name', 'step_num', category_dim, 'contribution/value'].
    Use DATA_JSON_STRUCTURE.flatten_recommendation.dimension when available; otherwise infer ('trait' for Prosocial/Proself, 'role' for Leader/Followers, else 'category').
  - If 'record["data"]' is numeric (int/float) or None, treat as scalar measurement:
    rows with ['group_name', 'step_num', 'value' (or 'contribution')].

Figure-type override policy:
- After building the aggregated DataFrame (respect 'group_by_fields' and 'aggregation.method/field' when present), compute 'unique_steps' from 'step_num'.
- If len(unique_steps) <= 1:
  - Use a categorical bar chart; x-axis is 'group_name' (or the flattened category_dim).
  - Do NOT use 'step' as x; use category labels as xticks and show values as bar heights.
  - Guard legend creation (only when >1 groups/series).
  - Optionally add value labels above bars for readability.
  - Annotate title or footnote with 'Single Step'.
- If len(unique_steps) == 2:
  - Prefer a scatter with markers; annotate each point's value; avoid lines unless explicitly justified.
- If len(unique_steps) >= 3:
  - A line plot is acceptable; sort by 'step_num' strictly ascending and set 'ax.xaxis.set_major_locator(MaxNLocator(integer=True))'.

Aggregation and ordering:
- Parse 'step' labels to integers; sort strictly ascending; verify there are no duplicates after aggregation.
- Set xticks before xticklabels to avoid formatter/locator warnings.

VisualizationSpec:
{viz_spec}
""".strip()
        )

        self.patch_template = (
            patch_template
            or '''
You are given an existing Python plotting script that failed to run or produced a poor visualization. Produce a corrected script.

Provide ONLY the full corrected Python script (no explanations, no markdown).
Make minimal changes necessary to fix the error while preserving the intended visualization.
Add imports or replace APIs if required to match installed libraries.

Constraints:
- Do NOT introduce variables named 'spec' or 'viz_spec' in runtime code.
- If a spec_file or DATA_JSON_STRUCTURE indicates a real data path and the file is non-empty, load and use it.

Data handling fixes to apply:
- Top-level container: after 'obj = json.load(f)', set 'records = obj.get("data", [])' when 'obj' is a dict; else if 'obj' is a list, 'records = obj'; do not iterate the dict directly.
- Type branch per record: if 'data' is dict with 'xAxis' and 'series', flatten into long-form rows (category_dim, value, group_name, step_num); if 'data' is numeric, treat as scalar measurement into ['group_name','step_num','value/contribution'].
- Use 'isinstance' checks to avoid attribute errors.

Figure-type override policy:
- Decide chart type AFTER aggregation. Compute 'unique_steps' from parsed 'step_num'.
- If len(unique_steps) <= 1, replace any line plotting with a categorical bar chart:
  - Use 'group_name' or the flattened category_dim for the x-axis; show bar heights as the aggregated metric.
  - Do NOT use 'step' as x in single-step scenarios.
  - Guard legend creation (only when >1 groups/series) and optionally add value labels above bars.
- If len(unique_steps) == 2, prefer a scatter with markers; annotate values.
- Use a line plot only when len(unique_steps) >= 3, with strict ascending x and 'MaxNLocator(integer=True)'.

Plotting hygiene:
- Import 'from matplotlib.ticker import MaxNLocator' and use it via 'ax.xaxis.set_major_locator(MaxNLocator(integer=True))'; do not call 'plt.MaxNLocator'.
- Set xticks before xticklabels to avoid FixedFormatter/FixedLocator warnings.

Original Script:
"""
{broken_code}
"""

Error Summary:
"""
{error}
"""

Additionally, ensure the 'step'/'time' x-axis is strictly ordered ascending by numeric value. If labels are strings (e.g., 'step_10', 'step_2'), parse digits and sort numerically before plotting, and set an integer tick locator on x.
'''.strip()
        )

    def generate_plot_code(self, viz_spec: Dict[str, Any]) -> str:
        prompt = self.gen_template.format(viz_spec=json.dumps(viz_spec, ensure_ascii=False, indent=2))
        # 追加数据结构摘要（若能解析到数据路径）
        ds_block = _build_data_structure_block_from_spec(viz_spec)
        if ds_block:
            prompt = prompt + "\n\nDATA_JSON_STRUCTURE:\n" + ds_block
        raw = self.llm.chat(user_query=prompt, system_prompt=self.system_prompt)
        return _sanitize_code(raw)

    # 方法：patch_plot_code（新增可选 spec 入参，并在 Prompt 追加数据结构）
    def patch_plot_code(
        self,
        broken_code: str,
        error: str,
        viz_spec: Optional[Dict[str, Any]] = None,
        spec_file: Optional[str] = None,
    ) -> str:
        base_prompt = self.patch_template.format(broken_code=broken_code, error=error)
        ds_block = ""
        try:
            spec: Optional[Dict[str, Any]] = None
            if viz_spec:
                spec = viz_spec
            elif spec_file:
                p = Path(spec_file)
                if p.exists():
                    with p.open("r", encoding="utf-8") as f:
                        spec = json.load(f)
            if spec:
                ds_block = _build_data_structure_block_from_spec(spec)
        except Exception:
            ds_block = ""
        prompt = base_prompt if not ds_block else base_prompt + "\n\nDATA_JSON_STRUCTURE:\n" + ds_block
        raw = self.llm.chat(user_query=prompt, system_prompt=self.system_prompt)
        return _sanitize_code(raw)


# Module-level convenience functions expected by the caller
_default_agent: Optional[PlotCodeAgent] = None


def _get_default_agent() -> PlotCodeAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = PlotCodeAgent()
    return _default_agent


def gen_plot_code(viz_spec: Dict[str, Any]) -> str:
    """Generate a Python plotting script string from a VisualizationSpec dict."""
    agent = _get_default_agent()
    return agent.generate_plot_code(viz_spec)


def patch_code(
    broken_code: str,
    error: str,
    viz_spec: Optional[Dict[str, Any]] = None,
    spec_file: Optional[str] = None,
) -> str:
    agent = _get_default_agent()
    return agent.patch_plot_code(broken_code, error, viz_spec=viz_spec, spec_file=spec_file)


def gen_plot_code_with_review(
    viz_spec: Dict[str, Any],
    suggestions: Optional[list[str]] = None,
    review_file: Optional[str] = None,
    project_name: Optional[str] = None,
    fig_index: Optional[int] = None,
) -> str:
    """
    评审增强版代码生成：将 review JSON 中的 suggestions 注入提示，重新生成绘图脚本。
    优先使用 `suggestions` 参数；否则尝试从 `review_file` 或
    `projects/{project_name}/analysis/figures/fig{fig_index}.review.json` 读取。
    若未获取到建议则回退到 `generate_plot_code`。
    """
    loaded_suggestions: list[str] = []
    try:
        if suggestions:
            loaded_suggestions = list(suggestions)
        else:
            review_path: Optional[Path] = None
            if review_file:
                review_path = Path(review_file)
            elif project_name and fig_index:
                from researcher.analysis.common import resolve_project_paths
                review_path = Path(resolve_project_paths(project_name)["figures_dir"]) / f"fig{fig_index}.review.json"
            if review_path and review_path.exists():
                with review_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                try:
                    loaded_suggestions = data.get("review", {}).get("suggestions", []) or []
                except Exception:
                    loaded_suggestions = []
    except Exception:
        loaded_suggestions = []

    if not loaded_suggestions:
        # 无建议则使用原始生成
        return self.generate_plot_code(viz_spec)

    # 在原始模板的末尾追加评审建议与明确的再生成指令
    prompt_base = self.gen_template.format(
        viz_spec=json.dumps(viz_spec, ensure_ascii=False, indent=2)
    )
    review_block = {
        "review_suggestions": loaded_suggestions,
        "instruction": (
            "Regenerate the plotting code incorporating these suggestions while "
            "preserving data semantics, aggregation rules, labeling policy, and visualization intent. "
            "Do not output markdown or JSON; output Python code only."
        ),
    }
    prompt = prompt_base + "\n\nReviewer Feedback:\n" + json.dumps(review_block, ensure_ascii=False, indent=2)
    raw = self.llm.chat(user_query=prompt, system_prompt=self.system_prompt)
    return _sanitize_code(raw)


__all__ = [
    "PlotCodeAgent",
    "gen_plot_code",
    "patch_code",
    "gen_plot_code_with_review",
]



# --------------------------- CLI and Utilities ---------------------------
DEMO_SPECS: Dict[str, Dict[str, Any]] = {
    "num_regions_openness_flow": {
        "id": "num_regions_openness_flow",
        "title": "Number of Cultural Regions by Openness and Information Flow",
        "data_source_category": "processed",
        "source_reference": "Number_of_Cultural_Regions_all_groups.json",
        "group_by_fields": ["openness", "interaction_range"],
        "aggregation": {"method": "count", "field": "region_count"},
        "suggested_visualization_type": "line",
        "why_this_figure": "Directly shows how varying openness and information flow parameters affects cultural region formation, addressing the research question's core.",
    },
    "polarization_openness_flow": {
        "id": "polarization_openness_flow",
        "title": "Global Polarization Index by Openness and Information Flow",
        "data_source_category": "processed",
        "source_reference": "Global_Polarization_Index_all_groups.json",
        "group_by_fields": ["openness", "interaction_range"],
        "aggregation": {"method": "mean", "field": "polarization_value"},
        "suggested_visualization_type": "line",
        "why_this_figure": "Quantifies fragmentation levels (distinct regions) normalized by population, revealing how openness and information flow jointly shape polarization.",
    },
    "region_size_distribution": {
        "id": "region_size_distribution",
        "title": "Region Size Distribution by Openness and Information Flow",
        "data_source_category": "processed",
        "source_reference": "Region_Size_Distribution_all_groups.json",
        "group_by_fields": ["openness", "interaction_range"],
        "aggregation": {"method": "distribution", "field": "region_size"},
        "suggested_visualization_type": "bar",
        "why_this_figure": "Shows how openness and information flow affect regional homogenization (large regions) vs fragmentation (small regions), complementing region count metrics.",
    },
}


def _load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def _resolve_viz_spec(
    *, spec_json: Optional[str], spec_file: Optional[str], demo_id: Optional[str]
) -> Dict[str, Any]:
    if spec_json:
        return json.loads(spec_json)
    if spec_file:
        return _load_json_file(Path(spec_file))
    if demo_id:
        if demo_id not in DEMO_SPECS:
            raise ValueError(f"Unknown demo_id: {demo_id}. Available: {list(DEMO_SPECS)}")
        return DEMO_SPECS[demo_id]
    raise ValueError("One of --spec-json, --spec-file, or --demo-id is required")


def _build_agent_from_args(args: argparse.Namespace) -> PlotCodeAgent:
    return PlotCodeAgent(config_name=args.config_name, config_path=args.config_path)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="PlotCodeAgent CLI")
    parser.add_argument(
        "--config-name",
        default="default-chat",
        help="Model config name defined in config/model_config.json",
    )
    parser.add_argument(
        "--config-path",
        default="config/model_config.json",
        help="Path to model configuration JSON",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # gen subcommand
    gen_p = subparsers.add_parser("gen", help="Generate plotting code from a VisualizationSpec")
    gen_p.add_argument("--spec-json", help="VisualizationSpec as JSON string")
    gen_p.add_argument("--spec-file", help="Path to VisualizationSpec JSON file")
    gen_p.add_argument("--demo-id", help=f"One of: {list(DEMO_SPECS.keys())}")
    gen_p.add_argument("--out", help="Path to save generated .py code; prints to stdout if omitted")

    # patch subcommand
    patch_p = subparsers.add_parser("patch", help="Patch a broken plotting script using an error summary")
    patch_p.add_argument("--broken-file", required=True, help="Path to the broken .py script")
    patch_p.add_argument("--error-text", help="Inline error summary text")
    patch_p.add_argument("--error-file", help="Path to a file containing the error summary")
    patch_p.add_argument("--out", help="Path to save corrected .py code; prints to stdout if omitted")

    # test subcommand
    test_p = subparsers.add_parser("test", help="Generate code for demo specs and save to a directory")
    test_p.add_argument(
        "--out-dir",
        default="outputs/code_agent_demos",
        help="Directory to write generated demo scripts",
    )
    test_p.add_argument(
        "--demo-ids",
        nargs="*",
        help="Subset of demo ids to run; defaults to all",
    )

    # gen-review subcommand
    genr_p = subparsers.add_parser("gen-review", help="Generate plotting code incorporating review suggestions")
    genr_p.add_argument("--spec-json", help="VisualizationSpec as JSON string")
    genr_p.add_argument("--spec-file", help="Path to VisualizationSpec JSON file")
    genr_p.add_argument("--demo-id", help=f"One of: {list(DEMO_SPECS.keys())}")
    genr_p.add_argument("--suggestions", nargs="*", help="Review suggestions list; overrides review_file")
    genr_p.add_argument("--review-file", help="Path to figX.review.json")
    genr_p.add_argument("--project-name", help="Project name under projects/{project_name}")
    genr_p.add_argument("--fig-index", type=int, help="Figure index (1..3) for review file resolution")
    genr_p.add_argument("--out", help="Path to save generated .py code; prints to stdout if omitted")

    args = parser.parse_args(argv)
    agent = _build_agent_from_args(args)

    if args.command == "gen":
        viz_spec = _resolve_viz_spec(
            spec_json=getattr(args, "spec_json", None),
            spec_file=getattr(args, "spec_file", None),
            demo_id=getattr(args, "demo_id", None),
        )
        code = agent.generate_plot_code(viz_spec)
        if args.out:
            _save_text(Path(args.out), code)
        else:
            sys.stdout.write(code)
            if not code.endswith("\n"):
                sys.stdout.write("\n")
        return 0

    if args.command == "patch":
        broken_path = Path(args.broken_file)
        with broken_path.open("r", encoding="utf-8") as f:
            broken_code = f.read()
        error_text = getattr(args, "error_text", None)
        if not error_text and getattr(args, "error_file", None):
            error_text = Path(args.error_file).read_text(encoding="utf-8")
        if not error_text:
            raise ValueError("Either --error-text or --error-file must be provided")
        fixed = agent.patch_plot_code(broken_code, error_text)
        if args.out:
            _save_text(Path(args.out), fixed)
        else:
            sys.stdout.write(fixed)
            if not fixed.endswith("\n"):
                sys.stdout.write("\n")
        return 0

    if args.command == "test":
        out_dir = Path(args.out_dir)
        demo_ids = args.demo_ids or list(DEMO_SPECS.keys())
        exit_code = 0
        for demo_id in demo_ids:
            if demo_id not in DEMO_SPECS:
                sys.stderr.write(f"Unknown demo id: {demo_id}\n")
                exit_code = 2
                continue
            spec = DEMO_SPECS[demo_id]
            try:
                code = agent.generate_plot_code(spec)
                _save_text(out_dir / f"{demo_id}.py", code)
            except Exception as exc:  # noqa: BLE001 - surface errors to user
                sys.stderr.write(f"Failed to generate for {demo_id}: {exc}\n")
                exit_code = 1
        return exit_code

    # 新增：gen-review 命令处理
    if args.command == "gen-review":
        viz_spec = _resolve_viz_spec(
            spec_json=getattr(args, "spec_json", None),
            spec_file=getattr(args, "spec_file", None),
            demo_id=getattr(args, "demo_id", None),
        )
        origin = (
            "spec_json" if getattr(args, "spec_json", None) else
            ("spec_file" if getattr(args, "spec_file", None) else (
                "demo_id" if getattr(args, "demo_id", None) else "unknown"
            ))
        )
        logger.info(
            f"[gen-review] start origin={origin} id={viz_spec.get('id')} title={viz_spec.get('title')} review_file={getattr(args, 'review_file', None)} project_name={getattr(args, 'project_name', None)} fig_index={getattr(args, 'fig_index', None)} suggestions_arg_count={len(getattr(args, 'suggestions', []) or [])} out={getattr(args, 'out', None)}"
        )
        code = agent.generate_plot_code_with_review(
            viz_spec,
            suggestions=getattr(args, "suggestions", None),
            review_file=getattr(args, "review_file", None),
            project_name=getattr(args, "project_name", None),
            fig_index=getattr(args, "fig_index", None),
        )
        if args.out:
            _save_text(Path(args.out), code)
        else:
            sys.stdout.write(code)
            if not code.endswith("\n"):
                sys.stdout.write("\n")
        return 0

    # Should not reach here
    return 1


def test_main() -> None:
    """Lightweight test runner that mimics `python -m ... code_agent test`."""
    _ = main(["test"])  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())


# 辅助函数区域（新增数据结构总结）
def _resolve_data_path_from_spec(spec: Dict[str, Any]) -> Optional[Path]:
    try:
        p = spec.get("_resolved_data_path")
        if p:
            path = Path(p)
            return path if path.exists() else None
        src = spec.get("source_reference")
        if not src:
            return None
        base = spec.get("processed_dir") or os.environ.get("STAGE1_PROCESSED_DIR")
        if base:
            path = Path(base) / src
            return path if path.exists() else None
    except Exception:
        return None
    return None


def _load_json_any(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _summarize_json_structure(obj: Any, max_records: int = 3) -> Dict[str, Any]:
    try:
        if isinstance(obj, dict):
            summary: Dict[str, Any] = {"type": "object", "keys": sorted(list(obj.keys()))}
            data = obj.get("data")
            if isinstance(data, list):
                sample_keys = []
                nested_hint = {}
                for idx, item in enumerate(data[:max_records]):
                    if isinstance(item, dict):
                        sample_keys.append(sorted(list(item.keys())))
                        # Inspect inner 'data' per record
                        inner = item.get("data")
                        if isinstance(inner, dict) and ("xAxis" in inner or "series" in inner) and not nested_hint:
                            xaxis = inner.get("xAxis", [])
                            series = inner.get("series", [])
                            nested_hint = {
                                "row_data_nested": True,
                                "inner_data_keys": sorted(list(inner.keys())),
                                "xAxis_sample": xaxis[:4],
                                "series_length": len(series),
                                "series_head": series[:4],
                            }
                    else:
                        sample_keys.append(type(item).__name__)
                summary.update({"data_type": "list", "sample_item_keys": sample_keys, "data_len": len(data)})
                if nested_hint:
                    summary.update(nested_hint)
            elif isinstance(data, dict):
                summary.update({"data_type": "object", "data_keys": sorted(list(data.keys()))})
            return summary
        if isinstance(obj, list):
            sample_keys = []
            nested_hint = {}
            for idx, item in enumerate(obj[:max_records]):
                if isinstance(item, dict):
                    sample_keys.append(sorted(list(item.keys())))
                    inner = item.get("data")
                    if isinstance(inner, dict) and ("xAxis" in inner or "series" in inner) and not nested_hint:
                        xaxis = inner.get("xAxis", [])
                        series = inner.get("series", [])
                        nested_hint = {
                            "row_data_nested": True,
                            "inner_data_keys": sorted(list(inner.keys())),
                            "xAxis_sample": xaxis[:4],
                            "series_length": len(series),
                            "series_head": series[:4],
                        }
                else:
                    sample_keys.append(type(item).__name__)
            out = {"type": "list", "length": len(obj), "sample_item_keys": sample_keys}
            if nested_hint:
                out.update(nested_hint)
            return out
        return {"type": type(obj).__name__}
    except Exception:
        return {"type": "unknown"}


def _build_data_structure_block_from_spec(spec: Dict[str, Any]) -> str:
    try:
        path = _resolve_data_path_from_spec(spec)
        if not path:
            return ""
        obj = _load_json_any(path)
        summary = _summarize_json_structure(obj)
        # Provide flatten recommendation if recognizable labels present
        flatten_hint = {}
        try:
            if isinstance(obj, dict) and isinstance(obj.get("data"), list) and obj["data"]:
                inner = obj["data"][0].get("data", {})
                labels = inner.get("xAxis", []) if isinstance(inner, dict) else []
                if labels and all(lbl in ["Prosocial", "Proself"] for lbl in labels[:2]):
                    flatten_hint = {"flatten_recommendation": {"dimension": "trait", "labels": labels[:4]}}
                elif labels and all(lbl in ["Leader", "Followers"] for lbl in labels[:2]):
                    flatten_hint = {"flatten_recommendation": {"dimension": "role", "labels": labels[:4]}}
        except Exception:
            flatten_hint = {}
        block_obj = {"data_path": str(path), "data_json_structure": summary}
        if flatten_hint:
            block_obj.update(flatten_hint)
        return json.dumps(block_obj, ensure_ascii=False, indent=2)
    except Exception:
        return ""
