import os
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from researcher.analysis.common import resolve_project_paths

# 替换对 analyzer_agent 的依赖为本文件内联的 SimpleChatLLM 与规划逻辑
try:
    from ..llm.agent_client import SimpleChatLLM
except Exception:
    try:
        from researcher.analysis.agent.llm.agent_client import SimpleChatLLM  # type: ignore
    except Exception:
        try:
            from src.researcher.analysis.agent.agent_client import SimpleChatLLM  # type: ignore
        except Exception:
            SimpleChatLLM = None  # type: ignore


class _DummyLLM:
    def chat(self, user_query: str, system_prompt: Optional[str] = None) -> str:
        try:
            start = user_query.find("{")
            end = user_query.rfind("}")
            prompt_json = user_query[start : end + 1] if start != -1 and end != -1 else "{}"
            prompt_obj = json.loads(prompt_json)
            metrics_catalog = prompt_obj.get("metrics_catalog") or []
        except Exception:
            metrics_catalog = []

        def pick_metric(i: int) -> str:
            if i < len(metrics_catalog):
                name = metrics_catalog[i].get("name") or metrics_catalog[i].get("id") or f"metric_{i+1}"
            else:
                name = f"metric_{i+1}"
            return str(name)

        specs = [
            {
                "id": "trend_1",
                "title": f"Trend over time: {pick_metric(0)}",
                "data_source_category": "processed",
                "source_reference": pick_metric(0),
                "group_by_fields": ["experiment_group"],
                "aggregation": {"method": "mean", "field": pick_metric(0), "note": "average over group"},
                "suggested_visualization_type": "line",
                "why_this_figure": "Shows how the key metric evolves over simulation steps across groups.",
            },
            {
                "id": "comparison_2",
                "title": f"Group comparison: final {pick_metric(1)}",
                "data_source_category": "processed",
                "source_reference": pick_metric(1),
                "group_by_fields": ["experiment_group"],
                "aggregation": {"method": "mean", "field": pick_metric(1), "note": "compare end state"},
                "suggested_visualization_type": "bar",
                "why_this_figure": "Compares end-state values by group to highlight differences.",
            },
            {
                "id": "matrix_3",
                "title": f"Condition matrix: {pick_metric(2)}",
                "data_source_category": "processed",
                "source_reference": pick_metric(2),
                "group_by_fields": ["openness", "interaction_range"],
                "aggregation": {"method": "mean", "field": pick_metric(2), "note": "heatmap across conditions"},
                "suggested_visualization_type": "heatmap",
                "why_this_figure": "Reveals interaction of conditions on the metric.",
            },
        ]
        return json.dumps(specs, ensure_ascii=False)


if SimpleChatLLM is None:
    SimpleChatLLM = _DummyLLM  # type: ignore

VisualizationSpec = Dict[str, Any]


def _default_paths(project_name: str) -> Dict[str, str]:
    base = Path(resolve_project_paths(project_name)["project_dir"])
    return {
        "scene_info": str(base / "base_scenario/scene_info.json"),
        "workflow_state": str(base / "workflow_state.json"),
        "processed_dir": str(base / "analysis/data/processed"),
        "outputs_dir": str(base / "analysis/figures"),
    }


