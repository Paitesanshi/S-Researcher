import json
import os
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
from researcher.analysis.common import resolve_project_paths

class DataLoader:
    def __init__(self, project_name: str, base_dir: Optional[str] = None):
        self.project_name = project_name
        if Path(project_name).is_absolute():
            self.project_dir = Path(project_name).resolve()
        elif base_dir:
            self.project_dir = Path(base_dir).resolve() / "projects" / project_name
        else:
            self.project_dir = Path(resolve_project_paths(project_name)["project_dir"])
        self.base_dir = self.project_dir.parent.parent
        self.analysis_dir = self.project_dir / "analysis"
        
        self.plan_path = self.analysis_dir / "research_analysis_plan.json"
        self.figures_summary_path = self.analysis_dir / "figures" / "figures_summary.json"
        self.data_processed_dir = self.analysis_dir / "data" / "processed"

        self.plan_data = self._load_json(self.plan_path)
        self.figures_data = self._load_json(self.figures_summary_path)
        
        # Index figures by ID for faster lookup
        self.figures_map = {}
        if self.figures_data and "figures" in self.figures_data:
            for fig in self.figures_data["figures"]:
                if "id" in fig:
                    self.figures_map[fig["id"]] = fig

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return None

    def get_analysis_items(self) -> List[Dict[str, Any]]:
        if not self.plan_data or "analysis_items" not in self.plan_data:
            return []
        return self.plan_data["analysis_items"]

    def get_analysis_context(self, item_id: str) -> Dict[str, Any]:
        """
        Retrieve all context needed for analysis of a specific item.
        """
        # 1. Find the item in the plan
        item = next((i for i in self.get_analysis_items() if i["id"] == item_id), None)
        if not item:
            return {"error": f"Item {item_id} not found in plan"}

        context = {
            "item": item,
            "data_file_path": None,
            "data": None,
            "figure_info": None,
            "figure_path": None,
            "figure_status": "missing"
        }

        # 2. Resolve Data File
        if "evidence_support" in item and "file_name" in item["evidence_support"]:
            file_name = item["evidence_support"]["file_name"]
            data_path = self.data_processed_dir / file_name
            if data_path.exists():
                context["data_file_path"] = str(data_path)
                # Load data sample or full data? Let's load full data as DataFrame or Dict
                try:
                    if data_path.suffix == '.json':
                        with open(data_path, 'r', encoding='utf-8') as f:
                            context["data"] = json.load(f)
                    elif data_path.suffix == '.csv':
                        context["data"] = pd.read_csv(data_path).to_dict(orient='records')
                except Exception as e:
                    context["data_error"] = str(e)
            else:
                context["data_error"] = f"Data file not found: {data_path}"

        # 3. Resolve Figure
        if item_id in self.figures_map:
            fig_entry = self.figures_map[item_id]
            context["figure_info"] = fig_entry
            
            # Check status
            if fig_entry.get("status") == "success":
                # Check file existence
                if "file_info" in fig_entry and "absolute_path" in fig_entry["file_info"]:
                    abs_path = Path(fig_entry["file_info"]["absolute_path"])
                    if abs_path.exists():
                        context["figure_path"] = str(abs_path)
                        context["figure_status"] = "available"
                    else:
                        context["figure_status"] = "file_not_found"
                else:
                    context["figure_status"] = "path_info_missing"
            else:
                context["figure_status"] = fig_entry.get("status", "unknown_status")
        
        return context

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Data Loader")
    parser.add_argument("--project-name", required=True, help="Project name")
    parser.add_argument("--item-id", required=True, help="Item ID to load context for")
    
    args = parser.parse_args()
    
    loader = DataLoader(args.project_name)
    context = loader.get_analysis_context(args.item_id)
    
    print(json.dumps(context, indent=2, default=str))
