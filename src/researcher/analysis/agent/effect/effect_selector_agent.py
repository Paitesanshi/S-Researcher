from typing import Dict, Any, Optional, List
import numpy as np
import re
from .effect_catalog import get_effect_type


def select_effects(effect_candidates: Dict[str, Any], eda_summary: Dict[str, Any], llm: Optional[Any] = None, instances: Optional[Dict[str, Any]] = None, min_score: Optional[float] = None, top_k: Optional[int] = None) -> Dict[str, Any]:
    cand_items = effect_candidates.get("items", [])
    eda_map = {item.get("type"): item.get("metrics", {}) for item in eda_summary.get("items", [])}
    inst_map: Dict[str, Dict[str, Any]] = {}
    if instances:
        for it in instances.get("items", []):
            inst_map[it.get("type")] = it
    out: List[Dict[str, Any]] = []
    for c in cand_items:
        et = c.get("type")
        tr = float(c.get("task_relevance", 0.0))
        metrics = eda_map.get(et, {})
        ds = _data_salience(et, metrics)
        cost = float(get_effect_type(et).get("cost_score", 0.0))
        rule_score = max(0.0, min(1.0, 0.6 * tr + 0.4 * ds - 0.15 * cost))
        llm_score = _llm_score(llm, et, metrics, c.get("reason")) if llm else None
        final_score = rule_score if llm_score is None else float(np.clip(0.5 * rule_score + 0.5 * llm_score, 0.0, 1.0))
        item = {
            "effect_id": inst_map.get(et, {}).get("effect_id"),
            "type": et,
            "score": round(final_score, 3),
            "rule_score": round(rule_score, 3),
            "llm_score": None if llm_score is None else round(float(llm_score), 3),
            "task_relevance": round(tr, 3),
            "data_salience": round(ds, 3),
            "cost_score": round(cost, 3),
        }
        out.append(item)
    if min_score is not None:
        out = [it for it in out if it["score"] >= float(min_score)]
    if isinstance(top_k, int) and top_k > 0:
        out = sorted(out, key=lambda x: x["score"], reverse=True)[:top_k]
    return {"schema_version": "0.1.0", "items": out}


def _data_salience(effect_type: str, metrics: Dict[str, Any]) -> float:
    if effect_type == "global_trend":
        s = metrics.get("slope")
        r2 = metrics.get("r2")
        a = np.tanh(abs(float(s))) if isinstance(s, (int, float)) else 0.0
        b = float(r2) if isinstance(r2, (int, float)) else 0.0
        return float(np.clip(0.5 * a + 0.5 * b, 0.0, 1.0))
    if effect_type == "group_level_diff":
        d = metrics.get("cohen_d_top2")
        md = metrics.get("mean_diff_top2")
        a = np.tanh(abs(float(d))) if isinstance(d, (int, float)) else 0.0
        b = np.tanh(abs(float(md))) if isinstance(md, (int, float)) else 0.0
        return float(np.clip(0.6 * a + 0.4 * b, 0.0, 1.0))
    if effect_type == "group_trend_diff":
        m = metrics.get("slope_diff_max")
        a = np.tanh(abs(float(m))) if isinstance(m, (int, float)) else 0.0
        return float(np.clip(a, 0.0, 1.0))
    if effect_type == "intervention_effect":
        did = metrics.get("did_estimate_top2")
        delta = None
        pre = metrics.get("pre_mean")
        post = metrics.get("post_mean")
        if isinstance(pre, (int, float)) and isinstance(post, (int, float)):
            delta = post - pre
        a = np.tanh(abs(float(did))) if isinstance(did, (int, float)) else 0.0
        b = np.tanh(abs(float(delta))) if isinstance(delta, (int, float)) else 0.0
        return float(np.clip(0.6 * a + 0.4 * b, 0.0, 1.0))
    if effect_type == "distribution_shift":
        ms = metrics.get("mean_shift_q25")
        sr = metrics.get("std_ratio_q25") or metrics.get("iqr_ratio_q25")
        a = np.tanh(abs(float(ms))) if isinstance(ms, (int, float)) else 0.0
        b = 0.0
        if isinstance(sr, (int, float)) and sr > 0:
            b = np.tanh(abs(np.log(float(sr))))
        return float(np.clip(0.5 * a + 0.5 * b, 0.0, 1.0))
    return 0.0


def _llm_score(llm: Any, effect_type: str, metrics: Dict[str, Any], reason: Optional[str]) -> Optional[float]:
    brief_pairs = []
    for k, v in list(metrics.items())[:6]:
        brief_pairs.append(f"{k}={v}")
    brief = ", ".join(brief_pairs)
    prompt = (
        "Score the overall analytical value of this exploratory effect from "
        "0 to 1. Return only the number.\n"
        f"Effect type: {effect_type}\n"
        f"Metrics: {brief}\n"
        f"Reason: {reason or ''}"
    )
    try:
        text = llm(prompt)
        if isinstance(text, (int, float)):
            val = float(text)
        else:
            s = str(text).strip()
            m = re.search(r"([0-9]*\.?[0-9]+)", s)
            val = float(m.group(1)) if m else None
        if val is None:
            return None
        return float(np.clip(val, 0.0, 1.0))
    except Exception:
        return None
