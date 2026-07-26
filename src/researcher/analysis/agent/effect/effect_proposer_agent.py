from typing import Dict, Any, Set, List
from .effect_catalog import list_effect_types, required_fields_satisfied


def propose_effect_candidates(available_fields: Set[str]) -> Dict[str, Any]:
    types = [t for t in list_effect_types() if required_fields_satisfied(t, available_fields)]
    items: List[Dict[str, Any]] = []
    for t in types:
        score = _task_relevance(t, available_fields)
        reason = _reason(t, available_fields)
        items.append({"type": t, "task_relevance": round(score, 2), "reason": reason})
    return {"schema_version": "0.1.0", "items": items}


def _task_relevance(effect_type: str, available_fields: Set[str]) -> float:
    base = 0.3
    if "time" in available_fields:
        base += 0.2
    if "group" in available_fields and effect_type in {"group_level_diff", "group_trend_diff", "intervention_effect"}:
        base += 0.2
    score = base
    if effect_type == "distribution_shift" and "time" not in available_fields:
        score -= 0.2
    return max(0.0, min(1.0, score))


def _reason(effect_type: str, available_fields: Set[str]) -> str:
    fields_part = ",".join(sorted(list(available_fields)))
    if effect_type == "global_trend":
        return f"has fields {fields_part}; trend over time"
    if effect_type == "group_level_diff":
        return f"has fields {fields_part}; group mean difference"
    if effect_type == "group_trend_diff":
        return f"has fields {fields_part}; group-by-time trend difference"
    if effect_type == "intervention_effect":
        return f"has fields {fields_part}; pre/post intervention"
    if effect_type == "distribution_shift":
        return f"has fields {fields_part}; distribution change over time"
    return f"has fields {fields_part}"
