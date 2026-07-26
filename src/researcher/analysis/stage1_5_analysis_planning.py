from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()

try:
    from src.researcher.analysis.agent.planning.data_profile import scan_processed_data, DataMetric
    from src.researcher.analysis.agent.planning.analysis_planner_agent import AnalysisPlannerAgent
except ImportError:
    try:
        from researcher.analysis.agent.planning.data_profile import scan_processed_data, DataMetric
        from researcher.analysis.agent.planning.analysis_planner_agent import AnalysisPlannerAgent
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        # We might need to handle this if running as script without src in path, 
        # but setup_sys_path should handle it.


def generate_fallback_plan(project_name: str, metrics: List[DataMetric]) -> Dict[str, Any]:
    """
    Generates a basic plan if LLM fails.
    """
    items = []
    for i, m in enumerate(metrics):
        items.append({
            "id": f"fallback_{i}",
            "research_question": f"Analyze the distribution/trend of {m.category}",
            "hypothesis_ref": "Exploratory Analysis",
            "analysis_type": "descriptive",
            "visualization_needed": True,
            "feasibility": {
                "data_available": True,
                "data_granularity_sufficient": True,
                "sample_size_estimate": "unknown"
            },
            "evidence_support": {
                "file_name": m.file_name,
                "metric_category": m.category,
                "data_type": m.data_type.value,
                "reasoning": "Fallback generation due to planner failure."
            },
            "visualization_hint": {
                "suggested_plot_type": "bar" if m.data_type.value == "distribution" else "line",
                "x_axis": "auto",
                "y_axis": "auto",
                "comparison_aspect": "auto"
            }
        })
    
    return {
        "project_name": project_name,
        "meta_goal": "Fallback Analysis Plan",
        "analysis_items": items,
        "generated_method": "heuristic_fallback"
    }

def run_analysis_planning(project_name: str) -> Dict[str, Any]:
    paths = resolve_project_paths(project_name)
    summary_path = Path(paths["semantic_summary"])
    processed_dir = Path(paths["processed_dir"])
    output_plan_path = Path(paths["analysis_plan"])
    
    # 1. Load Semantic Summary
    summary_context = {}
    if summary_path.exists():
        try:
            with summary_path.open("r", encoding="utf-8") as f:
                summary_data = json.load(f)
            
            # Extract rich context
            extracted = summary_data.get("extracted", {})
            text_section = summary_data.get("text", {})
            inspiration = summary_data.get("inspiration", {}).get("simulation_scenario", {})
            
            # Extract experiment design information
            experiment_design = summary_data.get("experiment_design", {})
            replication_settings = experiment_design.get("replication_settings", {})
            group_types = experiment_design.get("group_types", {})
            analysis_config = experiment_design.get("analysis_config", {})

            summary_context = {
                "hypotheses": extracted.get("hypotheses", []),
                "core_question": extracted.get("core_question") or text_section.get("research_topic", ""),
                "independent_variable": extracted.get("independent_variable") or inspiration.get("independent_variable"),
                "dependent_variable": extracted.get("dependent_variable") or inspiration.get("dependent_variable"),
                "scenario_description": text_section.get("scenario_description") or inspiration.get("description", ""),
                "domain": summary_data.get("scene", {}).get("domain", ""),
                # Experiment design info for analysis planning
                "num_replicates": replication_settings.get("num_replicates", 1),
                "group_types": group_types,
                "statistical_tests": analysis_config.get("statistical_tests", []),
                "comparison_groups": analysis_config.get("comparison_groups", []),
            }
        except Exception as e:
            logger.error(f"Failed to read summary: {e}")
    else:
        logger.warning(f"Summary file not found: {summary_path}")

    # 2. Scan Data
    metrics = []
    if processed_dir.exists():
        metrics = scan_processed_data(processed_dir)
        logger.info(f"Found {len(metrics)} data metrics.")
    else:
        logger.warning(f"Processed dir not found: {processed_dir}")

    # 3. Plan with Agent
    plan = {}
    try:
        agent = AnalysisPlannerAgent()
        
        # Run Agent if we have LLM and either hypotheses OR data metrics (for inductive analysis)
        if agent.llm and (summary_context.get("hypotheses") or metrics):
            logger.info("Invoking AnalysisPlannerAgent...")
            plan = agent.plan_analysis(project_name, summary_context, metrics)
    except Exception as e:
        logger.error(f"AnalysisPlannerAgent failed: {e}")
    
    # 4. Fallback if needed
    if not plan or "error" in plan or not plan.get("analysis_items"):
        if "error" in plan:
            logger.error(f"Agent failed: {plan['error']}")
        logger.info("Generating fallback plan...")
        plan = generate_fallback_plan(project_name, metrics)

    # 5. Save Plan
    try:
        output_plan_path.parent.mkdir(parents=True, exist_ok=True)
        with output_plan_path.open("w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        logger.info(f"Plan saved to {output_plan_path}")
    except Exception as e:
        logger.error(f"Failed to save plan: {e}")

    return plan

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", required=True)
    args = parser.parse_args()
    
    run_analysis_planning(args.project_name)
