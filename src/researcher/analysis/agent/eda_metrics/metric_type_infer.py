from typing import Dict, Any, List, Optional
import math

from .metric_registry import MetricRegistry, MetricRecord, MetricType
from .llm_metric_analyzer import build_metric_type_llm


def infer_types_for_registry(reg: MetricRegistry, llm: Optional[Any] = None) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for rec in reg.items():
        llm_engine = llm or _maybe_build_llm()
        t, insufficient, reason = _infer_type(rec, llm_engine)
        rec.type = t
        rec.flags.insufficient_data = insufficient
        rec.flags.reason = reason
        rec.flags.unknown_type = t == MetricType.unknown
        results.append({
            "metric_name": rec.metric_name,
            "type": rec.type,
            "flags": {
                "insufficient_data": rec.flags.insufficient_data,
                "unknown_type": rec.flags.unknown_type,
                "reason": rec.flags.reason,
            },
        })
    return {"items": results}


def _infer_type(rec: MetricRecord, llm: Optional[Any] = None):
    rows = rec.raw_rows
    if not rows:
        return MetricType.unknown, True, "empty_rows"
    fields = set()
    sample_data = None
    for r in rows[:50]:
        for k in r.keys():
            fields.add(k)
        v = r.get("data")
        if sample_data is None and v is not None:
            sample_data = v
    has_time = any(f in fields for f in ("step", "time", "t", "round"))
    if sample_data is None:
        return MetricType.unknown, True, "no_data_field"
    if isinstance(sample_data, (list, tuple)):
        return MetricType.distribution, False, None
    if isinstance(sample_data, dict):
        if "series" in sample_data or "xAxis" in sample_data:
            return MetricType.distribution, False, None
        return MetricType.distribution, False, None
    if isinstance(sample_data, (int, float)) and not (isinstance(sample_data, float) and math.isnan(sample_data)):
        if has_time:
            return MetricType.time_series, False, None
        if llm is not None:
            try:
                s = _llm_choose(llm, rec.metric_name, list(fields))
                if s in (MetricType.time_series, MetricType.distribution):
                    return s, False, None
            except Exception:
                pass
        return MetricType.distribution, False, None
    return MetricType.distribution, False, "fallback_distribution"


def _llm_choose(llm: Any, metric_name: str, fields: List[str]) -> str:
    prompt = (
        "Classify this metric as either 'time_series' or 'distribution'. "
        "Return exactly one of those labels.\n"
        f"metric: {metric_name}\n"
        f"fields: {', '.join(fields)}"
    )
    out = llm(prompt)
    s = str(out).strip().lower()
    if "time_series" in s:
        return MetricType.time_series
    if "distribution" in s:
        return MetricType.distribution
    return ""


def _maybe_build_llm():
    try:
        return build_metric_type_llm()
    except Exception:
        return None


__all__ = ["infer_types_for_registry"]
