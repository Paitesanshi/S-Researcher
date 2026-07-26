import argparse
import json
import sys
import pandas as pd
from typing import Any
from pathlib import Path

# Common Utils
try:
    from .common import setup_sys_path
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path

setup_sys_path()

# Imports with fallback
try:
    from researcher.analysis.agent.effect.effect_discovery_runner import run_effect_discovery
    from researcher.analysis.agent.effect.effect_project_runner import run_effect_discovery_for_project
    from researcher.analysis.agent.eda_metrics.project_metric_loader import load_project_metrics
    from researcher.analysis.agent.eda_metrics.metric_registry import MetricRegistry
    from researcher.analysis.agent.eda_metrics.metric_eda_runner import run_metric_eda
    from researcher.analysis.agent.effect.effect_project_runner_v2 import run_effect_discovery_v2
except ImportError:
    from src.researcher.analysis.agent.effect.effect_discovery_runner import run_effect_discovery
    from src.researcher.analysis.agent.effect.effect_project_runner import run_effect_discovery_for_project
    from src.researcher.analysis.agent.eda_metrics.project_metric_loader import load_project_metrics
    from src.researcher.analysis.agent.eda_metrics.metric_registry import MetricRegistry
    from src.researcher.analysis.agent.eda_metrics.metric_eda_runner import run_metric_eda
    from src.researcher.analysis.agent.effect.effect_project_runner_v2 import run_effect_discovery_v2


def _dummy_llm(x: Any) -> str:
    return "0.7"


def main():
    parser = argparse.ArgumentParser(description="Run Effect Discovery")
    sub = parser.add_subparsers(dest="mode")

    p_file = sub.add_parser("file", help="Run on a data file")
    p_file.add_argument("data_path", type=str, help="Path to CSV/Parquet data file")
    p_file.add_argument("task_text", type=str, help="Task description text")
    p_file.add_argument("dv_col", type=str, help="Dependent variable column name")
    p_file.add_argument("time_col", type=str, nargs="?", default=None, help="Time column name (optional)")
    p_file.add_argument("group_col", type=str, nargs="?", default=None, help="Group column name (optional)")
    p_file.add_argument("intervention_point", type=str, nargs="?", default=None, help="Intervention point (optional)")
    p_file.add_argument("min_score", type=float, nargs="?", default=None, help="Min score to filter effects (optional)")

    p_proj = sub.add_parser("project", help="Run on a project processed directory")
    p_proj.add_argument("project_name", type=str, help="Project name under projects/<name>")
    p_proj.add_argument("task_text", type=str, help="Task description text")
    p_proj.add_argument("min_score", type=float, nargs="?", default=None, help="Min score to filter effects (optional)")

    p_metrics = sub.add_parser("project-metrics", help="List metrics discovered in a project")
    p_metrics.add_argument("project_name", type=str, help="Project name under projects/<name>")
    p_eda = sub.add_parser("project-eda", help="Run per-metric EDA on a project")
    p_eda.add_argument("project_name", type=str, help="Project name under projects/<name>")
    p_v2 = sub.add_parser("project-v2", help="Run per-metric Effect Discovery v2 on a project")
    p_v2.add_argument("project_name", type=str, help="Project name under projects/<name>")
    p_v2.add_argument("min_score", type=float, nargs="?", default=None, help="Min score to filter effects (optional)")
    args = parser.parse_args()

    if args.mode == "project":
        result = run_effect_discovery_for_project(
            project_name=args.project_name,
            task_text=args.task_text,
            llm=_dummy_llm,
            min_score=args.min_score,
        )
    elif args.mode == "project-metrics":
        reg: MetricRegistry = load_project_metrics(args.project_name)
        result = {"metrics": reg.list_metrics()}
    elif args.mode == "project-eda":
        reg: MetricRegistry = load_project_metrics(args.project_name)
        result = run_metric_eda(reg)
    elif args.mode == "project-v2":
        result = run_effect_discovery_v2(
            project_name=args.project_name,
            llm=_dummy_llm,
            min_score=args.min_score,
        )
    else:
        if args.data_path.lower().endswith(".parquet"):
            df = pd.read_parquet(args.data_path)
        else:
            df = pd.read_csv(args.data_path)
        column_hints = {
            "dv_col": args.dv_col,
            "time_col": args.time_col,
            "group_col": args.group_col,
            "intervention_point": args.intervention_point,
        }
        result = run_effect_discovery(
            task_text=args.task_text,
            df=df,
            column_hints=column_hints,
            llm=_dummy_llm,
            min_score=args.min_score,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
