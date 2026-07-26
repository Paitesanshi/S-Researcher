from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from .agent_client import SimpleChatLLM
from researcher.analysis.common import get_common_model_name, get_model_config_path


def propose_metric_mapping(metric_name: str, rows: List[Dict[str, Any]], available_fields: List[str], llm: Optional[Any] = None) -> Dict[str, Any]:
    sample_rows = []
    for r in rows[:10]:
        d = {}
        for k, v in r.items():
            if k == "data":
                if isinstance(v, dict):
                    d[k] = {kk: (vv[:10] if isinstance(vv, list) else vv) for kk, vv in v.items()}
                elif isinstance(v, (list, tuple)):
                    d[k] = list(v)[:10]
                else:
                    d[k] = v
            else:
                d[k] = v
        sample_rows.append(d)
    context = {
        "metric_name": metric_name,
        "available_fields": available_fields,
        "rows_sample": sample_rows,
        "format": {
            "type": ["time_series", "distribution"],
            "mapping": {
                "time_field": ["step", "time", "t", "round", "none"],
                "group_field": ["group_name", "group", "groupName", "none"],
                "value_extractor": {
                    "path": ["series", "values", "counts", "data_array", "scalar"],
                    "agg": ["mean", "median", "sum", "len"],
                },
            },
        },
        "instruction": "Return JSON with fields: {type, mapping:{time_field, group_field, value_extractor:{path,agg}}, confidence, notes}.",
    }
    system_prompt = "Return ONLY valid JSON with fields: {type, mapping:{time_field, group_field, value_extractor:{path,agg}}, confidence, notes}."
    if llm is None:
        client = SimpleChatLLM(config_name=get_common_model_name(), config_path=get_model_config_path())
        return client.chat_json(user_query=pd.io.json.dumps(context, force_ascii=False), system_prompt=system_prompt, temperature=0.2)
    return llm(pd.io.json.dumps(context, force_ascii=False))


def apply_mapping_to_rows(mapping: Dict[str, Any], rows: List[Dict[str, Any]]) -> pd.DataFrame:
    t = str(mapping.get("type"))
    m = mapping.get("mapping") or {}
    tf = m.get("time_field")
    gf = m.get("group_field")
    ve = m.get("value_extractor") or {}
    path = ve.get("path")
    agg = ve.get("agg")
    times = []
    groups = []
    values = []
    for r in rows:
        v = r.get("data")
        seq = []
        if path == "series" and isinstance(v, dict):
            seq = v.get("series") or []
        elif path == "values" and isinstance(v, dict):
            seq = v.get("values") or []
        elif path == "counts" and isinstance(v, dict):
            seq = v.get("counts") or []
        elif path == "data_array" and isinstance(v, (list, tuple)):
            seq = list(v)
        elif path == "scalar" and isinstance(v, (int, float)):
            seq = [v]
        val = None
        arr = np.array(seq, dtype=float) if len(seq) > 0 else np.array([])
        if arr.size > 0:
            if agg == "mean":
                val = float(np.nanmean(arr))
            elif agg == "median":
                val = float(np.nanmedian(arr))
            elif agg == "sum":
                val = float(np.nansum(arr))
            elif agg == "len":
                val = float(arr.size)
        elif path == "scalar" and len(seq) == 1:
            val = float(seq[0])
        if tf and tf != "none":
            times.append(str(r.get(tf)))
        else:
            times.append(None)
        if gf and gf != "none":
            groups.append(r.get(gf))
        else:
            groups.append(None)
        values.append(val)
    df = pd.DataFrame({"value": values})
    if any(times):
        df["time"] = times
    if any(groups):
        df["group"] = groups
    if t == "distribution":
        df.rename(columns={"value": "value_agg"}, inplace=True)
    return df.dropna()


__all__ = ["propose_metric_mapping", "apply_mapping_to_rows"]
