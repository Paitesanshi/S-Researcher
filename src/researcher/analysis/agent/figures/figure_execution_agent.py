import json
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time
import argparse
from loguru import logger

# 兼容导入：相对优先，其次绝对


@dataclass
class Stage1Paths:
    scene_info: Path
    workflow_state: Path
    processed_dir: Optional[Path] = None
    outputs_dir: Path = Path("outputs")


@dataclass
class Stage1Config:
    max_retries: int = 2
    run_timeout_sec: int = 60
    enable_fallback: bool = True


# -------------------------- Helpers (module-level) --------------------------

def _indent(code: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in code.splitlines())


def _run_python_script(code: str, output_png: Path, timeout_sec: int) -> Tuple[bool, str, str, Path]:
    """
    在临时脚本中运行给定 Python 代码，并尽力保存 matplotlib/plotly 最后一幅图到 output_png。
    返回 (success, stdout, stderr, script_path)
    """
    tmp_dir = output_png.parent / "stage1_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    script_path = tmp_dir / f"run_{output_png.stem}.py"

    wrapper = (
        "import os, sys, traceback\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "OUTPUT_PNG = os.environ.get('STAGE1_OUTPUT_PNG')\n"
        "# monkeypatch show() to auto-save\n"
        "_stage1_saved = {'done': False}\n"
        "try:\n"
        "    import matplotlib.pyplot as plt\n"
        "    def _stage1_mpl_show(*args, **kwargs):\n"
        "        try:\n"
        "            nums = plt.get_fignums()\n"
        "            if nums:\n"
        "                fig = plt.figure(nums[-1])\n"
        "                path = OUTPUT_PNG or 'out.png'\n"
        "                fig.savefig(path, dpi=150, bbox_inches='tight')\n"
        "                _stage1_saved['done'] = True\n"
        "        except Exception:\n"
        "            pass\n"
        "    plt.show = _stage1_mpl_show\n"
        "except Exception:\n"
        "    pass\n"
        "try:\n"
        "    import plotly.io as pio\n"
        "    def _stage1_plotly_show(fig=None, *args, **kwargs):\n"
        "        try:\n"
        "            if fig is not None and hasattr(fig, 'write_image'):\n"
        "                path = OUTPUT_PNG or 'out.png'\n"
        "                fig.write_image(path, scale=2)\n"
        "                _stage1_saved['done'] = True\n"
        "        except Exception:\n"
        "            pass\n"
        "    pio.show = _stage1_plotly_show\n"
        "except Exception:\n"
        "    pass\n"
        "__stage1_error = None\n"
        "try:\n"
        f"{_indent(code)}\n"
        "except Exception as e:\n"
        "    __stage1_error = e\n"
        "    traceback.print_exc()\n"
        "# try save via matplotlib when not saved\n"
        "saved = bool(_stage1_saved.get('done'))\n"
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
        "if __stage1_error:\n"
        "    sys.exit(1)\n"
        "if not saved and OUTPUT_PNG:\n"
        "    sys.exit(2)\n"
    )

    script_path.write_text(wrapper, encoding="utf-8")

    import subprocess

    env = os.environ.copy()
    env["STAGE1_OUTPUT_PNG"] = str(output_png)
    try:
        cp = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        success = cp.returncode == 0 and output_png.exists()
        return success, cp.stdout, cp.stderr, script_path
    except subprocess.TimeoutExpired as e:  # type: ignore[name-defined]
        return False, e.stdout or "", (e.stderr or "") + "\nTIMEOUT", script_path


def _safe_load_dataset(spec: Dict[str, Any], processed_dir: Optional[Path]) -> Optional[List[Dict[str, Any]]]:
    src = spec.get("source_reference")
    if not src:
        return None
    candidates: List[Path] = []
    try:
        p = Path(src)
        if p.is_file():
            candidates.append(p)
    except Exception:
        pass
    if processed_dir:
        candidates.append(processed_dir / str(src))
    for path in candidates:
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                data = json.loads(text)
                if isinstance(data, list):
                    return [d for d in data if isinstance(d, dict)]
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    return [d for d in data["data"] if isinstance(d, dict)]
            except Exception:
                continue
    return None


