from typing import Dict, Any, Optional

from .effect_selector_agent import select_effects


def build_selection_for_metrics(candidates_by_metric: Dict[str, Any], eda_by_metric: Dict[str, Any], instances_by_metric: Dict[str, Any], llm: Optional[Any] = None, min_score: Optional[float] = None, top_k: Optional[int] = None) -> Dict[str, Any]:
    items = []
    eda_map = {e.get("metric_name"): e for e in eda_by_metric.get("items", [])}
    inst_map = {i.get("metric_name"): i for i in instances_by_metric.get("items", [])}
    for c in candidates_by_metric.get("items", []):
        name = c.get("metric_name")
        cand = c.get("candidates") or {"schema_version": "0.1.0", "items": []}
        e_item = eda_map.get(name)
        eda = {"schema_version": "0.1.0", "items": []}
        if e_item:
            metrics = (e_item.get("eda") or {}).get("metrics", {})
            cand_types = [it.get("type") for it in cand.get("items", [])]
            eda_items = []
            for t in cand_types:
                eda_items.append({"type": t, "metrics": metrics})
            eda = {"schema_version": "0.1.0", "items": eda_items}
        i_item = inst_map.get(name)
        inst = {"schema_version": "0.1.0", "items": []}
        if i_item:
            inst = i_item.get("instances") or inst
        sel = select_effects(cand, eda, llm=llm, instances=inst, min_score=min_score, top_k=top_k)
        items.append({"metric_name": name, "selection": sel})
    return {"schema_version": "0.1.0", "items": items}
