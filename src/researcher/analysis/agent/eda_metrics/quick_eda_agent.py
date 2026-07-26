from typing import Dict, Any, List
import numpy as np
import pandas as pd


def compute_quick_eda(df: pd.DataFrame, column_hints: Dict[str, Any], candidate_types: List[str]) -> Dict[str, Any]:
    time_col = column_hints.get("time_col")
    group_col = column_hints.get("group_col")
    dv_col = column_hints.get("dv_col")
    intervention_point = column_hints.get("intervention_point")
    items: List[Dict[str, Any]] = []
    for t in candidate_types:
        metrics: Dict[str, Any] = {}
        if t == "global_trend" and time_col and dv_col and time_col in df and dv_col in df:
            x = _to_numeric_time(df[time_col])
            y = pd.to_numeric(df[dv_col], errors="coerce")
            mask = (~x.isna()) & (~y.isna())
            xv = x[mask].to_numpy()
            yv = y[mask].to_numpy()
            if xv.size > 1 and np.var(xv) > 0:
                slope = float(np.cov(xv, yv, bias=True)[0, 1] / np.var(xv))
                r = np.corrcoef(xv, yv)[0, 1]
                r2 = float(r * r) if not np.isnan(r) else None
                metrics = {"slope": slope, "r2": r2}
        if t == "group_level_diff" and group_col and dv_col and group_col in df and dv_col in df:
            g = df[group_col]
            y = pd.to_numeric(df[dv_col], errors="coerce")
            grp = g.astype(str)
            means = y.groupby(grp).mean().to_dict()
            vars_ = y.groupby(grp).var(ddof=1).to_dict()
            counts = grp.value_counts().to_dict()
            top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:2]
            mean_diff = None
            cohen_d = None
            if len(top) == 2:
                a, b = top[0][0], top[1][0]
                ya = y[grp == a]
                yb = y[grp == b]
                ma = float(np.nanmean(ya))
                mb = float(np.nanmean(yb))
                va = float(np.nanvar(ya, ddof=1))
                vb = float(np.nanvar(yb, ddof=1))
                na = float(np.sum(~np.isnan(ya)))
                nb = float(np.sum(~np.isnan(yb)))
                mean_diff = ma - mb
                sp = np.sqrt(((na - 1) * va + (nb - 1) * vb) / max(na + nb - 2, 1))
                cohen_d = float(mean_diff / sp) if sp > 0 else None
            metrics = {"means_by_group": means, "vars_by_group": vars_, "mean_diff_top2": mean_diff, "cohen_d_top2": cohen_d}
        if t == "group_trend_diff" and time_col and group_col and dv_col and time_col in df and group_col in df and dv_col in df:
            x = _to_numeric_time(df[time_col])
            y = pd.to_numeric(df[dv_col], errors="coerce")
            grp = df[group_col].astype(str)
            slopes: Dict[str, float] = {}
            for name, sub in df[[time_col, dv_col, group_col]].dropna().groupby(grp):
                xv = _to_numeric_time(sub[time_col]).to_numpy()
                yv = pd.to_numeric(sub[dv_col], errors="coerce").to_numpy()
                if xv.size > 1 and np.var(xv) > 0:
                    s = float(np.cov(xv, yv, bias=True)[0, 1] / np.var(xv))
                    slopes[name] = s
            slope_diff_max = None
            if slopes:
                vals = list(slopes.values())
                slope_diff_max = float(np.max(vals) - np.min(vals))
            metrics = {"slope_by_group": slopes, "slope_diff_max": slope_diff_max}
        if t == "intervention_effect" and time_col and dv_col and time_col in df and dv_col in df and intervention_point is not None:
            x = _to_numeric_time(df[time_col])
            y = pd.to_numeric(df[dv_col], errors="coerce")
            mask_pre = x <= _to_numeric_point(intervention_point)
            mask_post = x > _to_numeric_point(intervention_point)
            pre_mean = float(np.nanmean(y[mask_pre])) if np.any(mask_pre) else None
            post_mean = float(np.nanmean(y[mask_post])) if np.any(mask_post) else None
            did_estimate = None
            deltas_by_group: Dict[str, float] = {}
            if group_col and group_col in df:
                grp = df[group_col].astype(str)
                for name, idx in grp.groupby(grp).groups.items():
                    ym = y.iloc[list(idx)]
                    xm = x.iloc[list(idx)]
                    pre = float(np.nanmean(ym[xm <= _to_numeric_point(intervention_point)])) if np.any(xm <= _to_numeric_point(intervention_point)) else np.nan
                    post = float(np.nanmean(ym[xm > _to_numeric_point(intervention_point)])) if np.any(xm > _to_numeric_point(intervention_point)) else np.nan
                    deltas_by_group[name] = post - pre if not np.isnan(pre) and not np.isnan(post) else np.nan
                if len(deltas_by_group) >= 2:
                    sorted_pairs = sorted(deltas_by_group.items(), key=lambda x: (-np.nan_to_num(x[1], nan=-1e9), x[0]))
                    a, b = sorted_pairs[0][0], sorted_pairs[1][0]
                    da = deltas_by_group[a]
                    db = deltas_by_group[b]
                    if not np.isnan(da) and not np.isnan(db):
                        did_estimate = float(da - db)
            metrics = {"pre_mean": pre_mean, "post_mean": post_mean, "deltas_by_group": deltas_by_group, "did_estimate_top2": did_estimate}
        if t == "distribution_shift" and time_col and dv_col and time_col in df and dv_col in df:
            x = _to_numeric_time(df[time_col])
            y = pd.to_numeric(df[dv_col], errors="coerce")
            df2 = pd.DataFrame({"x": x, "y": y}).dropna().sort_values("x")
            n = len(df2)
            first = df2.iloc[: max(int(n * 0.25), 1)]
            last = df2.iloc[max(n - max(int(n * 0.25), 1), 0) :]
            mean_shift = float(np.nanmean(last["y"])) - float(np.nanmean(first["y"])) if len(first) and len(last) else None
            std_ratio = None
            s1 = float(np.nanstd(first["y"])) if len(first) else np.nan
            s2 = float(np.nanstd(last["y"])) if len(last) else np.nan
            if not np.isnan(s1) and s1 > 0 and not np.isnan(s2):
                std_ratio = float(s2 / s1)
            metrics = {"mean_shift_q25": mean_shift, "std_ratio_q25": std_ratio}
        items.append({"type": t, "metrics": metrics})
    return {"schema_version": "0.1.0", "items": items}


def _to_numeric_time(s: pd.Series) -> pd.Series:
    if np.issubdtype(s.dtype, np.number):
        return s.astype(float)
    try:
        dt = pd.to_datetime(s, errors="coerce")
        return dt.view("int64").astype(float)
    except Exception:
        return pd.to_numeric(s, errors="coerce").astype(float)


def _to_numeric_point(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(pd.to_datetime(v).value)
    except Exception:
        try:
            return float(v)
        except Exception:
            return np.nan