def _fallback_simple_plot(
    spec: Dict[str, Any],
    output_png: Path,
    csv_out: Path,
    processed_dir: Optional[Path],
) -> Tuple[bool, str]:
    """基于简单聚合绘制折线/柱状作为回退，同时导出 CSV。返回 (success, message)。"""
    data = _safe_load_dataset(spec, processed_dir)
    if not data:
        # 无数据，生成占位图片与空 CSV
        try:
            csv_out.write_text("", encoding="utf-8")
        except Exception:
            pass
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.figure(figsize=(6, 3))
            plt.text(0.5, 0.5, "No data for fallback", ha="center", va="center")
            plt.axis("off")
            output_png.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(str(output_png), dpi=150, bbox_inches="tight")
            plt.close("all")
            return True, "fallback placeholder"
        except Exception as e:
            return False, f"fallback placeholder failed: {e}"

    group_by = spec.get("group_by_fields") or []
    if not isinstance(group_by, list):
        group_by = []
    agg = spec.get("aggregation") or {}
    method = (agg.get("method") or "count").lower()
    field = agg.get("field")

    # 简单聚合：生成 (group_keys..., value)
    table: Dict[Tuple[Any, ...], float] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        key = tuple(row.get(k) for k in group_by) if group_by else ("all",)
        if method == "mean" and field in row:
            # 先累加与计数
            val = float(row.get(field)) if row.get(field) is not None else 0.0
            if key not in table:
                table[key] = (val, 1.0)  # type: ignore[assignment]
            else:
                s, c = table[key]  # type: ignore[misc]
                table[key] = (s + val, c + 1.0)  # type: ignore[assignment]
        elif method == "sum" and field in row:
            val = float(row.get(field)) if row.get(field) is not None else 0.0
            table[key] = table.get(key, 0.0) + val  # type: ignore[assignment]
        else:
            # 默认 count
            table[key] = table.get(key, 0.0) + 1.0  # type: ignore[assignment]

    # 均值后处理
    if method == "mean":
        post: Dict[Tuple[Any, ...], float] = {}
        for k, v in table.items():
            if isinstance(v, tuple) and len(v) == 2:
                s, c = v
                post[k] = (s / max(c, 1.0)) if c else 0.0
            else:
                try:
                    post[k] = float(v)
                except Exception:
                    post[k] = 0.0
        table = post  # type: ignore[assignment]

    # 导出 CSV
    try:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        with csv_out.open("w", encoding="utf-8") as f:
            header = list(group_by) + ["value"]
            f.write(",".join(map(str, header)) + "\n")
            for k, v in sorted(table.items(), key=lambda kv: kv[0]):
                row = list(k) + [v]  # type: ignore[list-item]
                f.write(",".join(map(str, row)) + "\n")
    except Exception:
        pass

    # 绘制简单图
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        output_png.parent.mkdir(parents=True, exist_ok=True)
        # 针对 step/time 字段进行数值排序而非字典序
        first_dim = (group_by[0].lower() if group_by and isinstance(group_by[0], str) else None)
        numeric_x = first_dim in {"step", "time", "t", "round"}

        def _num_key_from_value(val: Any):
            if isinstance(val, (int, float)):
                return (0, float(val), str(val))
            s = str(val)
            digits = "".join(ch for ch in s if ch.isdigit())
            if digits:
                try:
                    return (0, float(digits), s)
                except Exception:
                    return (0, 0.0, s)
            # 无数字时，使用次序权重放在数字之后，并以原字符串作为次排序键
            return (1, float("inf"), s)

        if len(group_by) <= 1:
            # 单维度：x 为该维或 'all'
            xs: List[str] = []
            ys: List[float] = []
            if numeric_x:
                sorter = lambda kv: _num_key_from_value(kv[0][0] if isinstance(kv[0], tuple) else kv[0])
            else:
                sorter = lambda kv: kv[0]
            for k, v in sorted(table.items(), key=sorter):
                xs.append(str(k[0]))
                ys.append(float(v))
            vis = (spec.get("suggested_visualization_type") or "line").lower()
            plt.figure(figsize=(6, 4))
            if vis == "bar":
                plt.bar(xs, ys)
            else:
                plt.plot(xs, ys, marker="o")
            plt.title(spec.get("title") or spec.get("id") or "Figure")
            plt.tight_layout()
            plt.savefig(str(output_png), dpi=150)
            plt.close("all")
            return True, "fallback simple 1D"
        else:
            # 双维：按第二维分组，x 为第一维
            if numeric_x:
                dim1 = sorted({k[0] for k in table.keys()}, key=_num_key_from_value)
            else:
                dim1 = sorted({k[0] for k in table.keys()})
            dim2 = sorted({k[1] for k in table.keys()})
            plt.figure(figsize=(7, 4))
            for g in dim2:
                ys: List[float] = []
                for x in dim1:
                    ys.append(float(table.get((x, g), 0.0)))
                plt.plot(list(map(str, dim1)), ys, marker="o", label=str(g))
            plt.legend(title=str(group_by[1]))
            plt.title(spec.get("title") or spec.get("id") or "Figure")
            plt.tight_layout()
            plt.savefig(str(output_png), dpi=150)
            plt.close("all")
            return True, "fallback simple 2D"
    except Exception as e:
        return False, f"fallback plot failed: {e}"


