from typing import Dict, Any, List


EFFECT_CATALOG: Dict[str, Dict[str, Any]] = {
    "global_trend": {
        "id": "global_trend",
        "family": "trend",
        "required_fields": ["time", "dv"],
        "default_methods": ["trend_regression"],
        "viz_patterns": ["time_series_single"],
        "cost_score": 0.3,
    },
    "group_level_diff": {
        "id": "group_level_diff",
        "family": "group_time",
        "required_fields": ["group", "dv"],
        "default_methods": ["two_way_anova"],
        "viz_patterns": ["time_series_grouped"],
        "cost_score": 0.2,
    },
    "group_trend_diff": {
        "id": "group_trend_diff",
        "family": "group_time",
        "required_fields": ["time", "group", "dv"],
        "default_methods": ["regression_interaction", "mixed_effects"],
        "viz_patterns": ["time_series_grouped"],
        "cost_score": 0.6,
    },
    "intervention_effect": {
        "id": "intervention_effect",
        "family": "intervention",
        "required_fields": ["time", "group", "dv", "intervention_point"],
        "default_methods": ["difference_in_differences"],
        "viz_patterns": ["pre_post_by_group"],
        "cost_score": 0.5,
    },
    "distribution_shift": {
        "id": "distribution_shift",
        "family": "distribution",
        "required_fields": ["time", "dv"],
        "default_methods": ["distribution_distance"],
        "viz_patterns": ["distribution_over_time"],
        "cost_score": 0.4,
    },
}


def list_effect_types() -> List[str]:
    return list(EFFECT_CATALOG.keys())


def get_effect_type(effect_id: str) -> Dict[str, Any]:
    return EFFECT_CATALOG.get(effect_id, {})


def required_fields_satisfied(effect_id: str, available_fields: set) -> bool:
    item = EFFECT_CATALOG.get(effect_id)
    if not item:
        return False
    req = set(item.get("required_fields", []))
    return req.issubset(available_fields)


def validate_catalog() -> Dict[str, Any]:
    errors: List[str] = []
    allowed_fields = {"time", "group", "dv", "intervention_point"}
    ids = set()
    for k, v in EFFECT_CATALOG.items():
        if v.get("id") != k:
            errors.append(f"id_mismatch:{k}")
        if k in ids:
            errors.append(f"duplicate_id:{k}")
        ids.add(k)
        for key in ["family", "required_fields", "default_methods", "viz_patterns", "cost_score"]:
            if key not in v:
                errors.append(f"missing_key:{k}:{key}")
        rf = v.get("required_fields", [])
        if not set(rf).issubset(allowed_fields):
            errors.append(f"invalid_required_fields:{k}")
        cs = v.get("cost_score")
        if not isinstance(cs, (int, float)) or cs < 0.0 or cs > 1.0:
            errors.append(f"invalid_cost_score:{k}")
    return {"ok": len(errors) == 0, "errors": errors}
