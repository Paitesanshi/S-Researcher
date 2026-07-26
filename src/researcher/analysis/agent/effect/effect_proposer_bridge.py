from typing import Dict, Any, List, Set

from .effect_proposer_agent import propose_effect_candidates
from ..eda_metrics.metric_registry import MetricType


def build_available_fields(metric_type: str, rows_sample: List[Dict[str, Any]]) -> Set[str]:
    fields = set()
    if metric_type == MetricType.time_series:
        fields.update(["time", "dv"])
    else:
        fields.update(["dv"])
    ks = set()
    for r in rows_sample[:5]:
        ks.update(r.keys())
    if any(k in ks for k in ("step", "time", "t", "round")):
        fields.add("time")
    if any(k in ks for k in ("group_name", "group", "groupName")):
        fields.add("group")
    return fields


def propose_for_metrics(metric_items: List[Dict[str, Any]], raw_rows_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    out = []
    for item in metric_items:
        name = item.get("metric_name")
        mtype = item.get("type")
        rows = raw_rows_map.get(name, [])
        af = build_available_fields(mtype, rows)
        c = propose_effect_candidates(af)
        out.append({"metric_name": name, "candidates": c})
    return {"schema_version": "0.1.0", "items": out}
