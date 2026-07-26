"""
Stage2 Figure Analysis Orchestrator (Phase 0)

Skeleton only: function signatures, docstrings, and basic logging.
No business logic implemented in Phase 0.

Planned pipeline:
- figure plan -> figure code -> figure execute -> figure review -> figure analysis

Subsequent phases will incrementally implement each stage.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess
import sys
import re
import time
import random

# Common Utils
try:
    from .common import setup_sys_path, resolve_project_paths, logger
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from common import setup_sys_path, resolve_project_paths, logger

setup_sys_path()


from .common import get_common_model_name, get_plot_model_name, get_model_config_path


def _log(level: str, msg: str) -> None:
    # Wrapper for compatibility with existing calls, but using common logger
    lvl = (level or "INFO").upper()
    if lvl == "INFO":
        logger.info(f"stage2 - {msg}")
    elif lvl in ("WARN", "WARNING"):
        logger.warning(f"stage2 - {msg}")
    elif lvl == "ERROR":
        logger.error(f"stage2 - {msg}")
    else:
        logger.debug(f"stage2 - {msg}")


def get_paths_and_env(project_name: str, overrides: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    paths = resolve_project_paths(project_name, overrides)
    # Set environment variables for downstream tools compatibility
    try:
        os.environ["STAGE1_PROCESSED_DIR"] = str(Path(paths["processed_dir"]).absolute())
        os.environ["STAGE1_OUTPUTS_DIR"] = str(Path(paths["figures_dir"]).absolute())
    except Exception:
        pass
    return paths


def stage2_plan(project_name: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Stage2 - Figure Plan
    调用选图规划代理，生成方案与规范落盘，并进行自测校验。
    """
    paths = get_paths_and_env(project_name)
    cfg = cfg or {}
    if "config_name" not in cfg:
        cfg["config_name"] = get_common_model_name()
    
    # import planning agent
    try:
        from researcher.analysis.agent.figures.figure_plan_agent import plan_figures as _plan_figures
    except ImportError:
        try:
             from src.researcher.analysis.agent.figures.figure_plan_agent import plan_figures as _plan_figures
        except ImportError as e:
            _plan_figures = None
            _log("WARN", f"plan_figures import failed: {e}")

    result: Dict[str, Any] = {}
    if _plan_figures is not None:
        try:
            # Check for Stage 1.5 Analysis Plan first
            analysis_plan_path = Path(paths.get("analysis_plan", ""))
            if analysis_plan_path.exists():
                _log("INFO", f"using analysis plan from {analysis_plan_path}")
                with analysis_plan_path.open("r", encoding="utf-8") as f:
                    analysis_plan = json.load(f)
                
                # Pass analysis_items directly if available
                if "analysis_items" in analysis_plan:
                    cfg["analysis_items"] = analysis_plan["analysis_items"]

            result = _plan_figures(paths, cfg)
        except Exception as e:
            _log("WARN", f"plan_figures call failed: {e}; using local fallback")
            result = {}
    
    if not result.get("written_files"):
        _log("INFO", "using local fallback plan")
        outputs_dir = Path(paths["outputs_dir"]).absolute()
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        processed_dir = Path(paths["processed_dir"]).absolute()
        candidates: List[Path] = []
        try:
            if processed_dir.exists():
                for p in sorted(processed_dir.glob("*.json")):
                    candidates.append(p)
        except Exception:
            pass

        def _mk_spec(i: int, data_path: Optional[Path]) -> Dict[str, Any]:
            return {
                "id": f"fallback_{i}",
                "title": f"Fallback Figure {i}",
                "data_source_category": "processed",
                "source_reference": str(data_path) if data_path else None,
                "group_by_fields": [],
                "aggregation": {"method": "mean", "field": None},
                "suggested_visualization_type": "line",
                "why_this_figure": "Local fallback due to missing analyzer_agent.",
            }
        
        specs: List[Dict[str, Any]] = []
        for i in range(1, 4):
            dp = candidates[i-1] if i-1 < len(candidates) else None
            specs.append(_mk_spec(i, dp))
            
        used_specs: List[Dict[str, Any]] = []
        for sp in specs:
            used = dict(sp)
            used["processed_dir"] = str(processed_dir)
            try:
                sr = used.get("source_reference")
                if isinstance(sr, str) and sr:
                    rp = Path(sr)
                    if rp.exists():
                        used["_resolved_data_path"] = str(rp.absolute())
            except Exception:
                pass
            used_specs.append(used)
            
        plan_obj = {
            "project_name": Path(paths["workflow_state"]).name, # fallback name logic?
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(used_specs),
            "specs": specs,
            "specs_used": used_specs,
        }
        plan_path = outputs_dir / "figure_plan.json"
        try:
            with plan_path.open("w", encoding="utf-8") as f:
                json.dump(plan_obj, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
        written_files = [str(plan_path)]
        for i, used in enumerate(used_specs, start=1):
            p2 = outputs_dir / f"fig{i}_spec_used.json"
            try:
                with p2.open("w", encoding="utf-8") as f:
                    json.dump(used, f, ensure_ascii=False, indent=2)
                written_files.append(str(p2))
            except Exception:
                pass
        result = {"outputs_dir": str(outputs_dir), "written_files": written_files}

    written_files = list(result.get("written_files", []))
    _log("INFO", f"written_files: {written_files}")

    # self-test: existence + JSON integrity
    ok_files: List[str] = []
    errors: List[str] = []
    for fp in written_files:
        try:
            p = Path(fp)
            if not p.exists():
                errors.append(f"missing: {fp}")
                continue
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                errors.append(f"not_object: {fp}")
                continue
            if p.name == "figure_plan.json":
                required = ["specs", "specs_used", "count"]
                missing = [k for k in required if k not in data]
                if missing:
                    errors.append(f"plan_missing: {missing}")
                else:
                    ok_files.append(fp)
            else:
                ok_files.append(fp)
        except Exception as e:
            errors.append(f"json_error: {fp}: {e}")

    summary = {"paths": paths, "written_files": written_files, "validation": {"ok": ok_files, "errors": errors}}
    _log("INFO", f"plan validation summary: {summary['validation']}")
    return summary


def stage2_generate_codes(specs_used: List[Dict[str, Any]], project_name: str, cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Stage2 - Figure Code Generation
    """
    try:
        from researcher.analysis.agent.figures.code_agent import gen_plot_code
    except ImportError:
        try:
            from src.researcher.analysis.agent.figures.code_agent import gen_plot_code
        except ImportError as e:
            gen_plot_code = None
            _log("WARN", f"import gen_plot_code failed: {e}")

    paths = get_paths_and_env(project_name)
    figures_dir = Path(paths["outputs_dir"]).absolute()
    stage2_tmp = figures_dir / "stage2_tmp"
    stage2_tmp.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []

    for i, spec in enumerate(specs_used, start=1):
        code_text: Optional[str] = None
        err_msg: str = ""

        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if gen_plot_code is not None:
                    code_text = gen_plot_code(spec)
                    if code_text:
                        break
                else:
                    raise RuntimeError("gen_plot_code unavailable")
            except Exception as e:
                err_msg = f"gen_plot_code failed (attempt {attempt+1}/{max_retries}): {e}"
                _log("WARN", err_msg)
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                else:
                    _log("ERROR", f"gen_plot_code permanently failed for fig{i}: {e}")

        # Fallback code
        if not code_text:
            code_text = (
                "import matplotlib\n"
                "import matplotlib.pyplot as plt\n"
                "import numpy as np\n"
                "plt.rcParams.update({'font.size':12,'figure.figsize':(6,4),'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':1.0,'axes.labelsize':12,'xtick.direction':'out','ytick.direction':'out'})\n"
                "x = np.arange(1,6)\n"
                "y = np.array([0.8,1.0,1.1,0.9,1.2])\n"
                "err = np.array([0.05,0.04,0.06,0.05,0.07])\n"
                "plt.errorbar(x,y,yerr=err,fmt='o-',capsize=3,linewidth=1.5,markersize=5,color='#2C7FB8')\n"
                "plt.xlabel('Time')\n"
                "plt.ylabel('Value')\n"
                "plt.title('Fallback Plot')\n"
                "plt.tight_layout()\n"
                "plt.show()\n"
            )

        # Patching
        try:
            has_matplotlib = ("import matplotlib" in code_text)
            has_plotly = ("import plotly" in code_text)
            has_show = ("plt.show()" in code_text)

            patched_lines: List[str] = []
            if not has_matplotlib and not has_plotly:
                patched_lines.append("import matplotlib.pyplot as plt")
            if not has_show:
                patched_lines.append("\n# ensure show for self-test\nplt.tight_layout()\nplt.show()")
            if patched_lines:
                code_text = ("\n".join(patched_lines) + "\n\n" + code_text)
        except Exception:
            pass

        # Write to disk
        code_path = stage2_tmp / f"gen_fig{i}.py"
        try:
            code_path.write_text(code_text, encoding="utf-8")
            _log("INFO", f"wrote -> {code_path}")
        except Exception as e:
            err_msg = err_msg or f"write code failed: {e}"
            _log("ERROR", err_msg)

        # Self-test
        selftest_ok = False
        try:
            text = code_path.read_text(encoding="utf-8") if code_path.exists() else ""
            non_empty = bool(text.strip())
            has_imp = ("import matplotlib" in text) or ("import plotly" in text)
            has_show2 = ("plt.show()" in text)
            selftest_ok = non_empty and has_imp and has_show2
            if not selftest_ok:
                miss = []
                if not non_empty: miss.append("empty")
                if not has_imp: miss.append("no matplotlib/plotly import")
                if not has_show2: miss.append("no plt.show()")
                err_msg = err_msg or ("selftest failed: " + ", ".join(miss))
        except Exception as e:
            err_msg = err_msg or f"selftest IO failed: {e}"

        if err_msg:
             try:
                 (stage2_tmp / f"gen_fig{i}.error.txt").write_text(err_msg, encoding="utf-8")
             except Exception:
                 pass

        results.append({
            "index": i,
            "code_path": str(code_path),
            "code_text": code_text,
            "selftest_ok": bool(selftest_ok),
            "error": err_msg,
        })

    _log("INFO", f"stage2_generate_codes done: {len(results)} items, tmp={stage2_tmp}")
    return results


def stage2_execute_codes(code_items: List[Dict[str, Any]], project_name: str, timeout_sec: int = 60, max_tries: int = 3) -> List[Dict[str, Any]]:
    paths = get_paths_and_env(project_name)
    figures_dir = Path(paths["outputs_dir"]).absolute()
    stage2_tmp = figures_dir / "stage2_tmp"
    stage2_tmp.mkdir(parents=True, exist_ok=True)

    try:
        from researcher.analysis.agent.figures.code_agent import patch_code as _patch_code
    except ImportError:
        try:
            from src.researcher.analysis.agent.figures.code_agent import patch_code as _patch_code
        except ImportError as e:
            _patch_code = None
            _log("WARN", f"import patch_code failed: {e}")

    # Clean old figures
    for p in figures_dir.glob("fig*.png"):
        try: p.unlink()
        except Exception: pass

    def _indent(code: str, spaces: int = 4) -> str:
        pad = " " * spaces
        return "\n".join(pad + line if line.strip() else line for line in code.splitlines())

    def _run_attempt(i: int, code_text: str, label: str, fig_path: Path, timeout_sec: int) -> tuple[bool, str, str, Path, Path]:
        stdout_path = stage2_tmp / (f"gen_fig{i}.{label}.stdout.txt" if label != "orig" else f"gen_fig{i}.stdout.txt")
        stderr_path = stage2_tmp / (f"gen_fig{i}.{label}.stderr.txt" if label != "orig" else f"gen_fig{i}.stderr.txt")
        run_path = stage2_tmp / (f"run_gen_fig{i}_{label}.py" if label != "orig" else f"run_gen_fig{i}.py")

        wrapper = (
            "import os, sys, traceback\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "OUTPUT_PNG = os.environ.get('STAGE2_OUTPUT_PNG')\n"
            "_stage2_saved = {'done': False}\n"
            "try:\n"
            "    import matplotlib.pyplot as plt\n"
            "    def _stage2_mpl_show(*args, **kwargs):\n"
            "        try:\n"
            "            nums = plt.get_fignums()\n"
            "            if nums:\n"
            "                fig = plt.figure(nums[-1])\n"
            "                path = OUTPUT_PNG or 'out.png'\n"
            "                fig.savefig(path, dpi=150, bbox_inches='tight')\n"
            "                _stage2_saved['done'] = True\n"
            "        except Exception:\n"
            "            pass\n"
            "    plt.show = _stage2_mpl_show\n"
            "except Exception:\n"
            "    pass\n"
            "try:\n"
            "    import plotly.io as pio\n"
            "    def _stage2_plotly_show(fig=None, *args, **kwargs):\n"
            "        try:\n"
            "            if fig is not None and hasattr(fig, 'write_image'):\n"
            "                path = OUTPUT_PNG or 'out.png'\n"
            "                fig.write_image(path, scale=2)\n"
            "                _stage2_saved['done'] = True\n"
            "        except Exception:\n"
            "            pass\n"
            "    pio.show = _stage2_plotly_show\n"
            "except Exception:\n"
            "    pass\n"
            "__stage2_error = None\n"
            "try:\n"
            f"{_indent(code_text)}\n"
            "except Exception as e:\n"
            "    __stage2_error = e\n"
            "    traceback.print_exc()\n"
            "saved = bool(_stage2_saved.get('done'))\n"
            "try:\n"
            "    if not saved:\n"
            "        import matplotlib.pyplot as plt\n"
            "        nums = plt.get_fignums()\n"
            "        if nums:\n"
            "            fig = plt.figure(nums[-1])\n"
            "            path = OUTPUT_PNG or 'out.png'\n"
            "            fig.savefig(path, dpi=150, bbox_inches='tight')\n"
            "            saved = True\n"
            "except Exception:\n"
            "    pass\n"
            "if __stage2_error:\n"
            "    sys.exit(1)\n"
            "if not saved and OUTPUT_PNG:\n"
            "    sys.exit(2)\n"
        )

        try:
            run_path.write_text(wrapper, encoding="utf-8")
        except Exception: pass

        # Clean existing before run
        try:
            if fig_path.exists(): fig_path.unlink()
        except Exception: pass

        env = os.environ.copy()
        env["STAGE2_OUTPUT_PNG"] = str(fig_path)
        
        try:
            cp = subprocess.run(
                [sys.executable, str(run_path)],
                cwd=str(stage2_tmp),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            so, se = (cp.stdout or ""), (cp.stderr or "")
            try:
                stdout_path.write_text(so, encoding="utf-8")
                stderr_path.write_text(se or "unknown error", encoding="utf-8")
            except Exception: pass
            
            success = (cp.returncode == 0) and fig_path.exists() and (fig_path.stat().st_size > 0)
            return success, so, (se or "execution failed"), stdout_path, stderr_path
        except subprocess.TimeoutExpired as e:
            so, se = (e.stdout or ""), ((e.stderr or "") + "\nTIMEOUT")
            try:
                stdout_path.write_text(so, encoding="utf-8")
                stderr_path.write_text(se, encoding="utf-8")
            except Exception: pass
            return False, so, se, stdout_path, stderr_path

    results: List[Dict[str, Any]] = []
    for i in range(1, len(code_items) + 1):
        item = code_items[i - 1] if i - 1 < len(code_items) else {}
        code_text = item.get("code_text")
        if not code_text:
            cp = item.get("code_path")
            try:
                if cp: code_text = Path(cp).read_text(encoding="utf-8")
            except Exception: pass
        if not code_text:
             # Fallback logic was already handled in generation, but safety check
             code_text = ""

        fig_path = figures_dir / f"fig{i}.png"
        
        # Original attempt
        success, so, se, stdout_p, stderr_p = _run_attempt(i, code_text, "orig", fig_path, timeout_sec)
        
        attempts_meta = [{"label": "orig", "success": bool(success), "stderr_path": str(stderr_p)}]
        patch_tries_done = 0

        # Patch logic
        if (not success) and (_patch_code is not None) and (max_tries > 0):
            for t in range(max_tries):
                try:
                    spec_path = figures_dir / f"fig{i}_spec_used.json"
                    if spec_path.exists():
                        patched_text = _patch_code(code_text, se, spec_file=str(spec_path))
                    else:
                        patched_text = _patch_code(code_text, se)
                except Exception as e:
                    _log("WARN", f"patch_code try {t+1} failed: {e}")
                    break
                
                try:
                    (stage2_tmp / f"gen_fig{i}.patch{t+1}.py").write_text(patched_text, encoding="utf-8")
                except Exception: pass

                success2, so2, se2, stdout_p2, stderr_p2 = _run_attempt(i, patched_text, f"patch{t+1}", fig_path, timeout_sec)
                attempts_meta.append({"label": f"patch{t+1}", "success": bool(success2), "stderr_path": str(stderr_p2)})
                patch_tries_done = t + 1

                if success2:
                    success, se = True, None
                    code_text = patched_text
                    stdout_p, stderr_p = stdout_p2, stderr_p2
                    break
                else:
                    se = se2

        size_info = fig_path.stat().st_size if fig_path.exists() else 0
        _log("INFO", f"[fig{i}] done -> {fig_path} (size={size_info} bytes) success={success}")

        results.append({
            "index": i,
            "figure_path": str(fig_path),
            "success": bool(success),
            "error": (se or ""),
            "code_text": code_text,
            "stderr_path": str(stderr_p),
            "patch_tries_done": patch_tries_done,
            "attempts": attempts_meta,
        })

    _log("INFO", f"stage2_execute_codes finished: {len(results)} items, tmp={stage2_tmp}")
    return results


def stage2_review_figures(project_name: str, prompt: Optional[str] = None, max_round: int = 1) -> Dict[str, Any]:
    """
    Stage2 - Figure Review & Regeneration
    """
    _log("INFO", f"stage2_review_figures(project_name={project_name}, max_round={max_round})")
    paths = get_paths_and_env(project_name)
    figures_dir = Path(paths["outputs_dir"]).absolute()
    stage2_tmp = figures_dir / "stage2_tmp"
    stage2_tmp.mkdir(parents=True, exist_ok=True)

    try:
        from researcher.analysis.agent.figures.figure_review_agent import FigureReviewAgent
        from researcher.analysis.agent.figures.code_agent import patch_code as _patch_code
    except ImportError:
        try:
            from src.researcher.analysis.agent.figures.figure_review_agent import FigureReviewAgent
            from src.researcher.analysis.agent.figures.code_agent import patch_code as _patch_code
        except ImportError as e:
            _log("ERROR", f"import failed: {e}")
            return {"status": "error", "error": str(e), "results": []}

    # Get existing figures
    fig_paths = []
    try:
        for p in figures_dir.glob("fig*.png"):
            m = re.match(r"^fig(\d+)\.png$", p.name)
            if m: fig_paths.append(p)
    except Exception: pass
    fig_paths.sort(key=lambda x: int(re.match(r"^fig(\d+)\.png$", x.name).group(1)))

    agent = FigureReviewAgent()

    # Reuse run logic? Or duplicate? For now reuse simplified version
    def _run_simple(code_text: str, fig_path: Path):
        # This is simplified. Should ideally reuse _run_attempt from execute_codes but it's nested there.
        # We can just inline logic or refactor. Inline for now.
        env = os.environ.copy()
        env["STAGE2_OUTPUT_PNG"] = str(fig_path)
        
        # We need to wrap user code to support savefig injection
        # Minimal wrapper
        wrapper = (
            "import os, sys, matplotlib\n"
            "matplotlib.use('Agg')\n"
            "OUTPUT_PNG = os.environ.get('STAGE2_OUTPUT_PNG')\n"
            "try:\n"
            "    import matplotlib.pyplot as plt\n"
            "    def _show(*args, **kwargs):\n"
            "        try:\n"
            "             plt.savefig(OUTPUT_PNG or 'out.png', bbox_inches='tight')\n"
            "        except: pass\n"
            "    plt.show = _show\n"
            "except: pass\n"
            f"{code_text}\n"
        )
        
        run_path = stage2_tmp / f"run_review_{fig_path.stem}.py"
        run_path.write_text(wrapper, encoding="utf-8")
        
        try:
             subprocess.run([sys.executable, str(run_path)], env=env, cwd=str(stage2_tmp), timeout=60, capture_output=True)
             return fig_path.exists() and fig_path.stat().st_size > 0
        except:
             return False

    results = []
    for p in fig_paths:
        i = int(re.match(r"^fig(\d+)\.png$", p.name).group(1))
        review_json_path = p.with_name(f"fig{i}.review.json")
        
        try:
            review = agent.review_image_json(str(p), prompt or "Review for improvements.")
        except Exception as e:
            review = {"action": "keep", "issues": [str(e)]}

        # Save review
        try:
            review_json_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
        except: pass
        
        action = str(review.get("action", "keep")).lower()
        regen_success = False
        code_changed = False
        regen_code_path = stage2_tmp / f"gen_fig{i}.review.py"

        if action == "abort":
             try: p.unlink()
             except: pass
        elif action != "keep":
             # Try regen
             # ... simplified regen logic ...
             pass
        
        results.append({
            "index": i,
            "action": action,
            "regen_success": regen_success
        })

    return {"results": results}


def stage2_analyze_figures(project_name: str, workflow_state_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Stage2 - Figure Analysis
    """
    _log("INFO", f"stage2_analyze_figures(project_name={project_name})")
    paths = get_paths_and_env(project_name)
    figures_dir = Path(paths["outputs_dir"]).absolute()

    try:
        from researcher.analysis.agent.figures.explainer_agent import ExplainerAgent
    except ImportError:
        try:
            from src.researcher.analysis.agent.figures.explainer_agent import ExplainerAgent
        except ImportError as e:
            _log("ERROR", f"import ExplainerAgent failed: {e}")
            return {"status": "error"}

    # Load workflow state
    workflow_state = {}
    try:
        ws_path = Path(workflow_state_path or paths.get("workflow_state") or "")
        if ws_path.exists():
            with ws_path.open("r", encoding="utf-8") as f:
                workflow_state = json.load(f)
        else:
             workflow_state = {"project_name": project_name}
    except Exception:
        workflow_state = {"project_name": project_name}

    # Collect figures
    fig_paths = []
    try:
        for p in figures_dir.glob("fig*.png"):
             if re.match(r"^fig(\d+)\.png$", p.name):
                 fig_paths.append(p)
    except Exception: pass
    fig_paths.sort(key=lambda x: int(re.match(r"^fig(\d+)\.png$", x.name).group(1)))

    if not fig_paths:
         _log("WARN", f"No figures found in {figures_dir}")
         # fallback?
         fig_paths = [figures_dir / f"fig{i}.png" for i in range(1, 4)]

    # Build summaries
    fig_summaries = []
    for p in fig_paths:
        i = None
        m = re.match(r"^fig(\d+)\.png$", p.name)
        if m: i = int(m.group(1))
        
        spec_used = {}
        candidates = []
        if i: candidates.append(figures_dir / f"fig{i}_spec_used.json")
        candidates.append(figures_dir / f"{p.stem}_spec_used.json")
        
        for c in candidates:
            if c.exists():
                try: 
                    spec_used = json.loads(c.read_text(encoding="utf-8"))
                    break
                except: pass
        
        title = spec_used.get("title") or p.stem.replace("_", " ").title()
        summary_txt = spec_used.get("why_this_figure")
        referenced = []
        sr = spec_used.get("source_reference")
        if sr and isinstance(sr, str):
             referenced.append(Path(sr).name)
        
        fig_summaries.append({
            "id": p.stem,
            "title": title,
            "figure_path": str(p),
            "referenced_data": referenced,
            "summary": summary_txt
        })
    
    agent = ExplainerAgent()
    result_json_str = ""
    try:
        result_json_str = agent.explain(fig_summaries, workflow_state)
    except Exception as e:
        _log("ERROR", f"ExplainerAgent.explain failed: {e}")
    
    out_path = figures_dir / "fig_explanations.json"
    data_obj = {}
    if result_json_str:
        try: data_obj = json.loads(result_json_str)
        except: pass
    
    # Try reading if agent failed but file exists (maybe agent wrote it?)
    if not data_obj and out_path.exists():
        try: data_obj = json.loads(out_path.read_text(encoding="utf-8"))
        except: pass

    return {
        "status": "ok" if data_obj else "partial",
        "project_name": project_name,
        "written_path": str(out_path) if out_path.exists() else None,
        "count_figures": len(fig_summaries)
    }


def stage2_summarize_figures(project_name: str, specs_used: List[Dict[str, Any]], exec_results: List[Dict[str, Any]], review_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Stage2 - Figure Summary Generation
    """
    paths = get_paths_and_env(project_name)
    outputs_dir = Path(paths["outputs_dir"]).absolute()
    
    figures_list = []
    for i, spec in enumerate(specs_used, start=1):
        figures_list.append({
            "id": spec.get("id", f"fig{i}"),
            "index": i,
            "title": spec.get("title"),
        })

    summary_data = {
        "project_name": project_name,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "figures": figures_list
    }
    
    summary_path = outputs_dir / "figures_summary.json"
    try:
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    return {"path": str(summary_path), "data": summary_data}


def stage2_run(project_name: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Stage2 - Orchestrator Entry
    """
    opts = options or {}
    paths = get_paths_and_env(project_name)

    # 1) Plan（使用通用模型）
    plan_cfg = {"config_name": get_common_model_name()}
    plan_summary = stage2_plan(project_name, cfg=plan_cfg)
    specs_used = plan_summary.get("specs_used") or []
    
    if not specs_used:
         # Fallback load
         try:
             plan_path = Path(paths["outputs_dir"]) / "figure_plan.json"
             if plan_path.exists():
                 specs_used = json.loads(plan_path.read_text(encoding="utf-8")).get("specs_used", [])
         except: pass

    # 2) Code（使用绘图模型；具体模型由 code_agent 内部按环境变量解析）
    code_cfg = {"config_name": get_plot_model_name()}
    code_items = stage2_generate_codes(specs_used, project_name, cfg=code_cfg)

    # 3) Execute
    exec_results = stage2_execute_codes(code_items, project_name)

    # 4) Review
    review_summary = {}
    if opts.get("with_review"):
        review_summary = stage2_review_figures(project_name, max_round=opts.get("max_round", 1))

    # 5) Summarize
    summary_result = stage2_summarize_figures(project_name, specs_used, exec_results, review_summary)

    # 6) Analyze
    analyze_summary = {}
    if opts.get("with_analysis"):
        analyze_summary = stage2_analyze_figures(project_name)

    result = {
        "project_name": project_name,
        "phase": 4,
        "plan": plan_summary,
        "code": {"items": code_items},
        "execute": {"results": exec_results},
        "review": review_summary,
        "summary": summary_result,
        "analyze": analyze_summary,
    }
    _log("INFO", "stage2_run completed")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stage2 Figure Analysis Orchestrator")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--with-review", action="store_true")
    parser.add_argument("--with-analysis", action="store_true")
    args = parser.parse_args(argv)

    result = stage2_run(
        project_name=args.project_name,
        options={"with_review": args.with_review, "with_analysis": args.with_analysis},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
