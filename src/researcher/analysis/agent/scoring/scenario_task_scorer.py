from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from researcher.analysis.common import resolve_project_paths

def _project_paths(project_name: str) -> Dict[str, str]:
    base = Path(resolve_project_paths(project_name)["project_dir"])
    return {
        "analysis_dir": str(base / "analysis"),
        "effect_dir": str(base / "analysis" / "effect"),
        "semantic_summary": str(base / "analysis" / "research_semantic_summary.json"),
        "context_task_score": str(base / "analysis" / "effect" / "context_task_score.json"),
    }

def _read_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _extract_scene_summary(project_name: str) -> str:
    paths = _project_paths(project_name)
    obj = _read_json(paths["semantic_summary"]).copy()
    parts: List[str] = []
    try:
        ex = obj.get("extracted") or {}
        scene_name = ex.get("scene_name") or ""
        indep = ex.get("independent_variable") or ""
        dep = ex.get("dependent_variable") or ""
        levels = ex.get("contribution_levels") or []
        mech = ["Voluntary", "Forced"]
        lv_text = ",".join([str(x) for x in levels]) if isinstance(levels, list) else ""
        base = (
            f"Scenario: {scene_name}; independent variable: {indep} "
            f"(mechanisms: {','.join(mech)}; levels: {lv_text}); "
            f"dependent variable: {dep}."
        )
        parts.append(base)
        txt = (obj.get("text") or {}).get("scenario_description") or ""
        if isinstance(txt, str) and txt.strip():
            s = txt.strip().replace("\n", " ")
            s = s[:200]
            parts.append(f"Context: {s}")
    except Exception:
        pass
    out = " ".join([p for p in parts if p])
    return out or (
        "Assess relevance to follower cooperation in a public-goods leadership "
        "scenario, given the decision mechanism and contribution level."
    )

def _brief_metrics(metrics: Dict[str, Any]) -> str:
    items = []
    for k, v in list(metrics.items())[:6]:
        items.append(f"{k}={v}")
    return ", ".join(items)

def _parse_fields_from_reason(reason: Optional[str]) -> List[str]:
    if not isinstance(reason, str):
        return []
    s = reason.strip()
    idx = s.find("has fields ")
    if idx == -1:
        return []
    tail = s[idx + len("has fields "):]
    end = tail.find(";")
    if end != -1:
        tail = tail[:end]
    fields = [x.strip() for x in tail.split(",") if x.strip()]
    return fields

def _required_fields(effect_type: str) -> List[str]:
    try:
        from .effect.effect_catalog import get_effect_type
    except Exception:
        from src.researcher.analysis.agent.effect.effect_catalog import get_effect_type
    return list(get_effect_type(effect_type).get("required_fields", []))

def _cap_limit(effect_type: str, fields: List[str]) -> float:
    req = set(_required_fields(effect_type))
    have = set(fields)
    cap = 1.0
    if not req.issubset(have):
        cap = min(cap, 0.2)
    if effect_type in {"global_trend", "distribution_shift"} and "time" not in have:
        cap = min(cap, 0.4)
    if effect_type in {"group_level_diff", "group_trend_diff", "intervention_effect"} and "group" not in have:
        cap = min(cap, 0.4)
    return float(cap)

def _build_prompt(effect_type: str, metrics: Dict[str, Any], scene_summary: str, reason: Optional[str]) -> str:
    brief = _brief_metrics(metrics)
    return (
        "Score the task relevance of this effect type from 0 to 1 using the "
        "scenario and EDA evidence. Return only the number.\n"
        f"Scenario: {scene_summary}\n"
        f"Effect type: {effect_type}\n"
        f"Metrics: {brief}\n"
        f"Candidate rationale: {(reason or '').strip()}"
    )

def _build_llm(enable: bool, config_name: Optional[str], config_path: Optional[str]):
    if not enable:
        return lambda prompt: "0.7"
    try:
        from ..llm.agent_client import SimpleChatLLM
    except Exception:
        from src.researcher.analysis.agent.agent_client import SimpleChatLLM
    try:
        name = (config_name or "claude-sonnet-4-5-20250929").strip()
        if name == "openai-gpt4o":
            name = "gpt-4o"
        path = config_path or "config/model_config.json"
        cli = SimpleChatLLM(config_name=name, config_path=path)
        if getattr(cli, "client", None) is None:
            return lambda prompt: "0.7"
        return lambda prompt: cli.chat(user_query=prompt, system_prompt="Return ONLY a number between 0 and 1", temperature=0.3)
    except Exception:
        return lambda prompt: "0.7"

def score_from_result(project_name: str, result: Dict[str, Any], llm_enable: bool = False, llm_name: Optional[str] = None, llm_path: Optional[str] = None) -> Dict[str, Any]:
    paths = _project_paths(project_name)
    Path(paths["effect_dir"]).absolute().mkdir(parents=True, exist_ok=True)
    scene_summary = _extract_scene_summary(project_name)
    llm = _build_llm(llm_enable, llm_name, llm_path)
    type_best: Dict[str, Dict[str, Any]] = {}
    metrics_items = result.get("metrics", [])
    for m in metrics_items:
        eda_metrics = ((m.get("eda") or {}).get("metrics") or {})
        cand = (m.get("candidates") or {}).get("items", [])
        for c in cand:
            et = c.get("type")
            reason = c.get("reason")
            fields = _parse_fields_from_reason(reason)
            cap = _cap_limit(et, fields)
            prompt = _build_prompt(et, eda_metrics, scene_summary, reason)
            try:
                raw = llm(prompt)
                s = str(raw).strip()
                import re
                mnum = re.search(r"([0-9]*\.?[0-9]+)", s)
                val = float(mnum.group(1)) if mnum else 0.0
            except Exception:
                val = 0.7
            val = max(0.0, min(1.0, val))
            val = min(val, cap)
            rec = {
                "type": et,
                "task_relevance": round(float(val), 3),
                "llm_reason": (reason or "")[:200],
                "prompt_preview": prompt[:400],
            }
            prev = type_best.get(et)
            if not prev or float(rec["task_relevance"]) > float(prev.get("task_relevance", 0.0)):
                type_best[et] = rec
    items = list(type_best.values())
    out = {
        "schema_version": "0.1.0",
        "project_name": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "llm_config": {
            "enable": bool(llm_enable),
            "name": llm_name or None,
            "path": llm_path or None,
        },
        "items": items,
    }
    Path(paths["context_task_score"]).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    score_map = {it["type"]: float(it["task_relevance"]) for it in items}
    return {"audit_path": paths["context_task_score"], "items": items, "score_map": score_map}
