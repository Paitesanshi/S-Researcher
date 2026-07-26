from typing import Dict, Any
import pandas as pd

from .metric_registry import MetricRegistry, MetricType
from .metric_type_infer import infer_types_for_registry
from .metric_adapters import adapt_registry_to_tables
from .metric_eda_handlers import eda_time_series, eda_distribution, eda_summary


def run_metric_eda(reg: MetricRegistry, llm=None) -> Dict[str, Any]:
    infer_types_for_registry(reg, llm=llm)
    tables_info = adapt_registry_to_tables(reg)
    items = []
    # 这里仅返回 EDA 结果摘要；真实表预览在 tables_info
    for rec in reg.items():
        if rec.flags.insufficient_data:
            items.append({
                "metric_name": rec.metric_name,
                "type": rec.type,
                "eda": {"metrics": {}, "quality": {"insufficient": True, "notes": [rec.flags.reason]}},
            })
            continue
        df = _materialize_table(rec)
        if rec.type == MetricType.time_series:
            eda = eda_time_series(df)
        elif rec.type == MetricType.distribution:
            eda = eda_distribution(df)
        elif rec.type == MetricType.summary:
            eda = eda_summary(df)
        else:
            eda = {"metrics": {}, "quality": {"insufficient": True, "notes": ["unknown_type"]}}
        items.append({"metric_name": rec.metric_name, "type": rec.type, "eda": eda})
    return {"schema_version": "0.1.0", "items": items}


def _materialize_table(rec) -> pd.DataFrame:
    from .metric_adapters import _adapt_time_series, _adapt_distribution, _adapt_summary
    if rec.type == MetricType.time_series:
        return _adapt_time_series(rec.raw_rows)
    if rec.type == MetricType.distribution:
        return _adapt_distribution(rec.raw_rows)
    if rec.type == MetricType.summary:
        return _adapt_summary(rec.raw_rows)
    import pandas as pd
    return pd.DataFrame()


__all__ = ["run_metric_eda"]