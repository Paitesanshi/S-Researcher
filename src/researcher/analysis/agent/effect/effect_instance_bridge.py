from typing import Dict, Any, List, Optional

from .effect_instance_agent import extract_effect_instances


def build_instances_for_metrics(candidates_by_metric: Dict[str, Any], eda_by_metric: Dict[str, Any], llm: Optional[Any] = None) -> Dict[str, Any]:
    items = []
    for c in candidates_by_metric.get("items", []):
        name = c.get("metric_name")
        cand = c.get("candidates") or {"schema_version": "0.1.0", "items": []}
        eda_items = eda_by_metric.get("items", [])
        eda = {"schema_version": "0.1.0", "items": []}
        for e in eda_items:
            if e.get("metric_name") == name:
                eda = {"schema_version": "0.1.0", "items": [{"type": e.get("type"), "metrics": (e.get("eda") or {}).get("metrics", {})}]}
                break
        inst = extract_effect_instances(cand, eda, llm=llm)
        items.append({"metric_name": name, "instances": inst})
    return {"schema_version": "0.1.0", "items": items}
