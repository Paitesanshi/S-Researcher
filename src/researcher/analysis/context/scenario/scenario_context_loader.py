from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional
from researcher.analysis.common import resolve_project_paths

def _safe_read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None

def _summarize_text(s: Optional[str]) -> str:
    if not isinstance(s, str):
        return ""
    t = " ".join(s.strip().split())
    return t[:1200]

def load(project_name: str) -> Dict[str, Any]:
    base = Path(resolve_project_paths(project_name)["project_dir"])
    wf = _safe_read_json(base / "workflow_state.json") or {}
    bs_dir = base / "base_scenario"
    scene_info = _safe_read_json(bs_dir / "scene_info.json") or {}
    scenario_config = _safe_read_json(bs_dir / "scenario_config.json") or {}
    inspiration_output = _safe_read_json(bs_dir / "inspiration_output.json") or {}
    odd_protocol = _safe_read_json(bs_dir / "odd_protocol.json") or {}

    scenario_description = _summarize_text(wf.get("scenario_description"))
    research_topic = _summarize_text(wf.get("research_topic"))

    domain = (scene_info.get("domain") or "")
    scene_name = (scene_info.get("scene_name") or "")

    overview = ((scene_info.get("odd_protocol") or {}).get("overview") or {})
    design_concepts = ((scene_info.get("odd_protocol") or {}).get("design_concepts") or {})
    details = ((scene_info.get("odd_protocol") or {}).get("details") or {})

    sim_cfg = (scenario_config.get("simulation_config") or {})
    env_cfg = ((scenario_config.get("environment_config") or {}).get("data") or {})

    insp = (inspiration_output.get("scenario") or {}).get("simulation_scenario") or {}

    ctx: Dict[str, Any] = {
        "project_name": project_name,
        "scenario_description": scenario_description,
        "research_topic": research_topic,
        "scene": {
            "domain": domain,
            "scene_name": scene_name,
            "overview": overview,
            "design_concepts": design_concepts,
            "details": details,
        },
        "simulation": {
            "config": sim_cfg,
            "environment": env_cfg,
        },
        "inspiration": insp,
        "base_scenario_files": {
            "scene_info": str(bs_dir / "scene_info.json"),
            "scenario_config": str(bs_dir / "scenario_config.json"),
            "inspiration_output": str(bs_dir / "inspiration_output.json"),
            "odd_protocol": str(bs_dir / "odd_protocol.json"),
        },
    }

    out_dir = base / "analysis" / "effect"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    out_path = out_dir / "scenario_context_summary.json"
    try:
        out_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return ctx
