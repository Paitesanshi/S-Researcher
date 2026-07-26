from typing import Dict, Any, List
import numpy as np
import pandas as pd


def eda_time_series(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"metrics": {}, "quality": {"insufficient": True, "notes": ["empty"]}}
    x = pd.to_numeric(df.get("time"), errors="coerce")
    y = pd.to_numeric(df.get("value"), errors="coerce")
    mask = (~x.isna()) & (~y.isna())
    xv = x[mask].to_numpy()
    yv = y[mask].to_numpy()
    if xv.size < 2 or np.var(xv) == 0:
        return {"metrics": {"n": int(xv.size)}, "quality": {"insufficient": True, "notes": ["too_few_points"]}}
    varx = np.var(xv)
    slope = float(np.cov(xv, yv, bias=True)[0, 1] / varx)
    vary = np.var(yv)
    if varx > 0 and vary > 0:
        cov = float(np.cov(xv, yv, bias=True)[0, 1])
        r = float(cov / np.sqrt(varx * vary))
        r2 = float(r * r) if not np.isnan(r) else None
    else:
        r2 = None
    direction = "up" if slope > 0 else "down" if slope < 0 else "flat"
    return {"metrics": {"slope": slope, "r2": r2, "direction": direction, "n": int(len(xv))}, "quality": {"insufficient": False, "notes": []}}


def eda_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"metrics": {}, "quality": {"insufficient": True, "notes": ["empty"]}}
    # 优先按时间排序（step/time/t/round 已统一到 'time'）
    if "time" in df.columns:
        df = df.sort_values("time")
    y = pd.to_numeric(df.get("value_agg"), errors="coerce").dropna()
    if y.empty:
        return {"metrics": {"n": 0}, "quality": {"insufficient": True, "notes": ["no_values"]}}
    q = int(max(len(y) * 0.25, 1))
    first = y.iloc[:q]
    last = y.iloc[-q:]
    mean_shift = float(np.nanmean(last) - np.nanmean(first)) if len(first) and len(last) else None
    # 使用 IQR 比例，避免零方差导致的空值
    def _iqr(arr: pd.Series) -> float:
        q75 = np.nanpercentile(arr, 75)
        q25 = np.nanpercentile(arr, 25)
        return float(q75 - q25)
    iqr1 = _iqr(first) if len(first) else np.nan
    iqr2 = _iqr(last) if len(last) else np.nan
    iqr_ratio = None
    if not np.isnan(iqr1) and iqr1 > 0 and not np.isnan(iqr2):
        iqr_ratio = float(iqr2 / iqr1)
    return {"metrics": {"mean_shift_q25": mean_shift, "iqr_ratio_q25": iqr_ratio, "n": int(len(y))}, "quality": {"insufficient": False, "notes": []}}


def eda_summary(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"metrics": {}, "quality": {"insufficient": True, "notes": ["empty"]}}
    y = pd.to_numeric(df.get("stat_value"), errors="coerce").dropna()
    if y.empty:
        return {"metrics": {"n": 0}, "quality": {"insufficient": True, "notes": ["no_values"]}}
    return {"metrics": {"mean": float(np.nanmean(y)), "std": float(np.nanstd(y)), "n": int(len(y))}, "quality": {"insufficient": False, "notes": []}}


__all__ = ["eda_time_series", "eda_distribution", "eda_summary"]
