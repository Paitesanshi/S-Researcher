from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import sys

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()


def _log(level: str, msg: str) -> None:
    lvl = (level or "INFO").upper()
    if lvl == "INFO":
        logger.info(f"stage3-analysis - {msg}")
    elif lvl in ("WARN", "WARNING"):
        logger.warning(f"stage3-analysis - {msg}")
    elif lvl == "ERROR":
        logger.error(f"stage3-analysis - {msg}")
    else:
        logger.debug(f"stage3-analysis - {msg}")


def run_stage3(project_name: str, config_name: Optional[str] = None) -> Dict[str, Any]:
    _log("INFO", f"Starting Stage 3 Analysis for project: {project_name}")

    try:
        from researcher.analysis.agent.stage3.data_loader import DataLoader
        from researcher.analysis.agent.stage3.stat_analyzer import StatAnalyzer
        from researcher.analysis.agent.stage3.visual_analyzer import VisualAnalyzer
    except ImportError:
        from src.researcher.analysis.agent.stage3.data_loader import DataLoader
        from src.researcher.analysis.agent.stage3.stat_analyzer import StatAnalyzer
        from src.researcher.analysis.agent.stage3.visual_analyzer import VisualAnalyzer

    loader = DataLoader(project_name)
    stat_analyzer = StatAnalyzer()
    visual_analyzer = VisualAnalyzer()

    items = loader.get_analysis_items()
    _log("INFO", f"Found {len(items)} items to analyze.")

    results = {}

    for item in items:
        item_id = item["id"]
        question = item["research_question"]
        _log("INFO", f"Processing Item {item_id}: {question}")

        context = loader.get_analysis_context(item_id)
        stat_result = {}
        if context.get("data"):
            _log("INFO", f"Performing statistical analysis for {item_id}...")
            stat_result = stat_analyzer.analyze(
                context["data"], 
                question, 
                item.get("analysis_type", "exploratory")
            )
        else:
            _log("WARNING", f"No data found for {item_id}, skipping statistical analysis.")
            stat_result = {"status": "skipped", "reason": context.get("data_error", "No data")}

        visual_result = {}
        stats_summary = stat_result.get("structured_analysis")
        _log("INFO", f"Performing visual analysis for {item_id}...")
        visual_result = visual_analyzer.analyze(
            context.get("figure_path"),
            question,
            stats_summary
        )

        conclusion = "Analysis completed."
        if stat_result.get("structured_analysis"):
            conclusion += " Statistical insights available."
        if visual_result.get("status") == "success":
            conclusion += " Visual evidence supported."
            
        results[question] = {
            "id": item_id,
            "hypothesis": item.get("hypothesis_ref"),
            "statistical_analysis": stat_result,
            "visual_analysis": visual_result,
            "conclusion": conclusion,
            "timestamp": datetime.now().isoformat()
        }

    output_dir = loader.analysis_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "stage3_analysis_results.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    _log("INFO", f"Stage 3 Analysis complete. Results saved to {output_path}")
    return {"status": "ok", "output_path": str(output_path), "count_items": len(items)}

def main():
    parser = argparse.ArgumentParser(description="Stage 3 Data Analysis Coordinator")
    parser.add_argument("--project-name", required=True, help="Project name")
    args = parser.parse_args()
    run_stage3(args.project_name)

if __name__ == "__main__":
    main()
