import os
import json
from typing import Any, Dict
from pathlib import Path

from .metric_registry import MetricRegistry, MetricRecord
from researcher.analysis.common import resolve_project_paths


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "projects").exists():
            return parent
    return p.parents[len(p.parents) - 1]


def _read_processed_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    data = obj.get("data") if isinstance(obj, dict) else obj
    return data if isinstance(data, list) else []


def load_project_metrics(project_name: str) -> MetricRegistry:
    processed_dir = Path(resolve_project_paths(project_name)["processed_dir"])
    reg = MetricRegistry()
    if not processed_dir.exists():
        return reg
    for fname in sorted(os.listdir(processed_dir)):
        if not fname.endswith("_all_groups.json"):
            continue
        if fname.startswith("figures_analysis_combine"):
            continue
        base = os.path.splitext(fname)[0].replace("_all_groups", "")
        rows = _read_processed_file(str(processed_dir / fname))
        rec = MetricRecord(metric_name=base, file_path=str(processed_dir / fname), raw_rows=rows)
        reg.add(rec)
    return reg


__all__ = ["load_project_metrics"]
