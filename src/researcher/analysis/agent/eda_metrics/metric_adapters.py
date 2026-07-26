from typing import Dict, Any, List
import numpy as np
import pandas as pd

from .metric_registry import MetricRegistry, MetricRecord, MetricType
from ..llm.llm_struct_adapter import propose_metric_mapping, apply_mapping_to_rows


def adapt_registry_to_tables(reg: MetricRegistry) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for rec in reg.items():
        out = {"metric_name": rec.metric_name, "type": rec.type}
        if rec.flags.insufficient_data:
            out.update({"ok": False, "reason": rec.flags.reason})
            items.append(out)
            continue
        if rec.type == MetricType.time_series:
            df = _adapt_time_series(rec.raw_rows)
        elif rec.type == MetricType.distribution:
            df = _adapt_distribution(rec.raw_rows)
        elif rec.type == MetricType.summary:
            df = _adapt_summary(rec.raw_rows)
        else:
            out.update({"ok": False, "reason": "unknown_type"})
            items.append(out)
            continue
        # 若失败，尝试 LLM 结构适配（受限解析）
        if (df is None or df.empty) and rec.raw_rows:
            try:
                mapping = propose_metric_mapping(rec.metric_name, rec.raw_rows, list(rec.raw_rows[0].keys()))
                df = apply_mapping_to_rows(mapping, rec.raw_rows)
            except Exception:
                pass
        ok = df is not None and not df.empty
        out.update({"ok": ok, "reason": None if ok else "empty_table"})
        if ok:
            out.update({"table_preview": df.head(3).to_dict(orient="records")})
        items.append(out)
    return {"items": items}


def _adapt_time_series(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    time_col = None
    for tc in ("step", "time", "t", "round"):
        if tc in df.columns:
            time_col = tc
            break
    group_col = None
    for gc in ("group_name", "group", "groupName"):
        if gc in df.columns:
            group_col = gc
            break
    if "data" not in df.columns:
        return pd.DataFrame()
    # 支持标量或 dict/数组聚合为单值
    def _extract_series(x):
        if isinstance(x, dict):
            if isinstance(x.get("series"), list):
                return x.get("series")
            if isinstance(x.get("values"), list):
                return x.get("values")
            if isinstance(x.get("counts"), list):
                return x.get("counts")
            return []
        if isinstance(x, (list, tuple)):
            return list(x)
        if isinstance(x, (int, float)):
            return [x]
        return []

    vals = df["data"].map(lambda v: _extract_series(v))
    agg_vals = vals.map(lambda arr: float(np.nanmean(arr)) if len(arr) > 0 else np.nan)

    out = pd.DataFrame({
        "value": pd.to_numeric(agg_vals, errors="coerce"),
    })
    # 时间兜底：优先使用提供的时间列，否则用行序；若方差为0则用行序替换
    if time_col:
        out["time"] = _to_numeric_time(df[time_col])
    else:
        out["time"] = np.arange(len(out), dtype=float)
    # 若时间方差为0或唯一值过少，改用行序
    try:
        if out["time"].nunique() < 2 or float(np.nanvar(out["time"].to_numpy())) == 0.0:
            out["time"] = np.arange(len(out), dtype=float)
    except Exception:
        out["time"] = np.arange(len(out), dtype=float)

    if group_col:
        out["group"] = df[group_col].astype(str)
    # 去除缺失
    out = out.dropna()
    # 最少两个点
    if len(out) < 2:
        return pd.DataFrame()
    return out


def _adapt_distribution(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    time_col = None
    for tc in ("step", "time", "t", "round"):
        if tc in df.columns:
            time_col = tc
            break
    group_col = None
    for gc in ("group_name", "group", "groupName"):
        if gc in df.columns:
            group_col = gc
            break
    def _extract_series(x):
        if isinstance(x, dict):
            if isinstance(x.get("series"), list):
                return x.get("series")
            if isinstance(x.get("values"), list):
                return x.get("values")
            if isinstance(x.get("counts"), list):
                return x.get("counts")
            return []
        if isinstance(x, (list, tuple)):
            return list(x)
        return []
    dist = df[df["data"].map(lambda x: len(_extract_series(x)) > 0)]
    if dist.empty:
        return pd.DataFrame()
    series_len = dist["data"].map(lambda d: len(_extract_series(d)))
    series_mean = dist["data"].map(lambda d: float(np.nanmean(_extract_series(d))) if len(_extract_series(d)) > 0 else np.nan)
    out = pd.DataFrame({
        "value_agg": series_mean,
        "n": series_len,
    })
    if time_col:
        out["time"] = _to_numeric_time(dist[time_col])
    if group_col:
        out["group"] = dist[group_col].astype(str)
    return out.dropna()


def _adapt_summary(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "data" not in df.columns:
        return pd.DataFrame()
    scalar = df[df["data"].map(lambda x: isinstance(x, (int, float)))]
    if scalar.empty:
        return pd.DataFrame()
    group_col = None
    for gc in ("group_name", "group", "groupName"):
        if gc in df.columns:
            group_col = gc
            break
    out = pd.DataFrame({"stat_value": pd.to_numeric(scalar["data"], errors="coerce")})
    if group_col:
        out["group"] = scalar[group_col].astype(str)
    return out.dropna()


def _to_numeric_time(s: pd.Series) -> pd.Series:
    if np.issubdtype(s.dtype, np.number):
        return pd.to_numeric(s, errors="coerce").astype(float)
    # handle strings like 'step_1'
    try:
        ss = s.astype(str).str.replace("^step_", "", regex=True)
        num = pd.to_numeric(ss, errors="coerce")
        if num.notna().any():
            return num.astype(float)
    except Exception:
        pass
    # datetime to int64 ns
    try:
        dt = pd.to_datetime(s, errors="coerce")
        return dt.view("int64").astype(float)
    except Exception:
        pass
    # final fallback
    return pd.to_numeric(s, errors="coerce").astype(float)


__all__ = ["adapt_registry_to_tables"]