from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import sys

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()


def _log(level: str, msg: str) -> None:
    lvl = (level or "INFO").upper()
    if lvl == "INFO":
        logger.info(f"stage2-effect - {msg}")
    elif lvl in ("WARN", "WARNING"):
        logger.warning(f"stage2-effect - {msg}")
    elif lvl == "ERROR":
        logger.error(f"stage2-effect - {msg}")
    else:
        logger.debug(f"stage2-effect - {msg}")


def _dummy_llm(x: Any) -> str:
    return "0.7"


def stage2_effect_run(project_name: str, min_score: Optional[float] = None, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Use common resolution
    paths = resolve_project_paths(project_name)
    # We specifically need effect dir as outputs_dir for this module
    paths["outputs_dir"] = paths["effect_dir"]
    
    _log("INFO", f"run_effect_discovery_v2(project_name={project_name})")

    result: Dict[str, Any] = {}
    try:
        try:
            from researcher.analysis.agent.effect.effect_project_runner_v2 import run_effect_discovery_v2
        except ImportError:
            from src.researcher.analysis.agent.effect.effect_project_runner_v2 import run_effect_discovery_v2
            
        result = run_effect_discovery_v2(
            project_name=project_name,
            llm=_dummy_llm,
            min_score=min_score,
        )
    except Exception as e:
        _log("ERROR", f"effect_discovery_v2 failed: {e}")
        out_dir = Path(paths["outputs_dir"]).absolute()
        out_path = out_dir / "stage2_effect.json"
        if out_path.exists():
            try:
                meta = json.loads(out_path.read_text(encoding="utf-8"))
                result = meta.get("result", {})
            except Exception:
                result = {"metrics": []}
        else:
            result = {"metrics": []}

    try:
        use_scorer = isinstance(cfg, dict) and bool(cfg.get("use_scenario_scorer", False))
    except Exception:
        use_scorer = False

    if use_scorer:
        try:
            try:
                from researcher.analysis.agent.scenario_task_scorer import score_from_result as _score_from_result
            except ImportError:
                from src.researcher.analysis.agent.scenario_task_scorer import score_from_result as _score_from_result
                
            llm_enable = bool((cfg or {}).get("llm_enable", False))
            llm_name = (cfg or {}).get("llm_name")
            llm_path = (cfg or {}).get("llm_path")
            audit = _score_from_result(project_name, result, llm_enable=llm_enable, llm_name=llm_name, llm_path=llm_path)
            score_map = audit.get("score_map", {})
            for m in result.get("metrics", []):
                cand = (m.get("candidates") or {}).get("items", [])
                for c in cand:
                    et = c.get("type")
                    if et in score_map:
                        c["task_relevance"] = round(float(score_map[et]), 3)
            _log("INFO", f"scenario_scorer applied, audit={audit.get('audit_path')}")
        except Exception as e:
            _log("ERROR", f"scenario_scorer failed: {e}")

    out_dir = Path(paths["outputs_dir"]).absolute()
    out_path = out_dir / "stage2_effect.json"
    summary_path = out_dir / "stage2_effect_summary.json"
    spec_path = out_dir / "effect_scoring_spec.json"

    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[str] = []
    try:
        try:
            from researcher.analysis.agent.effect.effect_selector_bridge import build_selection_for_metrics
        except ImportError:
            from src.researcher.analysis.agent.effect.effect_selector_bridge import build_selection_for_metrics
            
        items = result.get("metrics", [])
        candidates_by_metric = {
            "schema_version": "0.1.0",
            "items": [
                {"metric_name": m.get("metric_name"), "candidates": m.get("candidates")}
                for m in items
            ],
        }
        eda_by_metric = {
            "schema_version": "0.1.0",
            "items": [
                {"metric_name": m.get("metric_name"), "type": m.get("type"), "eda": m.get("eda")}
                for m in items
            ],
        }
        instances_by_metric = {
            "schema_version": "0.1.0",
            "items": [
                {"metric_name": m.get("metric_name"), "instances": m.get("instances")}
                for m in items
            ],
        }
        top_k = None
        if isinstance(cfg, dict):
            tk = cfg.get("top_k")
            if isinstance(tk, int) and tk > 0:
                top_k = tk
        sel = build_selection_for_metrics(
            candidates_by_metric,
            eda_by_metric,
            instances_by_metric,
            llm=_dummy_llm,
            min_score=min_score,
            top_k=top_k,
        )
        sel_map = {s.get("metric_name"): s.get("selection") for s in sel.get("items", [])}
        for m in items:
            m_name = m.get("metric_name")
            m["selection"] = sel_map.get(m_name, {"schema_version": "0.1.0", "items": []})
    except Exception:
        pass

    try:
        meta = {
            "project_name": project_name,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "0.1.0",
            "result": result,
        }
        out_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(str(out_path))
    except Exception as e:
        _log("ERROR", f"write stage2_effect.json failed: {e}")

    try:
        items = result.get("metrics", [])
        flat_selection = []
        for m in items:
            sel = (m.get("selection") or {}).get("items", [])
            for it in sel:
                flat_selection.append({
                    "metric_name": m.get("metric_name"),
                    "type": it.get("type"),
                    "score": it.get("score"),
                    "rule_score": it.get("rule_score"),
                    "llm_score": it.get("llm_score"),
                    "task_relevance": it.get("task_relevance"),
                    "data_salience": it.get("data_salience"),
                    "cost_score": it.get("cost_score"),
                })
        summary_obj = {
            "project_name": project_name,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(flat_selection),
            "selection": flat_selection,
        }
        summary_path.write_text(json.dumps(summary_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(str(summary_path))
    except Exception:
        pass

    try:
        spec = {
            "schema_version": "0.1.0",
            "final_score": "rule_score if llm_score is None else clip(0.5*rule_score+0.5*llm_score,0,1)",
            "rule_score": "clip(0.6*task_relevance+0.4*data_salience-0.15*cost_score,0,1)",
            "data_salience": {
                "global_trend": {
                    "metrics": ["slope", "r2"],
                    "formula": "clip(0.5*tanh(|slope|)+0.5*r2,0,1)",
                },
                "group_level_diff": {
                    "metrics": ["cohen_d_top2", "mean_diff_top2"],
                    "formula": "clip(0.6*tanh(|cohen_d_top2|)+0.4*tanh(|mean_diff_top2|),0,1)",
                },
                "group_trend_diff": {
                    "metrics": ["slope_diff_max"],
                    "formula": "clip(tanh(|slope_diff_max|),0,1)",
                },
                "intervention_effect": {
                    "metrics": ["did_estimate_top2", "pre_mean", "post_mean"],
                    "formula": "clip(0.6*tanh(|did_estimate_top2|)+0.4*tanh(|post_mean-pre_mean|),0,1)",
                },
                "distribution_shift": {
                    "metrics": ["mean_shift_q25", "std_ratio_q25", "iqr_ratio_q25"],
                    "formula": "clip(0.5*tanh(|mean_shift_q25|)+0.5*tanh(|log(std_ratio_q25 or iqr_ratio_q25)|),0,1)",
                },
            },
            "cost_score": {
                "global_trend": 0.3,
                "group_level_diff": 0.2,
                "group_trend_diff": 0.6,
                "intervention_effect": 0.5,
                "distribution_shift": 0.4,
            },
        }
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(str(spec_path))
    except Exception:
        pass

    _log("INFO", f"written_files: {written}")
    return {"status": "ok", "project_name": project_name, "paths": paths, "written_files": written}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stage2 Effect Analysis (discover + persist)")
    parser.add_argument("--project-name", required=True, help="Project name under projects/{name}")
    parser.add_argument("--min-score", type=float, default=None, help="Min score filter for selected effects")
    parser.add_argument("--enable-llm", action="store_true", help="Enable real LLM scoring via agent_client")
    parser.add_argument("--llm-config-name", type=str, default=None, help="LLM config name (e.g., openai-gpt4o/sonnet)")
    parser.add_argument("--llm-config-path", type=str, default=None, help="LLM config JSON path")
    parser.add_argument("--top-k", type=int, default=None, help="Select top K effects by score per metric")
    parser.add_argument("--use-scenario-scorer", action="store_true", help="Use scenario-based LLM scorer for task_relevance")
    args = parser.parse_args(argv)

    llm_enable = bool(getattr(args, "enable_llm", False))
    llm_name = getattr(args, "llm_config_name", None)
    llm_path = getattr(args, "llm_config_path", None)
    
    try:
        from researcher.analysis.agent.llm_adapter import build_llm
    except ImportError:
        from src.researcher.analysis.agent.llm_adapter import build_llm
        
    llm = build_llm(llm_enable, llm_name, llm_path)
    global _dummy_llm
    _dummy_llm = llm
    
    cfg = {
        "top_k": getattr(args, "top_k", None),
        "use_scenario_scorer": bool(getattr(args, "use_scenario_scorer", False)),
        "llm_enable": llm_enable,
        "llm_name": llm_name,
        "llm_path": llm_path,
    }
    result = stage2_effect_run(args.project_name, min_score=args.min_score, cfg=cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
