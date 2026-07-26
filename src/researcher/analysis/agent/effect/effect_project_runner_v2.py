from typing import Dict, Any, Optional

from ..eda_metrics.project_metric_loader import load_project_metrics
from ..eda_metrics.metric_eda_runner import run_metric_eda
from .effect_proposer_bridge import propose_for_metrics
from .effect_instance_bridge import build_instances_for_metrics
from .effect_selector_bridge import build_selection_for_metrics


def run_effect_discovery_v2(project_name: str, task_text: Optional[str] = None, llm=None, min_score: Optional[float] = None) -> Dict[str, Any]:
    reg = load_project_metrics(project_name)
    eda_summary = run_metric_eda(reg, llm=llm)
    raw_rows_map = {rec.metric_name: rec.raw_rows for rec in reg.items()}
    candidates = propose_for_metrics(eda_summary.get("items", []), raw_rows_map)
    instances = build_instances_for_metrics(candidates, eda_summary, llm=llm)
    selection = build_selection_for_metrics(candidates, eda_summary, instances, llm=llm, min_score=min_score)
    return {
        "metrics": [
            {
                "metric_name": m.get("metric_name"),
                "type": m.get("type"),
                "eda": m.get("eda"),
                "candidates": next((c.get("candidates") for c in candidates.get("items", []) if c.get("metric_name") == m.get("metric_name")), {}),
                "instances": next((i.get("instances") for i in instances.get("items", []) if i.get("metric_name") == m.get("metric_name")), {}),
                "selection": next((s.get("selection") for s in selection.get("items", []) if s.get("metric_name") == m.get("metric_name")), {}),
            }
            for m in eda_summary.get("items", [])
        ]
    }


__all__ = ["run_effect_discovery_v2"]
