from typing import Dict, Any, Optional, Set, List
import pandas as pd

from .effect_catalog import list_effect_types, required_fields_satisfied
from .effect_proposer_agent import propose_effect_candidates
from ..eda_metrics.quick_eda_agent import compute_quick_eda
from .effect_instance_agent import extract_effect_instances
from .effect_selector_agent import select_effects


def run_effect_discovery(task_text: str, df: pd.DataFrame, column_hints: Dict[str, Any], llm: Optional[Any] = None, min_score: Optional[float] = None) -> Dict[str, Any]:
    available_fields: Set[str] = set()
    if column_hints.get("time_col"):
        available_fields.add("time")
    if column_hints.get("group_col"):
        available_fields.add("group")
    if column_hints.get("dv_col"):
        available_fields.add("dv")
    if column_hints.get("intervention_point") is not None:
        available_fields.add("intervention_point")

    valid_types: List[str] = [t for t in list_effect_types() if required_fields_satisfied(t, available_fields)]
    candidates = propose_effect_candidates(available_fields)
    candidates["items"] = [it for it in candidates["items"] if it.get("type") in valid_types]

    eda_summary = compute_quick_eda(df, column_hints, [it["type"] for it in candidates["items"]])
    instances = extract_effect_instances(candidates, eda_summary, llm=llm)
    selection = select_effects(candidates, eda_summary, llm=llm, instances=instances, min_score=min_score)

    return {
        "effect_candidates": candidates,
        "effect_eda_summary": eda_summary,
        "effect_instances": instances,
        "selected_effects": selection,
    }