# -------------------------- Agent Class --------------------------

class PlotExecutionAgent:
    """
    执行代理：简化为仅执行现有脚本
    - 仅运行 stage1_tmp/run_fig{i}.py（若存在）
    - 返回三张 PNG 的绝对路径列表
    """

    def run(self, paths: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> List[Path]:
        # 解析路径与配置（保留日志）
        scene_info = Path(paths.get("scene_info"))
        workflow_state = Path(paths.get("workflow_state"))
        processed_dir = Path(paths.get("processed_dir")) if paths.get("processed_dir") else None
        outputs_dir = Path(paths.get("outputs_dir") or "outputs").absolute()
        outputs_dir.mkdir(parents=True, exist_ok=True)

        conf = Stage1Config(**(cfg or {}))

        try:
            logger.add(str(outputs_dir / "stage1.log"), rotation="1 MB", enqueue=True, backtrace=False, diagnose=False, level="INFO")
        except Exception:
            pass
        logger.info("Stage1 start. outputs_dir={}", outputs_dir)
        logger.info(f"ENV: ONESIM_MODEL_NAME={os.environ.get('ONESIM_MODEL_NAME')} ONESIM_MODEL_CONFIG={os.environ.get('ONESIM_MODEL_CONFIG')}")
        logger.info(f"scene_info={scene_info}")
        logger.info(f"workflow_state={workflow_state}")
        if processed_dir:
            logger.info(f"processed_dir={processed_dir}")
            try:
                os.environ["STAGE1_PROCESSED_DIR"] = str(processed_dir)
            except Exception:
                pass

        # 固定图片输出与临时脚本目录
        figures_dir = outputs_dir
        stage_tmp_dir = figures_dir / "stage1_tmp"
        stage_tmp_dir.mkdir(parents=True, exist_ok=True)

        # 产物目标路径（仅 PNG）
        fig_paths = [figures_dir / f"fig{i}.png" for i in range(1, 4)]
        for p in fig_paths:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        # only execute run_fig{i}
        results: List[Path] = []
        for i in range(3):
            fig_path = fig_paths[i]
            last_err_out = ""
            logger.info(f"[fig{i+1}] begin")

            try:
                run_file = stage_tmp_dir / f"run_fig{i+1}.py"
                if run_file.exists():
                    text = run_file.read_text(encoding="utf-8")
                    ok2, so2, se2, _ = _run_python_script(text, fig_path, conf.run_timeout_sec)
                    (stage_tmp_dir / f"run_fig{i+1}.stdout.txt").write_text(so2 or "", encoding="utf-8")
                    (stage_tmp_dir / f"run_fig{i+1}.stderr.txt").write_text(se2 or "", encoding="utf-8")
                    if ok2:
                        logger.info(f"[fig{i+1}] run_fig script success -> {fig_path}")
                    else:
                        last_err_out = se2 or last_err_out
                        logger.warning(f"[fig{i+1}] run_fig script failed\n{(se2 or '')[:800]}")
                else:
                    last_err_out = "run_fig script not found"
                    logger.warning(f"[fig{i+1}] run_fig script not found -> {run_file}")
            except Exception as e:
                logger.warning(f"[fig{i+1}] executing run_fig failed: {e}")

            if not fig_path.exists():
                try:
                    (stage_tmp_dir / f"fig{i+1}_failed.txt").write_text(last_err_out or "unknown error", encoding="utf-8")
                except Exception:
                    pass
                logger.info(f"[fig{i+1}] no image produced; error saved")

            results.append(fig_path)
            try:
                size_info = fig_path.stat().st_size if fig_path.exists() else 0
            except Exception:
                size_info = 0
            logger.info(f"[fig{i+1}] done -> {fig_path} (size={size_info} bytes)")

        logger.info("Stage1 simplified done.")
        return results


# -------------------------- Compatibility API --------------------------

__all__ = ["run_stage1", "PlotExecutionAgent", "Stage1Paths", "Stage1Config"]


def run_stage1(paths: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> List[Path]:
    agent = PlotExecutionAgent()
    return agent.run(paths, cfg)


# -------------------------- CLI --------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Figure Execution Agent (Stage1 replacement)")
    parser.add_argument("--scene-info", dest="scene_info", help="Path to scene_info.json")
    parser.add_argument("--workflow-state", dest="workflow_state", help="Path to workflow_state.json")
    parser.add_argument("--processed-dir", dest="processed_dir", help="Processed data directory", default=None)
    parser.add_argument("--outputs-dir", dest="outputs_dir", help="Outputs directory (default: outputs)", default=os.environ.get("STAGE1_OUTPUTS_DIR", "outputs"))
    parser.add_argument("--max-retries", type=int, default=int(os.environ.get("STAGE1_MAX_RETRIES", "2")))
    parser.add_argument("--run-timeout-sec", type=int, default=int(os.environ.get("STAGE1_RUN_TIMEOUT", "60")))
    parser.add_argument("--disable-fallback", action="store_true", help="Disable fallback simple plot and CSV export")
    parser.add_argument("--code-path", dest="code_path", default=None, help="Path to a Python plotting script to run directly")

    args = parser.parse_args(argv)

    # if provided code path then go to test entry
    if args.code_path:
        try:
            code_path = Path(args.code_path)
            code_text = code_path.read_text(encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"Failed to read code path: {e}\n")
            return 2
        figures_dir = Path(args.outputs_dir).absolute()
        stage_tmp_dir = figures_dir / "stage1_tmp"
        try:
            stage_tmp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        fig_path = figures_dir / "fig1.png"
        try:
            if fig_path.exists():
                fig_path.unlink()
        except Exception:
            pass
        ok, so, se, _ = _run_python_script(code_text, fig_path, args.run_timeout_sec)
        try:
            (stage_tmp_dir / f"{code_path.stem}.stdout.txt").write_text(so or "", encoding="utf-8")
            (stage_tmp_dir / f"{code_path.stem}.stderr.txt").write_text(se or "", encoding="utf-8")
        except Exception:
            pass
        if ok and fig_path.exists():
            print(str(fig_path.absolute()))
            return 0
        else:
            try:
                (stage_tmp_dir / f"{code_path.stem}_failed.txt").write_text(se or "unknown error", encoding="utf-8")
            except Exception:
                pass
            sys.stderr.write("Execution failed; error saved.\n")
            return 1

    scene_info = args.scene_info or os.environ.get("SCENE_INFO_PATH")
    workflow_state = args.workflow_state or os.environ.get("WORKFLOW_STATE_PATH")
    processed_dir = args.processed_dir or os.environ.get("PROCESSED_DIR")
    outputs_dir = args.outputs_dir

    if not scene_info or not workflow_state:
        sys.stderr.write("--scene-info and --workflow-state are required (or set SCENE_INFO_PATH/WORKFLOW_STATE_PATH)\n")
        return 2

    paths = {
        "scene_info": scene_info,
        "workflow_state": workflow_state,
        "processed_dir": processed_dir,
        "outputs_dir": outputs_dir,
    }
    cfg = {
        "max_retries": args.max_retries,
        "run_timeout_sec": args.run_timeout_sec,
        "enable_fallback": not args.disable_fallback,
    }

    try:
        figs = run_stage1(paths, cfg)
        for p in figs:
            print(str(Path(p).absolute()))
        return 0
    except Exception as e:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
