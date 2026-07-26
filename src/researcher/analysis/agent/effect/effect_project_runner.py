from typing import Dict, Any, Optional
from pathlib import Path
import json

import pandas as pd

from ..utils.processed_loader import build_loader_from_processed_dir
from .effect_discovery_runner import run_effect_discovery
from researcher.analysis.common import resolve_project_paths


def _infer_time_field(cols) -> Optional[str]:
    for tf in ("step", "time", "t", "round"):
        if tf in cols:
            return tf
    return None


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "projects").exists():
            return parent
    return p.parents[len(p.parents) - 1]


def run_effect_discovery_for_project(project_name: str, task_text: str, llm: Optional[Any] = None, min_score: Optional[float] = None) -> Dict[str, Any]:
    processed_dir = Path(resolve_project_paths(project_name)["processed_dir"])
    loader = build_loader_from_processed_dir(str(processed_dir))
    ctx = loader({})
    df: pd.DataFrame = ctx.get("data", pd.DataFrame())
    cols = df.columns.tolist()
    time_col = _infer_time_field(cols)
    group_col = "group_name" if "group_name" in cols else None
    column_hints = {
        "dv_col": "data",
        "time_col": time_col,
        "group_col": group_col,
        "intervention_point": None,
    }
    result = run_effect_discovery(task_text=task_text, df=df, column_hints=column_hints, llm=llm, min_score=min_score)
    return result


__all__ = ["run_effect_discovery_for_project"]
