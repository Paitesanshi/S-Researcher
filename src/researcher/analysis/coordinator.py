#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OneSim Researcher Analysis Coordinator (E2E Pipeline)

Executes the analysis pipeline:
1) Stage 1: Data Processing (Collection & Semantic Summary)
2) Stage 2: Figure Analysis (Plan -> Code -> Execute -> Review -> Explain)
3) Stage 3: Data Analysis (Deep Statistical & Visual Analysis)

Input: project_name
"""

import sys
import os
import json
import argparse
from typing import Dict, Any
from pathlib import Path

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    # If running as script
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()


def coordinate_analysis(project_name: str, config_name: str = "default-chat", latest_runs: int = 1) -> Dict[str, Any]:
    """
    Unified Coordinator.
    """
    paths = resolve_project_paths(project_name)
    project_dir = Path(paths["project_dir"])
    logger.info(f"[coordinator] Using project dir: {project_dir}")

    from researcher.analysis.common import apply_model_env, get_model_config_path
    apply_model_env(common_model=config_name, plot_model=config_name, config_path=get_model_config_path())

    # --- Stage 1: Data Processing ---
    logger.info("[coordinator] Stage 1: Data Processing (Collection & Summary)")
    from researcher.analysis.stage1_process_data import run_stage1
    
    # run_stage1 handles collection and semantic summary
    ret = run_stage1(
        groups_base_path=paths["groups_dir"],
        output_dir=paths["processed_dir"],
        latest_runs=int(latest_runs),
        project_name=project_name,
        verbose=True
    )
    if ret != 0:
        logger.error("[coordinator] Stage 1 failed.")
        # We might want to continue or exit? Continuing might be futile if no data.
        # But let's proceed as some data might exist.

    # --- Stage 1.5: Analysis Planning ---
    logger.info("[coordinator] Stage 1.5: Analysis Planning")
    try:
        from researcher.analysis.stage1_5_analysis_planning import run_analysis_planning
        run_analysis_planning(project_name)
    except Exception as e:
        logger.warning(f"[coordinator] Stage 1.5 planning failed: {e}. Proceeding to Stage 2 with fallback.")

    # --- Stage 2: Figure Generation & Analysis ---
    logger.info("[coordinator] Stage 2: Figure Generation & Analysis")
    from researcher.analysis.stage2_figure_analysis import stage2_run

    # Ensure stage1 outputs are available as context (workflow_state)
    # stage2_run loads workflow_state internally.
    
    stage2_result = stage2_run(
        project_name=project_name,
        options={
            "with_review": True,   # Enable review if available
            "with_analysis": True, # Enable explanation if available
            "max_round": 2
        }
    )
    
    # --- Stage 3: Deep Data Analysis ---
    logger.info("[coordinator] Stage 3: Deep Data Analysis")
    from researcher.analysis.stage3_data_analysis import run_stage3

    run_stage3(project_name, config_name=config_name)

    # Summary
    summary = {
        "project_dir": str(project_dir),
        "paths": paths,
        "stage2_summary": stage2_result.get("summary"),
        "model_config": config_name,
    }
    logger.info("[coordinator] Pipeline completed successfully")
    return summary


def main():
    parser = argparse.ArgumentParser(description="OneSim Researcher: End-to-End analysis coordinator.")
    parser.add_argument("project_name", help="Project name under projects/ or absolute path")
    parser.add_argument("--config-name", default="default-chat", help="Model config name (default: default-chat)")
    parser.add_argument("--latest-runs", type=int, default=1, help="Collect latest N runs per group (default: 1)")
    args = parser.parse_args()

    summary = coordinate_analysis(args.project_name, config_name=args.config_name, latest_runs=args.latest_runs)
    try:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception:
        pass


if __name__ == "__main__":
    main()
