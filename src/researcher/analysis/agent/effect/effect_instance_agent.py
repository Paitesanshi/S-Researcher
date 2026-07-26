from typing import Dict, Any, List, Optional


def extract_effect_instances(effect_candidates: Dict[str, Any], eda_summary: Dict[str, Any], llm: Optional[Any] = None) -> Dict[str, Any]:
    cand_items = effect_candidates.get("items", [])
    eda_map = {item.get("type"): item.get("metrics", {}) for item in eda_summary.get("items", [])}
    out_items: List[Dict[str, Any]] = []
    eid = 1
    for c in cand_items:
        et = c.get("type")
        metrics = eda_map.get(et, {})
        desc = _build_desc(et, metrics, llm)
        origin = {
            "candidate_type": et,
            "from_eda_stats": list(metrics.keys()),
            "stage": "Stage2",
        }
        item = {
            "effect_id": f"E{eid}",
            "type": et,
            "status": "exploratory",
            "description": desc,
            "origin": origin,
            "links_to_gt": {"matched_gt_effect_id": None, "match_score": None},
            "numeric_evidence": metrics,
            "visual_evidence": [],
        }
        out_items.append(item)
        eid += 1
    return {"schema_version": "0.1.0", "items": out_items}


def _build_desc(effect_type: str, metrics: Dict[str, Any], llm: Optional[Any]) -> str:
    brief = _metrics_brief(metrics)
    if llm:
        prompt = (
            "Write one concise English description of the following exploratory "
            f"effect. Be objective and specific. Effect type: {effect_type}.\n"
            f"EDA: {brief}"
        )
        try:
            text = llm(prompt)
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception:
            pass
    return _fallback_desc(effect_type, metrics)


def _metrics_brief(metrics: Dict[str, Any]) -> str:
    pairs = []
    for k, v in list(metrics.items())[:6]:
        pairs.append(f"{k}={v}")
    return ", ".join(pairs)


def _fallback_desc(effect_type: str, metrics: Dict[str, Any]) -> str:
    if effect_type == "global_trend":
        s = metrics.get("slope")
        if isinstance(s, (int, float)):
            return "The overall trend rises over time." if s > 0 else "The overall trend falls over time."
        return "The outcome exhibits an overall temporal trend."
    if effect_type == "group_level_diff":
        d = metrics.get("mean_diff_top2")
        if isinstance(d, (int, float)):
            return "The two leading groups have different means." if abs(d) > 0 else "The two leading groups have similar means."
        return "Mean levels differ across groups."
    if effect_type == "group_trend_diff":
        m = metrics.get("slope_diff_max")
        if isinstance(m, (int, float)):
            return "Temporal trends differ across groups." if m > 0 else "Temporal trends are similar across groups."
        return "Groups exhibit different temporal trends."
    if effect_type == "intervention_effect":
        pre = metrics.get("pre_mean")
        post = metrics.get("post_mean")
        if isinstance(pre, (int, float)) and isinstance(post, (int, float)):
            return "The outcome increases after the intervention." if post > pre else "The outcome decreases after the intervention."
        return "The outcome changes after the intervention."
    if effect_type == "distribution_shift":
        ms = metrics.get("mean_shift_q25")
        if isinstance(ms, (int, float)):
            return "The distribution mean shifts upward over time." if ms > 0 else "The distribution mean shifts downward over time."
        return "The distribution shifts over time."
    return "The data contain an exploratory pattern."
