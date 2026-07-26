from __future__ import annotations

import sys
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, List

# Try to import loguru, otherwise provide a fallback
try:
    from loguru import logger
except ImportError:
    import logging
    class _LoggerFallback:
        def __init__(self):
            self._logger = logging.getLogger("ResearcherAnalysis")
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            if not self._logger.handlers:
                self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

        def info(self, msg: str, *args, **kwargs):
            self._logger.info(msg, *args, **kwargs)

        def warning(self, msg: str, *args, **kwargs):
            self._logger.warning(msg, *args, **kwargs)

        def error(self, msg: str, *args, **kwargs):
            self._logger.error(msg, *args, **kwargs)

        def debug(self, msg: str, *args, **kwargs):
            self._logger.debug(msg, *args, **kwargs)

        def add(self, *args, **kwargs):
            pass # Dummy for loguru compatibility

        def remove(self, *args, **kwargs):
            pass

    logger = _LoggerFallback()


def get_project_root() -> Path:
    """
    Returns the repository root directory.
    Assumes this file is at src/researcher/analysis/common.py
    So root is parents[3]
    """
    return Path(__file__).resolve().parents[3]


def setup_sys_path():
    """
    Ensures the repository root and src directory are in sys.path.
    """
    root = get_project_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    
    src_str = str(root / "src")
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def resolve_project_paths(project_name: str, overrides: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Resolve canonical paths used across the analysis pipeline.
    
    Returns a dict with keys:
    - project_dir
    - groups_dir
    - analysis_dir
    - processed_dir
    - figures_dir
    - scene_info
    - workflow_state
    - analysis_plan
    - data_dir
    - outputs_dir (alias for figures_dir or effect dir depending on context, but here we standardize)
    """
    root = get_project_root()
    
    # Check if project_name is an absolute path or relative
    p_path = Path(project_name)
    if p_path.is_absolute() and p_path.exists():
        project_dir = p_path
    else:
        project_dir = root / "projects" / project_name

    analysis_dir = project_dir / "analysis"
    data_dir = analysis_dir / "data"
    
    paths = {
        "project_dir": str(project_dir),
        "groups_dir": str(project_dir / "groups"),
        "analysis_dir": str(analysis_dir),
        "data_dir": str(data_dir),
        "processed_dir": str(data_dir / "processed"),
        "figures_dir": str(analysis_dir / "figures"),
        "effect_dir": str(analysis_dir / "effect"),
        "scene_info": str(project_dir / "base_scenario" / "scene_info.json"),
        "workflow_state": str(project_dir / "workflow_state.json"),
        "analysis_plan": str(analysis_dir / "research_analysis_plan.json"),
        "semantic_summary": str(analysis_dir / "research_semantic_summary.json"),
    }
    
    # Aliases for compatibility
    paths["outputs_dir"] = paths["figures_dir"]
    
    if overrides:
        for k, v in overrides.items():
            if k in paths and v:
                paths[k] = v

    # Ensure directories exist
    for k in ["processed_dir", "figures_dir", "effect_dir"]:
        try:
            Path(paths[k]).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    return paths

def get_logger(name: str = "stage"):
    """
    Returns a logger instance. 
    If using loguru, it returns the global logger (loguru doesn't really use names like std logging).
    We can wrap it if needed to add context, but simple is better.
    """
    return logger

def get_model_config_path() -> str:
    p = os.environ.get("ONESIM_MODEL_CONFIG_PATH") or os.environ.get("ONESIM_MODEL_CONFIG") or "config/model_config.json"
    return str(p)

def get_common_model_name() -> str:
    n = os.environ.get("ANALYSIS_COMMON_MODEL_NAME") or os.environ.get("ONESIM_MODEL_NAME") or "default-chat"
    if n == "openai-gpt4o":
        n = "gpt-4o"
    return n

def get_plot_model_name() -> str:
    n = os.environ.get("ANALYSIS_PLOT_MODEL_NAME") or os.environ.get("ONESIM_PLOT_MODEL_NAME") or get_common_model_name()
    return n

def apply_model_env(common_model: Optional[str] = None, plot_model: Optional[str] = None, config_path: Optional[str] = None) -> None:
    cm = (common_model or get_common_model_name())
    pm = cm
    cp = (config_path or get_model_config_path())
    os.environ["ONESIM_MODEL_NAME"] = cm
    os.environ["ONESIM_MODEL_CONFIG"] = cp
    os.environ["ONESIM_MODEL_CONFIG_PATH"] = cp
    os.environ["ANALYSIS_COMMON_MODEL_NAME"] = cm
    os.environ["ANALYSIS_PLOT_MODEL_NAME"] = pm