def _ensure_dir(path: str) -> Path:
    p = Path(path).absolute()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _looks_like_filename(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return bool(re.match(r"^[\w.-]+\.(json|csv)$", text.strip(), flags=re.IGNORECASE))


def _resolve_source_reference(src_ref: Optional[str], processed_dir: Optional[Path]) -> Optional[Path]:
    if not src_ref:
        return None
    # 1) 绝对/相对路径直接存在
    try:
        p = Path(src_ref)
        if p.exists() and p.is_file():
            return p.absolute()
    except Exception:
        pass
    # 2) 在 processed_dir 下查找
    if processed_dir and processed_dir.exists():
        # 2.1 直接拼接
        candidate = processed_dir / src_ref
        if candidate.exists() and candidate.is_file():
            return candidate.absolute()
        # 2.2 若未带扩展，尝试 .json
        if not os.path.splitext(src_ref)[1]:
            cand_json = processed_dir / f"{src_ref}.json"
            if cand_json.exists() and cand_json.is_file():
                return cand_json.absolute()
        # 2.3 遍历匹配文件名或 stem
        try:
            for fp in sorted(processed_dir.glob("*.json")):
                if fp.name == src_ref or fp.stem == src_ref:
                    return fp.absolute()
        except Exception:
            pass
    return None


def _inject_resolution(spec: Dict[str, Any], processed_dir: Optional[Path]) -> Dict[str, Any]:
    used = dict(spec or {})
    # 注入 processed_dir，便于下游定位数据
    if processed_dir:
        used["processed_dir"] = str(processed_dir.absolute())
    # 尝试解析 source_reference → _resolved_data_path
    src_ref = used.get("source_reference")
    rp = _resolve_source_reference(src_ref, processed_dir)
    if rp is not None:
        used["_resolved_data_path"] = str(rp)
    return used


class AnalyzerAgent:
    def __init__(
        self,
        model_config_name: Optional[str] = None,
        model_config_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.model_config_name = (
            model_config_name
            or os.environ.get("ONESIM_MODEL_NAME")
            or "claude-sonnet-4-5-20250929"
        )
        self.model_config_path = (
            model_config_path
            or os.environ.get("ONESIM_MODEL_CONFIG", "config/model_config.json")
        )
        self.system_prompt = (
            system_prompt
            or (
                "You are a senior research visualization planner. "
                "Given a simulation scene specification, a research question, and available processed metrics, "
                "propose the three most insightful visualizations. Output strict JSON only."
            )
        )
        try:
            self.llm = SimpleChatLLM(
                config_name=self.model_config_name, config_path=self.model_config_path
            )
        except Exception:
            try:
                self.llm = SimpleChatLLM()  # type: ignore
            except Exception:
                self.llm = _DummyLLM()

    def propose_figures(
        self,
        scene_info: Union[str, Dict[str, Any]],
        workflow_state: Union[str, Dict[str, Any]],
        index: Union[str, Dict[str, Any], None] = None,
        max_results: int = 3,
        max_retries: int = 2,
    ) -> List[VisualizationSpec]:
        scene = self._ensure_json_object(scene_info, label="scene_info")
        workflow = self._ensure_json_object(workflow_state, label="workflow_state")
        index_summary = self._summarize_index(index)
        processed_catalog = (
            self._build_processed_catalog(index_summary.get("details", {}).get("path"))
            if index_summary.get("type") == "directory"
            else None
        )

        prompt = self._build_prompt(scene, workflow, index_summary, max_results, processed_catalog)
        last_raw: Optional[str] = None

        for attempt in range(max_retries + 1):
            raw = self.llm.chat(user_query=prompt, system_prompt=self.system_prompt)
            last_raw = raw
            specs = self._parse_llm_json(raw)
            ok, errors = self._validate_specs(specs, max_results)
            if ok:
                try:
                    self._maybe_save_specs(index_summary, specs[:max_results])
                except Exception:
                    pass
                return specs[:max_results]

            prompt = self._build_repair_prompt(
                scene=scene,
                workflow=workflow,
                index_summary=index_summary,
                max_results=max_results,
                previous_output=raw,
                errors=errors,
                attempt=attempt + 1,
            )

        raise ValueError(
            "The model did not produce a valid VisualizationSpec within "
            f"{max_retries + 1} attempts. Last raw output: {last_raw}"
        )

    def _ensure_json_object(
        self, obj: Union[str, Dict[str, Any]], label: str
    ) -> Dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str):
            if os.path.exists(obj):
                with open(obj, "r", encoding="utf-8") as f:
                    return json.load(f)
            try:
                return json.loads(obj)
            except Exception as e:
                raise ValueError(f"{label} must be dict, path, or JSON string: {e}")
        raise ValueError(f"{label} must be dict, path string, or JSON string.")

    def _summarize_index(
        self, index: Union[str, Dict[str, Any], None]
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"type": None, "details": None}
        if index is None:
            return summary

        if isinstance(index, dict):
            keys = list(index.keys())
            sample_keys = keys[:20]
            summary["type"] = "dict"
            summary["details"] = {
                "key_count": len(keys),
                "sample_keys": sample_keys,
            }
            return summary

        if isinstance(index, str):
            if os.path.isdir(index):
                try:
                    entries = sorted(os.listdir(index))
                except Exception:
                    entries = []
                files = [e for e in entries if os.path.isfile(os.path.join(index, e))]
                dirs = [e for e in entries if os.path.isdir(os.path.join(index, e))]
                summary["type"] = "directory"
                summary["details"] = {
                    "path": index,
                    "file_count": len(files),
                    "dir_count": len(dirs),
                    "sample_files": files[:30],
                    "sample_dirs": dirs[:10],
                }
                return summary

            if os.path.isfile(index):
                summary["type"] = "file"
                summary["details"] = {
                    "path": index,
                    "size_bytes": os.path.getsize(index),
                }
                return summary

        summary["type"] = type(index).__name__
        summary["details"] = str(index)[:500]
        return summary

    def _build_prompt(
        self,
        scene: Dict[str, Any],
        workflow: Dict[str, Any],
        index_summary: Dict[str, Any],
        max_results: int,
        processed_catalog: Optional[Dict[str, Any]] = None,
    ) -> str:
        research_question = workflow.get("research_question") or workflow.get(
            "research_topic"
        )
        metrics = scene.get("odd_protocol", {}).get("metrics") or scene.get("metrics")
        if not isinstance(metrics, list):
            metrics = []

        metrics_brief: List[Dict[str, Any]] = []
        for m in metrics:
            if not isinstance(m, dict):
                continue
            metrics_brief.append(
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "visualization_type": m.get("visualization_type"),
                    "function_name": m.get("function_name"),
                    "description": m.get("description"),
                    "update_interval": m.get("update_interval"),
                }
            )

        scene_overview = scene.get("odd_protocol", {}).get("overview", {})
        scene_design = scene.get("odd_protocol", {}).get("design_concepts", {})

        guide = {
            "task": "Select exactly three figures that best explain the research question using available metrics and processed outputs.",
            "output_schema": {
                "id": "string (short identifier)",
                "title": "string (clear human-friendly title)",
                "data_source_category": "one of: agent|environment|processed|simulation_summary|custom",
                "source_reference": "string (which metric/function/file/folder it relies on)",
                "group_by_fields": [
                    "array of strings (dimensions or fields used to group data)"
                ],
                "aggregation": {
                    "method": "string (e.g., count|mean|sum|proportion|entropy|region_count)",
                    "field": "string or null (field to aggregate)",
                    "note": "string (any caveats)",
                },
                "suggested_visualization_type": "string (bar|line|area|heatmap|scatter|network)",
                "why_this_figure": "string (concise rationale tied to research question)",
            },
            "constraints": [
                "Return JSON array ONLY, with exactly three items.",
                "Prefer metrics whose visualization_type aligns with the intent.",
                "If processed outputs exist, consider aggregations across experiment groups.",
                "Be specific about grouping (e.g., by experiment group, openness, interaction_range).",
                "For time-evolving metrics (e.g., simulation outputs across steps), prefer line charts with 'step' (or 'time') as the x-axis; ensure the x-axis is sorted ascending and include clear legends when multiple groups/series exist.",
                "Label axes explicitly (x='Step' or 'Time', y=metric name), enable grid lines, and use integer tick locator on the x-axis; rotate tick labels if dense.",
                "If the metric is normalized/bounded in [0,1] (e.g., indices/proportions), constrain y-limits to [0,1] with evenly spaced ticks to improve interpretability.",
                "Use a consistent color palette; when multiple groups exist, prefer placing the legend outside the plotting area to avoid occlusion (e.g., upper-right with bbox_to_anchor).",
                "Promote diversity across the three figures: avoid producing three highly similar charts; consider combining line (trend), bar (category comparison / end-state), and heatmap (interaction/condition matrix) where appropriate.",
                "Axes must be semantically meaningful (units/categories/ranges); consider log-scale y when values span orders of magnitude.",
                "When time series are long/dense, allow readable presentation via downsampling (plot every N steps) or smoothing (rolling mean) while preserving the key trends.",
                "If groups are numerous, limit to top_k salient groups (e.g., by final value or variance) and clearly state the selection logic in the spec's note.",
                "Keep annotations minimal and purposeful (e.g., mark key steps or thresholds) without cluttering the chart.",
            ],
        }

        prompt_obj = {
            "scene_overview": scene_overview,
            "scene_design_concepts": scene_design,
            "metrics_catalog": metrics_brief,
            "workflow_research_question": research_question,
            "index_summary": index_summary,
            "processed_catalog": processed_catalog,
            "instructions": guide,
            "max_results": max_results,
        }
        return (
            "Plan the three figures that best address the research question "
            "using the scenario and available metrics below. Return only a JSON "
            "array containing exactly three objects that follow the schema.\n\n"
            + json.dumps(prompt_obj, ensure_ascii=False, indent=2)
        )

    def _build_processed_catalog(self, dir_path: Optional[str]) -> Optional[Dict[str, Any]]:
        if not dir_path or not os.path.isdir(dir_path):
            return None
        datasets: List[Dict[str, Any]] = []
        try:
            entries = sorted(os.listdir(dir_path))
        except Exception:
            entries = []
        for name in entries:
            if not name.lower().endswith(".json"):
                continue
            if name.startswith("figures_analysis_combine"):
                continue
            fpath = os.path.join(dir_path, name)
            if not os.path.isfile(fpath):
                continue
            try:
                size_b = os.path.getsize(fpath)
            except Exception:
                size_b = 0
            summary: Dict[str, Any] = {
                "filename": name,
                "size_bytes": size_b,
                "category": None,
                "entry_count": None,
                "sample_fields": None,
                "nested_data_shape": None,
                "time_field": None,
                "group_field": None,
            }
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                if isinstance(obj, dict):
                    fi = obj.get("file_info") or {}
                    if isinstance(fi, dict):
                        summary["category"] = fi.get("category") or None
                    data = obj.get("data")
                else:
                    data = obj
                rows = data if isinstance(data, list) else []
                summary["entry_count"] = len(rows)
                head = rows[: min(10, len(rows))]
                fields: Dict[str, int] = {}
                for r in head:
                    if isinstance(r, dict):
                        for k in r.keys():
                            fields[k] = fields.get(k, 0) + 1
                if fields:
                    summary["sample_fields"] = sorted(list(fields.keys()))
                for tf in ("step", "time", "t", "round"):
                    if tf in fields:
                        summary["time_field"] = tf
                        break
                for gf in ("group_name", "group", "experiment_group"):
                    if gf in fields:
                        summary["group_field"] = gf
                        break
                nested_shape = None
                for r in head:
                    if isinstance(r, dict) and isinstance(r.get("data"), dict):
                        dd = r.get("data")
                        if isinstance(dd, dict) and "xAxis" in dd and "series" in dd:
                            nested_shape = "distribution(xAxis,series)"
                            break
                    if isinstance(r, dict) and (
                        isinstance(r.get("data"), (int, float, str)) or r.get("data") is None
                    ):
                        nested_shape = nested_shape or "scalar"
                summary["nested_data_shape"] = nested_shape
            except Exception:
                pass
            datasets.append(summary)
        name_map: Dict[str, str] = {}
        for ds in datasets:
            fname = ds.get("filename") or ""
            base = os.path.splitext(fname)[0]
            cat = (ds.get("category") or "").strip()
            if cat:
                name_map[cat] = fname
            name_map[base] = fname
        catalog = {
            "path": dir_path,
            "datasets": datasets,
            "name_to_file": name_map,
        }
        return catalog

    def _maybe_save_specs(self, index_summary: Dict[str, Any], specs: List[VisualizationSpec]) -> None:
        try:
            details = index_summary.get("details") if isinstance(index_summary, dict) else None
            dir_path = details.get("path") if isinstance(details, dict) else None
            if not dir_path or not os.path.isdir(dir_path):
                return
            out_cn = os.path.join(dir_path, "figures_analysis_combine.json")
            out_en = os.path.join(dir_path, "figures_analysis_combine_en.json")
            with open(out_cn, "w", encoding="utf-8") as f:
                json.dump(specs, f, ensure_ascii=False, indent=2)
            with open(out_en, "w", encoding="utf-8") as f:
                json.dump(specs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _parse_llm_json(self, raw: str) -> List[VisualizationSpec]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            pass

        array_match = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    return [d for d in data if isinstance(d, dict)]
            except Exception:
                pass

        cleaned = raw.replace("'", '"')
        cleaned = re.sub(r",\s*([\]\}])", r"\1", cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            return []
        return []

    def _validate_specs(
        self, specs: Optional[List[Dict[str, Any]]], max_results: int
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not isinstance(specs, list):
            return False, ["The output is not a JSON array."]
        if len(specs) != max_results:
            errors.append(
                f"Expected {max_results} objects but received {len(specs)}."
            )

        allowed_source = {"agent", "environment", "processed", "simulation_summary", "custom"}
        allowed_vis = {"bar", "line", "area", "heatmap", "scatter", "network"}

        for i, item in enumerate(specs):
            if not isinstance(item, dict):
                errors.append(f"Item {i} is not an object.")
                continue
            for key in [
                "id",
                "title",
                "data_source_category",
                "source_reference",
                "group_by_fields",
                "aggregation",
                "suggested_visualization_type",
                "why_this_figure",
            ]:
                if key not in item:
                    errors.append(f"Item {i} is missing field: {key}")

            if item.get("data_source_category") not in allowed_source:
                errors.append(
                    f"Item {i} has invalid data_source_category: "
                    f"{item.get('data_source_category')}"
                )
            if item.get("suggested_visualization_type") not in allowed_vis:
                errors.append(
                    f"Item {i} has invalid suggested_visualization_type: "
                    f"{item.get('suggested_visualization_type')}"
                )
            if not isinstance(item.get("group_by_fields"), list):
                errors.append(f"Item {i} group_by_fields must be an array.")
            agg = item.get("aggregation")
            if not isinstance(agg, dict) or "method" not in agg:
                errors.append(
                    f"Item {i} aggregation must be an object containing method."
                )
        return len(errors) == 0, errors

    def _build_repair_prompt(
        self,
        scene: Dict[str, Any],
        workflow: Dict[str, Any],
        index_summary: Dict[str, Any],
        max_results: int,
        previous_output: str,
        errors: List[str],
        attempt: int,
    ) -> str:
        base = self._build_prompt(scene, workflow, index_summary, max_results)
        feedback = {
            "attempt": attempt,
            "previous_output": previous_output,
            "errors": errors,
            "instruction": (
                "Correct the errors and return a JSON array that strictly follows "
                f"the schema. It must contain exactly {max_results} objects. "
                "Return JSON only, without additional text."
            ),
        }
        return base + "\n\nREPAIR_FEEDBACK:\n" + json.dumps(feedback, ensure_ascii=False, indent=2)


# 便捷函数（供 plan_figures 内部调用）
def propose_figures(
    scene_info: Union[str, Dict[str, Any]],
    workflow_state: Union[str, Dict[str, Any]],
    index: Union[str, Dict[str, Any], None] = None,
    model_config_name: Optional[str] = None,
    model_config_path: Optional[str] = None,
) -> List[VisualizationSpec]:
    agent = AnalyzerAgent(
        model_config_name=model_config_name, model_config_path=model_config_path
    )
    return agent.propose_figures(scene_info, workflow_state, index)


def _convert_analysis_item_to_spec(item: Dict[str, Any]) -> VisualizationSpec:
    """
    Converts a Stage 1.5 Analysis Item to a Stage 2 Visualization Spec.
    """
    evidence = item.get("evidence_support", {})
    hint = item.get("visualization_hint", {})
    
    spec = {
        "id": item.get("id", "unknown"),
        "title": item.get("research_question", "Analysis Figure"),
        "data_source_category": "processed",
        "source_reference": evidence.get("file_name"),
        "group_by_fields": [],
        "aggregation": {
            "method": "mean", 
            "field": evidence.get("metric_category"), 
            "note": f"Based on analysis type: {item.get('analysis_type', 'descriptive')}"
        },
        "suggested_visualization_type": hint.get("suggested_plot_type", "line"),
        "why_this_figure": f"Hypothesis: {item.get('hypothesis_ref', 'N/A')}. Reasoning: {evidence.get('reasoning', '')}",
        "_origin_analysis_item": item  # Keep trace
    }
    
    # Refine group_by based on hints or evidence
    if hint.get("x_axis") and hint.get("x_axis") != "auto":
        # Sometimes x_axis is 'step', sometimes 'group_name'
        # We put it in group_by_fields for Stage 2 to consider
        spec["group_by_fields"].append(hint["x_axis"])
        
    return spec


def plan_figures(paths: Dict[str, str],
                 cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    - 输入：包含 scene_info、workflow_state、processed_dir、outputs_dir 的路径字典
    - 输出：写入 figure_plan.json 及逐图规范 JSON 文件，并返回概要字典
    """
    scene_info = paths.get("scene_info")
    workflow_state = paths.get("workflow_state")
    processed_dir = Path(paths.get("processed_dir")) if paths.get("processed_dir") else None
    outputs_dir = _ensure_dir(paths.get("outputs_dir") or "outputs")

    # 导出环境变量，便于下游工具兼容
    try:
        if processed_dir:
            os.environ["STAGE1_PROCESSED_DIR"] = str(processed_dir.absolute())
        os.environ["STAGE1_OUTPUTS_DIR"] = str(outputs_dir.absolute())
    except Exception:
        pass

    cfg = cfg or {}
    
    specs: List[Dict[str, Any]] = []
    
    # STRATEGY 1: Use Stage 1.5 Analysis Plan if provided
    analysis_items = cfg.get("analysis_items")
    if analysis_items and isinstance(analysis_items, list):
        print(f" Processing {len(analysis_items)} analysis items...")
        for item in analysis_items:
            # Only convert items meant for visualization
            if item.get("visualization_needed") is False:
                continue
                
            try:
                spec = _convert_analysis_item_to_spec(item)
                specs.append(spec)
            except Exception as e:
                print(f"Warning: Failed to convert item {item.get('id')}: {e}")
    
    # STRATEGY 2: Fallback to LLM Proposal if no plan
    if not specs:
        config_name = cfg.get("config_name") or os.environ.get("ONESIM_MODEL_NAME", "claude-sonnet-4-5-20250929")
        config_path = cfg.get("config_path") or os.environ.get("ONESIM_MODEL_CONFIG", "config/model_config.json")
        try:
            specs = propose_figures(
                scene_info=scene_info,
                workflow_state=workflow_state,
                index=str(processed_dir) if processed_dir else None,
                model_config_name=config_name,
                model_config_path=config_path,
            )
        except Exception as e:
            specs = []
            # 兜底：至少占位 3 个对象，确保后续写文件结构稳定
            for i in range(3):
                specs.append({
                    "id": f"fallback_{i+1}",
                    "title": f"Fallback Figure {i+1}",
                    "data_source_category": "processed",
                    "source_reference": None,
                    "group_by_fields": [],
                    "aggregation": {"method": "mean", "field": None},
                    "suggested_visualization_type": "line",
                    "why_this_figure": f"Plan fallback due to error: {e}",
                })

    # 规范增强 + 落盘
    used_specs: List[Dict[str, Any]] = []
    # Limit to top 5 to avoid overwhelming Stage 2 (or keep all if explicit plan)
    # If it came from analysis_items, we probably want all of them.
    # If from LLM proposal, usually it returns 3.
    target_specs = specs if analysis_items else specs[:3]
    
    for sp in target_specs:
        used_specs.append(_inject_resolution(sp, processed_dir))

    # 写整体方案
    plan_obj = {
        "project_name": Path(workflow_state).name if isinstance(workflow_state, str) else None,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(used_specs),
        "specs": target_specs,            # 原始规范合集
        "specs_used": used_specs,         # 增强后用于绘图的合集
        "source": "stage1_5_plan" if analysis_items else "llm_proposal"
    }
    plan_path = outputs_dir / "figure_plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_obj, f, ensure_ascii=False, indent=2)

    # 写逐图规范
    written: List[str] = [str(plan_path)]
    for i, (orig, used) in enumerate(zip(target_specs, used_specs), start=1):
        p2 = outputs_dir / f"fig{i}_spec_used.json"
        try:
            with open(p2, "w", encoding="utf-8") as f:
                json.dump(used, f, ensure_ascii=False, indent=2)
            written.append(str(p2))
        except Exception:
            pass

    return {
        "outputs_dir": str(outputs_dir),
        "written_files": written,
    }


def _resolve_cli_paths(project_name: str,
                       scene_info: Optional[str],
                       workflow_state: Optional[str],
                       processed_dir: Optional[str],
                       outputs_dir: Optional[str]) -> Dict[str, str]:
    defaults = _default_paths(project_name)
    return {
        "scene_info": scene_info or defaults["scene_info"],
        "workflow_state": workflow_state or defaults["workflow_state"],
        "processed_dir": processed_dir or defaults["processed_dir"],
        "outputs_dir": outputs_dir or defaults["outputs_dir"],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate figure plans and specification files."
    )
    parser.add_argument(
        "--project-name",
        required=True,
        help="Project name, for example social_dynamics_combine",
    )
    parser.add_argument(
        "--scene-info",
        dest="scene_info",
        default=None,
        help="Optional scene_info.json override",
    )
    parser.add_argument(
        "--workflow-state",
        dest="workflow_state",
        default=None,
        help="Optional workflow_state.json override",
    )
    parser.add_argument(
        "--processed-dir",
        dest="processed_dir",
        default=None,
        help="Optional processed-data directory override",
    )
    parser.add_argument(
        "--outputs-dir",
        dest="outputs_dir",
        default=None,
        help="Output directory; defaults to projects/<name>/analysis/figures",
    )
    parser.add_argument("--config-name", dest="config_name", default=os.environ.get("ONESIM_MODEL_NAME", "claude-sonnet-4-5-20250929"))
    parser.add_argument("--config-path", dest="config_path", default=os.environ.get("ONESIM_MODEL_CONFIG", "config/model_config.json"))

    args = parser.parse_args(argv)
    paths = _resolve_cli_paths(args.project_name, args.scene_info, args.workflow_state, args.processed_dir, args.outputs_dir)
    cfg = {"config_name": args.config_name, "config_path": args.config_path}

    try:
        result = plan_figures(paths, cfg)
        # 控制台输出写入的文件列表，便于测试核对
        for fp in result.get("written_files", []):
            print(fp)
        return 0
    except Exception as e:
        print(f"[ERROR] figure_plan_agent failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
