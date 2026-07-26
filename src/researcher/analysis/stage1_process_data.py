"""
Stage1: Process data by collecting scene metrics (simple)
- CLI compatible with the existing collector script
- Provides programmatic API: run_stage1(...)
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()

# Imports
try:
    from researcher.analysis.agent.utils.collect_scene_metrics_simple import SimpleSceneMetricsCollector
except ImportError:
    from src.researcher.analysis.agent.utils.collect_scene_metrics_simple import SimpleSceneMetricsCollector

try:
    from researcher.analysis.context.semantic.research_semantic_summary import build_summary
except ImportError:
    try:
        from src.researcher.analysis.context.semantic.research_semantic_summary import build_summary
    except ImportError:
        build_summary = None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage1: Collect scene metrics (simple)."
    )
    parser.add_argument("--groups-path", type=str, required=False)
    parser.add_argument("--output-dir", type=str, required=False)
    parser.add_argument("--project-name", type=str, default=None)
    parser.add_argument("--latest-runs", type=int, default=1)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _load_group_types(project_name: Optional[str]) -> dict:
    """
    Load rich group types from experiment_config.json if available.

    Returns a dict mapping group_name -> {
        "type": "control" | "treatment" | "replicate" | "observation",
        "replicate_of": base_group_name (only for replicates),
        "all_runs": [list of all run names] (only for base groups),
        "description": group description if available
    }
    """
    if not project_name:
        return {}
    try:
        paths = resolve_project_paths(project_name)
        project_dir = Path(paths["project_dir"])
        exp_config_path = project_dir / "experiment_design" / "experiment_config.json"
        if exp_config_path.exists():
            import json
            with open(exp_config_path, 'r', encoding='utf-8') as f:
                experiment_config = json.load(f)

            # Use the same extraction logic as research_semantic_summary
            try:
                from researcher.analysis.context.semantic.research_semantic_summary import _extract_group_types
            except ImportError:
                from src.researcher.analysis.context.semantic.research_semantic_summary import _extract_group_types

            group_types = _extract_group_types(experiment_config)
            logger.info(f"Loaded {len(group_types)} group types from experiment_config.json (rich structure)")
            return group_types
    except Exception as e:
        logger.warning(f"Failed to load group types: {e}")
    return {}


def run_stage1(
    groups_base_path: str,
    output_dir: str,
    latest_runs: int = 1,
    verbose: bool = False,
    project_name: Optional[str] = None,
) -> int:
    """Programmatic API for Stage1 processing. Returns 0 on success, 1 on error."""
    try:
        groups_path = Path(groups_base_path)
        if not groups_path.exists():
            logger.error(f"Groups directory does not exist: {groups_base_path}")
            return 1

        # Load group types from experiment_config.json
        group_types = _load_group_types(project_name)

        collector = SimpleSceneMetricsCollector(
            groups_base_path=groups_base_path,
            output_dir=output_dir,
            latest_runs=latest_runs,
            group_types=group_types,
        )
        collector.save()

        if project_name and build_summary:
            logger.info(f"Generating semantic summary for project: {project_name}")
            try:
                build_summary(project_name)
                logger.info("Semantic summary generated successfully.")
            except Exception as e:
                logger.error(f"Failed to generate semantic summary: {e}")
        elif project_name and not build_summary:
            logger.warning("build_summary function could not be imported. Skipping semantic summary generation.")

        return 0
    except Exception as e:
        logger.error(f"Stage1 processing error: {e}")
        return 1


def main(
    groups_base_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    latest_runs: int = 1,
) -> int:
    # Parse arguments if paths not provided
    if groups_base_path is None or output_dir is None:
        args = parse_arguments()
        project_name = getattr(args, "project_name", None)
        
        resolved_groups = args.groups_path
        resolved_output = args.output_dir

        if project_name:
            paths = resolve_project_paths(project_name)
            resolved_groups = paths["groups_dir"]
            resolved_output = paths["processed_dir"]
            logger.info(f"Using project-name derived paths: {resolved_groups} -> {resolved_output}")
        
        if not resolved_groups or not resolved_output:
             logger.error("When --project-name is not provided, both --groups-path and --output-dir are required.")
             return 1

        latest_runs = int(getattr(args, "latest_runs", latest_runs))
        verbose = bool(getattr(args, "verbose", False))
        return run_stage1(
            groups_base_path=resolved_groups,
            output_dir=resolved_output,
            latest_runs=latest_runs,
            verbose=verbose,
            project_name=project_name,
        )
    
    # direct call path
    return run_stage1(
        groups_base_path=groups_base_path,
        output_dir=output_dir,
        latest_runs=latest_runs,
        verbose=False,
    )


if __name__ == "__main__":
    sys.exit(main())
