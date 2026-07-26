from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List

def _read_json(p: Path) -> Dict[str, Any]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}

def _norm_text(s: Optional[str]) -> str:
    if not isinstance(s, str):
        return ""
    return "\n".join([ln.strip() for ln in s.strip().splitlines()])

def _extract_section(text: str, start_key: str, stop_keys: List[str]) -> str:
    if not text:
        return ""
    idx = text.find(start_key)
    if idx < 0:
        return ""
    sub = text[idx + len(start_key):]
    stop_idx = len(sub)
    for k in stop_keys:
        j = sub.find(k)
        if j >= 0:
            stop_idx = min(stop_idx, j)
    return sub[:stop_idx].strip()

def _lines_nonempty(s: str) -> List[str]:
    return [ln.strip() for ln in s.splitlines() if ln.strip()]


def _extract_group_types(experiment_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract rich group type mapping from experiment_config.

    Returns a dict mapping group_name -> {
        "type": "control" | "treatment" | "replicate" | "observation",
        "replicate_of": base_group_name (only for replicates),
        "all_runs": [list of all run names including self and replicates] (only for base groups),
        "description": group description if available
    }
    """
    group_types: Dict[str, Dict[str, Any]] = {}
    exp_groups = experiment_config.get("experimental_groups", {})
    replication_settings = exp_groups.get("replication_settings", {})
    num_replicates = replication_settings.get("num_replicates", 1)

    # Helper to build all_runs list for a base group
    def _build_all_runs(base_name: str) -> List[str]:
        runs = [base_name]
        if num_replicates > 1:
            for rep_idx in range(1, num_replicates):
                runs.append(f"{base_name}_rep_{rep_idx}")
        return runs

    # Control group
    control = exp_groups.get("control_group", {})
    if control and control.get("name"):
        base_name = control["name"]
        group_types[base_name] = {
            "type": "control",
            "all_runs": _build_all_runs(base_name),
            "description": control.get("description", ""),
        }
        # Add replicates for control
        if num_replicates > 1:
            for rep_idx in range(1, num_replicates):
                rep_name = f"{base_name}_rep_{rep_idx}"
                group_types[rep_name] = {
                    "type": "replicate",
                    "replicate_of": base_name,
                    "replicate_index": rep_idx,
                }

    # Treatment groups
    for treatment in exp_groups.get("treatment_groups", []):
        if treatment.get("name"):
            base_name = treatment["name"]
            group_types[base_name] = {
                "type": "treatment",
                "all_runs": _build_all_runs(base_name),
                "description": treatment.get("description", ""),
                "parameters": treatment.get("parameters", {}),
            }
            # Add replicates for this treatment
            if num_replicates > 1:
                for rep_idx in range(1, num_replicates):
                    rep_name = f"{base_name}_rep_{rep_idx}"
                    group_types[rep_name] = {
                        "type": "replicate",
                        "replicate_of": base_name,
                        "replicate_index": rep_idx,
                    }

    # Observation runs (for inductive paradigm)
    obs = exp_groups.get("observation_runs", {})
    if obs and obs.get("name"):
        base_name = obs["name"]
        group_types[base_name] = {
            "type": "observation",
            "all_runs": _build_all_runs(base_name),
            "description": obs.get("description", ""),
        }
        # Add replicates for observation
        if num_replicates > 1:
            for rep_idx in range(1, num_replicates):
                rep_name = f"{base_name}_rep_{rep_idx}"
                group_types[rep_name] = {
                    "type": "replicate",
                    "replicate_of": base_name,
                    "replicate_index": rep_idx,
                }

    # Legacy manually defined replicates
    for replicate in exp_groups.get("replicates", []):
        if replicate.get("name"):
            rep_name = replicate["name"]
            # Try to infer base group from naming pattern
            base_name = replicate.get("replicate_of", "")
            group_types[rep_name] = {
                "type": "replicate",
                "replicate_of": base_name,
            }

    return group_types


def _extract_group_types_simple(experiment_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract simple group type mapping (legacy compatibility).
    Returns dict mapping group_name -> type_string.
    """
    rich = _extract_group_types(experiment_config)
    return {name: info["type"] for name, info in rich.items()}

def _get_project_root() -> Path:
    """Get project root dynamically."""
    # This file is at src/researcher/analysis/context/semantic/research_semantic_summary.py
    # Root is 5 levels up
    return Path(__file__).resolve().parents[5]


def build_summary(project_name: str) -> Dict[str, Any]:
    from researcher.analysis.common import resolve_project_paths

    base = Path(resolve_project_paths(project_name)["project_dir"])
    wf = _read_json(base / "workflow_state.json")
    bs_dir = base / "base_scenario"
    exp_dir = base / "experiment_design"
    scene_info = _read_json(bs_dir / "scene_info.json")
    scenario_config = _read_json(bs_dir / "scenario_config.json")
    inspiration_output = _read_json(bs_dir / "inspiration_output.json")
    odd_protocol = _read_json(bs_dir / "odd_protocol.json")
    # Load experiment design files
    experiment_config = _read_json(exp_dir / "experiment_config.json")
    intervention_specs = _read_json(exp_dir / "intervention_specifications.json")

    scenario_description = _norm_text(wf.get("scenario_description"))
    research_topic = _norm_text(wf.get("research_topic"))

    core = _extract_section(scenario_description or research_topic, "核心问题：", ["具体假设", "🔬", "实验设计", "\n\n"])
    hy = _extract_section(scenario_description or research_topic, "具体假设：", ["🔬", "实验设计", "\n\n"])
    hypotheses = _lines_nonempty(hy)

    sim_scn = (inspiration_output.get("scenario") or {}).get("simulation_scenario") or {}
    iv_name = sim_scn.get("Independent_variable")
    iv_range = sim_scn.get("Independent_variable_range")
    dv_name = sim_scn.get("dependent_variable")

    env_cfg_all = (scenario_config.get("environment_config") or {}).get("data") or {}
    env_cfg = env_cfg_all.get("public_goods_game") or {}
    leader_strategies = env_cfg.get("leader_strategies")
    contribution_levels = env_cfg.get("contribution_levels")
    total_rounds = env_cfg.get("total_rounds")

    scene_name = scene_info.get("scene_name")
    domain = scene_info.get("domain")
    odd_from_scene = (scene_info.get("odd_protocol") or {})
    metrics_info = []
    for m in scene_info.get("metrics") or []:
        metrics_info.append({
            "id": m.get("id"),
            "name": m.get("name"),
            "description": m.get("description"),
            "visualization_type": m.get("visualization_type"),
            "update_interval": m.get("update_interval"),
            "variables": m.get("variables"),
            "function_name": m.get("function_name"),
        })
    agent_types_info = scene_info.get("agent_types")
    portrait_info = scene_info.get("portrait")

    sim_cfg = scenario_config.get("simulation_config") or {}
    agent_cfg = (scenario_config.get("agent_config") or {})
    agent_cfg_types = (agent_cfg.get("types") or {})
    metric_cfg = (scenario_config.get("metric_config") or {})
    metric_cfg_list = []
    for m in metric_cfg.get("metrics") or []:
        metric_cfg_list.append({
            "name": m.get("name"),
            "type": m.get("type"),
            "description": m.get("description"),
        })

    summary: Dict[str, Any] = {
        "project_name": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "0.1.0",
        "sources": {
            "workflow_state": str(base / "workflow_state.json"),
            "scene_info": str(bs_dir / "scene_info.json"),
            "scenario_config": str(bs_dir / "scenario_config.json"),
            "inspiration_output": str(bs_dir / "inspiration_output.json"),
            "odd_protocol": str(bs_dir / "odd_protocol.json"),
            "experiment_config": str(exp_dir / "experiment_config.json"),
            "intervention_specs": str(exp_dir / "intervention_specifications.json"),
        },
        "scene": {
            "domain": domain,
            "scene_name": scene_name,
            "odd_protocol": odd_from_scene,
            "metrics": metrics_info,
            "agent_types": agent_types_info,
            "portrait": portrait_info,
        },
        "simulation": {
            "config": sim_cfg,
            "environment": env_cfg_all,
        },
        "scenario_config": {
            "simulation_config": sim_cfg,
            "environment_public_goods_game": {
                "total_rounds": total_rounds,
                "leader_strategies": leader_strategies,
                "contribution_levels": contribution_levels,
            },
            "agent_config_types": agent_cfg_types,
            "metric_config_metrics": metric_cfg_list,
        },
        "inspiration": {
            "simulation_scenario": {
                "description": sim_scn.get("description"),
                "independent_variable": iv_name,
                "independent_variable_range": iv_range,
                "dependent_variable": dv_name,
                "interactions": sim_scn.get("interactions"),
                "key_parameters": sim_scn.get("key_parameters"),
                "expected_insights": sim_scn.get("expected_insights"),
            },
            "input_data": {
                "theory": (inspiration_output.get("input_data") or {}).get("theory"),
                "observation": (inspiration_output.get("input_data") or {}).get("observation"),
                "condition": (inspiration_output.get("input_data") or {}).get("condition"),
            },
        },
        "text": {
            "scenario_description": scenario_description,
            "research_topic": research_topic,
        },
        "extracted": {
            "core_question": core,
            "hypotheses": hypotheses,
            "independent_variable": iv_name,
            "independent_variable_range": iv_range,
            "dependent_variable": dv_name,
            "leader_strategies": leader_strategies,
            "contribution_levels": contribution_levels,
            "total_rounds": total_rounds,
            "scene_name": scene_name,
            "domain": domain,
        },
        "odd_protocol_raw": odd_protocol,
        "experiment_design": {
            "experiment_info": experiment_config.get("experiment_info", {}),
            "experimental_groups": experiment_config.get("experimental_groups", {}),
            "replication_settings": experiment_config.get("experimental_groups", {}).get("replication_settings", {
                "num_replicates": 3,
                "base_seed": 10001,
                "seed_strategy": "sequential"
            }),
            "analysis_config": experiment_config.get("analysis_config", {}),
            "group_types": _extract_group_types(experiment_config),
        },
        "intervention_specs": intervention_specs,
    }

    out_dir = base / "analysis"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    out_path = out_dir / "research_semantic_summary.json"
    try:
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return summary

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Research Semantic Summary")
    parser.add_argument("--project-name", required=True)
    args = parser.parse_args(argv)
    s = build_summary(getattr(args, "project_name"))
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
