import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from researcher.analysis.common import resolve_project_paths

try:
    from ..llm.agent_client import SimpleChatLLM
except Exception:
    from src.researcher.analysis.agent.agent_client import SimpleChatLLM  # type: ignore


class ExplainerAgent:
    """
    Generate concise, structured explanations for three figures based on their
    summary metadata and the workflow_state context.

    - Input: fig_summaries (list[dict]), workflow_state (dict)
    - Output: JSON string with per-figure: phenomenon -> key_values -> conclusion
    - Side-effect: writes the JSON to fig_explanations.json under outputs dir
      resolved by env STAGE1_OUTPUTS_DIR or default ./outputs
    """

    def __init__(
        self,
        config_name: Optional[str] = None,
        config_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        cfg_name = (config_name or os.environ.get("ANALYSIS_PLOT_MODEL_NAME") or os.environ.get("ONESIM_PLOT_MODEL_NAME") or os.environ.get("STAGE2_PLOT_MODEL_NAME") or os.environ.get("ONESIM_MODEL_NAME") or "claude-sonnet-4-5-20250929").strip()
        if cfg_name == "openai-gpt4o":
            cfg_name = "gpt-4o"
        cfg_path = (
            config_path
            or os.environ.get("ONESIM_MODEL_CONFIG")
            or "config/model_config.json"
        )
        try:
            self.llm = SimpleChatLLM(config_name=cfg_name, config_path=cfg_path)
        except Exception:
            self.llm = None  # type: ignore
        self.system_prompt = (
            system_prompt
            or (
                "You are a research explainer agent. Given workflow context and "
                "three figure summaries, produce a JSON-only analysis capturing, "
                "for each figure: the main phenomenon observed, key numeric values "
                "(as label/value pairs), and a concise conclusion tied to the "
                "research question. Do not include markdown or extra text."
            )
        )
        self._llm_enabled = bool(getattr(self.llm, "client", None))

    def explain(self, fig_summaries: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> str:
        out_dir = self._resolve_outputs_dir()
        import time
        log_file = out_dir / "explainer_agent.log"
        def _log(level: str, msg: str) -> None:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            cleaned = str(msg).rstrip("\n")
            line = f"{ts} | {level:<8} | explainer - {cleaned}"
            try:
                print(line)
            except Exception:
                pass
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                with log_file.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

        _log("INFO", f"Explain start: outputs_dir={out_dir}")

        fig_path: Optional[str] = None
        if isinstance(fig_summaries, list) and fig_summaries:
            fp = fig_summaries[0].get("figure_path")
            if isinstance(fp, str) and fp.strip():
                fig_path = fp
        if not fig_path:
            default_dir = out_dir
            candidate = default_dir / "fig1.png"
            if candidate.exists():
                fig_path = str(candidate)
            else:
                _log("WARNING", f"Figure path not provided and default not found: {candidate}")

        spec: Optional[Dict[str, Any]] = None
        data_path: Optional[str] = None
        if fig_path:
            spec = self._resolve_spec_for_figure(fig_path)
            if spec:
                data_path = self._resolve_data_path_from_spec(spec)
                _log("DEBUG", f"Resolved spec for figure: data_path={data_path}")
            else:
                _log("WARNING", f"No spec_used json found for figure: {fig_path}")

        data: Optional[Dict[str, Any]] = None
        if self._llm_enabled:
            try:
                ws_brief = self._brief_workflow(workflow_state)
                dataset_summary = self._summarize_dataset(data_path) if isinstance(data_path, str) else {"status": "no_data_path"}
                instruction_text = self._build_multimodal_instruction(workflow_state, spec, fig_path)

                content_parts: List[Dict[str, Any]] = [
                    {"type": "text", "text": instruction_text},
                    {"type": "text", "text": "workflow_state_brief:\n" + json.dumps(ws_brief, ensure_ascii=False, indent=2)},
                ]
                if spec:
                    content_parts.append({"type": "text", "text": "figure_spec_used:\n" + json.dumps(spec, ensure_ascii=False, indent=2)})
                if dataset_summary:
                    content_parts.append({"type": "text", "text": "dataset_summary:\n" + json.dumps(dataset_summary, ensure_ascii=False, indent=2)})

                _log("DEBUG", f"Multimodal parts count={len(content_parts)} | image_path_set={bool(fig_path)}")
                data = self.llm.chat_multimodal_json(  # type: ignore[attr-defined]
                    user_text="",
                    image_paths=([fig_path] if fig_path else None),
                    system_prompt="Return ONLY valid JSON that matches the figure_analysis schema. No markdown or explanations.",
                    temperature=0.2,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                    content_parts=content_parts,
                )
                _log("INFO", "LLM multimodal JSON returned.")
            except Exception as e:
                _log("ERROR", f"Multimodal chat failed: {e}")
        else:
            _log("WARNING", "LLM unavailable; using fallback builder")
            data = None

        if not isinstance(data, dict):
            if self._llm_enabled:
                _log("WARNING", "Multimodal parse failed; falling back to text-only prompt.")
                prompt = self._build_prompt(fig_summaries, workflow_state)
                _log("DEBUG", f"Prompt length={len(prompt)}")
                try:
                    raw = self.llm.chat(user_query=prompt, system_prompt=self.system_prompt)  # type: ignore[attr-defined]
                    _log("INFO", f"LLM chat returned length={len(raw)}")
                    data = self._parse_json_strict(raw)
                    if not data:
                        _log("WARNING", "Initial parse failed; attempting repair prompt")
                        repair_prompt = self._build_repair_prompt(fig_summaries, workflow_state, raw)
                        raw = self.llm.chat(user_query=repair_prompt, system_prompt=self.system_prompt)  # type: ignore[attr-defined]
                        _log("INFO", f"Repair chat returned length={len(raw)}")
                        data = self._parse_json_strict(raw)
                except Exception as e:
                    _log("ERROR", f"Text-only chat failed: {e}")
                    data = None
            else:
                data = None

        if not isinstance(data, dict):
            _log("WARNING", "Repair/LLM parse failed; building fallback JSON")
            data = self._fallback_build(fig_summaries, workflow_state)

        if (not fig_summaries) and fig_path:
            stem = Path(fig_path).stem
            fig_summaries = [{
                "id": stem,
                "title": stem.replace("_", " ").title(),
                "figure_path": fig_path,
                "referenced_data": ([Path(data_path).name] if data_path else []),
                "summary": (spec.get("why_this_figure") if isinstance(spec, dict) else None),
            }]

        data = self._normalize_to_figure_analysis_schema(data, fig_summaries or [], workflow_state)
        _log("DEBUG", "Normalized analysis schema")

        out_path = self._resolve_outputs_dir() / "fig_explanations.json"
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            _log("INFO", f"Wrote fig_explanations.json -> {out_path}")
        except Exception as e:
            _log("ERROR", f"Failed to write fig_explanations.json: {e}")
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _resolve_spec_for_figure(self, figure_path: str) -> Optional[Dict[str, Any]]:
        try:
            fig = Path(figure_path)
            fig_dir = fig.parent
            stem = fig.stem
            candidates = [
                fig_dir / f"{stem}_spec_used.json",
                fig_dir / "fig1_spec_used.json",
                fig_dir / f"{stem}_spec.json",
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    with c.open("r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception:
            return None
        return None

    def _resolve_data_path_from_spec(self, spec: Dict[str, Any]) -> Optional[str]:
        def _as_path(p: Optional[str]) -> Optional[str]:
            if isinstance(p, str) and Path(p).exists():
                return str(Path(p).absolute())
            return None
        for k in ("applyto", "apply_to", "dataset_path", "data_path", "_resolved_data_path"):
            p = spec.get(k)
            if isinstance(p, str):
                resolved = _as_path(p)
                if resolved:
                    return resolved
        proc = spec.get("processed_dir")
        src = spec.get("source_reference")
        if isinstance(proc, str) and isinstance(src, str):
            candidate = Path(proc) / src
            if candidate.exists():
                return str(candidate.absolute())
        return None

    def _summarize_dataset(self, data_path: Optional[str], max_records: int = 10) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"path": data_path, "status": "unavailable"}
        if not data_path:
            return summary
        try:
            p = Path(data_path)
            summary["exists"] = p.exists()
            summary["size_bytes"] = p.stat().st_size if p.exists() else None
            if p.suffix.lower() == ".json" and p.exists():
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    head = data[:max_records]
                    summary.update({
                        "status": "ok",
                        "type": "list",
                        "length": len(data),
                        "head": head,
                    })
                elif isinstance(data, dict):
                    keys = list(data.keys())
                    sample_keys = keys[:max_records]
                    sample_values = [data[k] for k in sample_keys]
                    summary.update({
                        "status": "ok",
                        "type": "dict",
                        "keys_count": len(keys),
                        "sample": [{"key": k, "value": sample_values[i]} for i, k in enumerate(sample_keys)],
                    })
                else:
                    summary.update({"status": "loaded", "type": type(data).__name__})
        except Exception as e:
            summary["error"] = str(e)
        return summary

    def _build_multimodal_instruction(self, workflow_state: Dict[str, Any], spec: Optional[Dict[str, Any]], figure_path: Optional[str]) -> str:
        rq = workflow_state.get("research_question") or workflow_state.get("research_topic") or workflow_state.get("question")
        project_name = workflow_state.get("project_name") or workflow_state.get("project") or ""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        format_example = {
            "project_name": project_name,
            "analysis_title": "Figure-grounded analysis and conclusions",
            "generated_at": now,
            "research_paradigm": "attribution_analysis",
            "research_question": rq,
            "scenario_description": workflow_state.get("scenario_description") or "A brief description of the simulation scenario and variables under study.",
            "figures_analyzed": [
                {
                    "name": (spec.get("title") if isinstance(spec, dict) else "Figure"),
                    "file": (Path(figure_path).name if figure_path else "fig1.png"),
                    "summary": (spec.get("why_this_figure") if isinstance(spec, dict) else "A short summary connected to the research question."),
                    "referenced_data": [spec.get("source_reference")] if isinstance(spec, dict) and spec.get("source_reference") else []
                }
            ],
            "groups_included": [],
            "key_findings": [],
            "metrics_citations": {},
            "supporting_evidence_notes": [],
            "limitations": [],
            "recommendations": [],
            "data_sources": [spec.get("source_reference")] if isinstance(spec, dict) and spec.get("source_reference") else [],
            "paths": {
                "figures_dir": "analysis/figures",
                "data_processed_dir": (spec.get("processed_dir") if isinstance(spec, dict) else "analysis/data/processed"),
            },
            "version": 2
        }
        constraints = [
            "Output STRICT JSON only. No extra text or markdown.",
            "Top-level keys: project_name, analysis_title, generated_at, research_paradigm, research_question, scenario_description, figures_analyzed, groups_included, key_findings, metrics_citations, supporting_evidence_notes, limitations, recommendations, data_sources, paths, version.",
            "Interpret the attached image together with the spec and dataset summary.",
            "Keep language concise, factual, and tied to the research_question.",
        ]
        instruction = {
            "task": "Produce analysis JSON matching scripts/figure_analysis.json structure for ONE figure.",
            "constraints": constraints,
            "format_example": format_example,
        }
        return "Generate JSON only. No explanations outside JSON.\n" + json.dumps(instruction, ensure_ascii=False, indent=2)

    def _build_prompt(self, fig_summaries: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> str:
        rq = (
            workflow_state.get("research_question")
            or workflow_state.get("research_topic")
            or workflow_state.get("question")
        )
        project_name = (
            workflow_state.get("project_name")
            or workflow_state.get("project")
            or ""
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        guide: Dict[str, Any] = {
            "task": "Produce analysis JSON matching scripts/figure_analysis.json structure exactly.",
            "constraints": [
                "Output STRICT JSON only. No extra text or markdown.",
                "Top-level keys (and order if possible): project_name, analysis_title, generated_at, research_paradigm, research_question, scenario_description, figures_analyzed, groups_included, key_findings, metrics_citations, supporting_evidence_notes, limitations, recommendations, data_sources, paths, version.",
                "figures_analyzed: array of 3 objects with keys: name, file, summary, referenced_data (array of strings).",
                "Keep language concise, factual, grounded in provided workflow_state and figure summaries.",
                "If specific numeric values are not available, provide qualitative but non-trivial summaries consistent with the research question.",
            ],
            "defaults": {
                "analysis_title": "Figure-grounded analysis and conclusions",
                "research_paradigm": "attribution_analysis",
                "paths": {
                    "figures_dir": "analysis/figures",
                    "data_processed_dir": "analysis/data/processed"
                },
                "version": 2
            },
            "format_example": {
                "project_name": project_name,
                "analysis_title": "Figure-grounded analysis and conclusions",
                "generated_at": now,
                "research_paradigm": "attribution_analysis",
                "research_question": rq,
                "scenario_description": "One to two sentences summarizing the simulation scenario.",
                "figures_analyzed": [
                    {
                        "name": "Average Cultural Regions",
                        "file": "avg_cultural_regions.png",
                        "summary": "A short summary of what this figure shows and the pattern.",
                        "referenced_data": ["Number_of_Cultural_Regions_all_groups.json"]
                    }
                ],
                "groups_included": [],
                "key_findings": [
                    "Finding A stated as a concise bullet.",
                    "Finding B stated as a concise bullet."
                ],
                "metrics_citations": {},
                "supporting_evidence_notes": [],
                "limitations": [],
                "recommendations": [],
                "data_sources": [
                    "Number_of_Cultural_Regions_all_groups.json"
                ],
                "paths": {
                    "figures_dir": "analysis/figures",
                    "data_processed_dir": "analysis/data/processed"
                },
                "version": 2
            }
        }

        payload = {
            "project_name": project_name,
            "generated_at": now,
            "research_question": rq,
            "workflow_state_brief": self._brief_workflow(workflow_state),
            "fig_summaries": fig_summaries,
            "instructions": guide,
        }
        return (
            "Generate JSON only. No explanations outside JSON.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )

    def _build_repair_prompt(
        self,
        fig_summaries: List[Dict[str, Any]],
        workflow_state: Dict[str, Any],
        previous_output: str,
    ) -> str:
        base = self._build_prompt(fig_summaries, workflow_state)
        feedback = {
            "error": "Your previous output was not valid strict JSON or did not match the schema. Return ONLY a valid JSON object.",
            "previous_output": previous_output[:2000],
        }
        return base + "\n\n" + json.dumps(feedback, ensure_ascii=False, indent=2)

    def _parse_json_strict(self, raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}\s*\Z", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

    def _fallback_build(self, fig_summaries: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        rq = (
            workflow_state.get("research_question")
            or workflow_state.get("research_topic")
            or workflow_state.get("question")
        )
        project_name = (
            workflow_state.get("project_name")
            or workflow_state.get("project")
            or ""
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        figures: List[Dict[str, Any]] = []
        data_sources_set = set()
        for fs in fig_summaries[:3]:
            file_name = None
            try:
                file_name = Path(fs.get("figure_path", "")).name if fs.get("figure_path") else None
            except Exception:
                file_name = None
            refs = self._infer_referenced(fs)
            for r in refs:
                data_sources_set.add(r)
            figures.append(
                {
                    "name": fs.get("title") or (fs.get("id") or "Figure").replace("_", " ").title(),
                    "file": file_name or (fs.get("id") or "figure") + ".png",
                    "summary": fs.get("summary")
                    or fs.get("phenomenon")
                    or "A concise description of the visible pattern consistent with the research question.",
                    "referenced_data": refs,
                }
            )

        return {
            "project_name": project_name,
            "analysis_title": "Figure-grounded analysis and conclusions",
            "generated_at": now,
            "research_paradigm": "attribution_analysis",
            "research_question": rq,
            "scenario_description": workflow_state.get("scenario_description")
            or "A brief description of the simulation scenario and variables under study.",
            "figures_analyzed": figures,
            "groups_included": workflow_state.get("groups_included") or [],
            "key_findings": workflow_state.get("key_findings") or [],
            "metrics_citations": workflow_state.get("metrics_citations") or {},
            "supporting_evidence_notes": workflow_state.get("supporting_evidence_notes") or [],
            "limitations": workflow_state.get("limitations") or [],
            "recommendations": workflow_state.get("recommendations") or [],
            "data_sources": sorted(list(data_sources_set)) if data_sources_set else [],
            "paths": {
                "figures_dir": "analysis/figures",
                "data_processed_dir": "analysis/data/processed",
            },
            "version": 2,
        }

    def _normalize_to_figure_analysis_schema(
        self,
        data: Dict[str, Any],
        fig_summaries: List[Dict[str, Any]],
        workflow_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize the model output to match scripts/figure_analysis.json fields and order."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        def as_list(value, default):
            if value is None:
                return list(default)
            if isinstance(value, list):
                return value
            return [value]

        def as_dict(value, default):
            if isinstance(value, dict):
                return value
            return dict(default)

        # Convert alternative shapes
        figures_analyzed: List[Dict[str, Any]] = []
        data_sources_from_figs = set()
        if isinstance(data.get("figures_analyzed"), list):
            for item in data["figures_analyzed"][:3]:
                name = item.get("name") or item.get("title") or "Figure"
                file_name = item.get("file") or item.get("figure") or None
                refs = as_list(item.get("referenced_data"), [])
                for r in refs:
                    if isinstance(r, str):
                        data_sources_from_figs.add(r)
                figures_analyzed.append(
                    {
                        "name": name,
                        "file": file_name or f"{name.lower().replace(' ', '_')}.png",
                        "summary": item.get("summary")
                        or item.get("phenomenon")
                        or item.get("conclusion")
                        or "",
                        "referenced_data": refs,
                    }
                )
        elif isinstance(data.get("figure_explanations"), list):
            # Map legacy schema -> required schema
            for item in data["figure_explanations"][:3]:
                name = item.get("title") or (item.get("figure_id") or "Figure").replace("_", " ").title()
                file_name = (item.get("figure_id") or name).lower().replace(" ", "_") + ".png"
                refs = as_list(item.get("referenced_data"), [])
                for r in refs:
                    if isinstance(r, str):
                        data_sources_from_figs.add(r)
                figures_analyzed.append(
                    {
                        "name": name,
                        "file": file_name,
                        "summary": item.get("summary")
                        or item.get("phenomenon")
                        or item.get("conclusion")
                        or "",
                        "referenced_data": refs,
                    }
                )
        else:
            # Build from fig_summaries if nothing provided
            for fs in fig_summaries[:3]:
                try:
                    file_name = Path(fs.get("figure_path", "")).name if fs.get("figure_path") else (fs.get("id") or "figure") + ".png"
                except Exception:
                    file_name = (fs.get("id") or "figure") + ".png"
                refs = self._infer_referenced(fs)
                for r in refs:
                    data_sources_from_figs.add(r)
                figures_analyzed.append(
                    {
                        "name": fs.get("title") or (fs.get("id") or "Figure").replace("_", " ").title(),
                        "file": file_name,
                        "summary": fs.get("summary")
                        or fs.get("phenomenon")
                        or "",
                        "referenced_data": refs,
                    }
                )

        # Compose normalized output with required key order
        normalized: Dict[str, Any] = {}
        normalized["project_name"] = data.get("project_name") or workflow_state.get("project_name") or workflow_state.get("project") or ""
        normalized["analysis_title"] = data.get("analysis_title") or "Figure-grounded analysis and conclusions"
        normalized["generated_at"] = data.get("generated_at") or now
        normalized["research_paradigm"] = data.get("research_paradigm") or "attribution_analysis"
        normalized["research_question"] = data.get("research_question") or workflow_state.get("research_question") or workflow_state.get("research_topic") or workflow_state.get("question")
        normalized["scenario_description"] = data.get("scenario_description") or "A brief description of the simulation scenario and variables under study."
        normalized["figures_analyzed"] = figures_analyzed
        normalized["groups_included"] = as_list(data.get("groups_included"), [])
        normalized["key_findings"] = as_list(data.get("key_findings"), [])
        normalized["metrics_citations"] = as_dict(data.get("metrics_citations"), {})
        normalized["supporting_evidence_notes"] = as_list(data.get("supporting_evidence_notes"), [])
        normalized["limitations"] = as_list(data.get("limitations"), [])
        normalized["recommendations"] = as_list(data.get("recommendations"), [])

        # Merge data_sources from payload and figures
        payload_sources = set([s for s in as_list(data.get("data_sources"), []) if isinstance(s, str)])
        all_sources = sorted(list(payload_sources.union(data_sources_from_figs)))
        normalized["data_sources"] = all_sources

        paths = data.get("paths") or {"figures_dir": "analysis/figures", "data_processed_dir": "analysis/data/processed"}
        normalized["paths"] = {
            "figures_dir": paths.get("figures_dir", "analysis/figures"),
            "data_processed_dir": paths.get("data_processed_dir", "analysis/data/processed"),
        }
        normalized["version"] = data.get("version") or 2
        return normalized

    def _infer_referenced(self, fs: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        for k in ["source_reference", "referenced_data", "data_file", "dataset"]:
            v = fs.get(k)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                out.extend([str(x) for x in v])
        return sorted(list({*out}))

    def _brief_workflow(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "project_name",
            "status",
            "steps_completed",
            "experiment_design",
            "workflow_version",
        ]
        brief: Dict[str, Any] = {}
        for k in keys:
            v = workflow_state.get(k)
            if v is not None:
                brief[k] = v if isinstance(v, (str, int, float)) else str(v)[:400]
        return brief

    def _resolve_outputs_dir(self) -> Path:
        p = os.environ.get("STAGE1_OUTPUTS_DIR", "outputs")
        return Path(p).absolute()


def explain(fig_summaries: List[Dict[str, Any]], workflow_state: Dict[str, Any]) -> str:
    agent = ExplainerAgent()
    return agent.explain(fig_summaries, workflow_state)


__all__ = ["ExplainerAgent", "explain"]


def _default_fig_dir(project_name: str) -> Path:
    return Path(resolve_project_paths(project_name)["figures_dir"])


def _build_fig_summaries_from_dir(fig_dir: Path, prefer_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    figs: List[Dict[str, Any]] = []
    candidates: List[Path] = []
    if prefer_files:
        for name in prefer_files:
            p = fig_dir / name
            if p.exists() and p.is_file():
                candidates.append(p)
    else:
        for name in ["fig1.png", "fig2.png", "fig3.png"]:
            p = fig_dir / name
            if p.exists() and p.is_file():
                candidates.append(p)
    for p in candidates[:3]:
        stem = p.stem
        figs.append(
            {
                "id": stem,
                "title": stem.replace("_", " ").title(),
                "figure_path": str(p),
                "referenced_data": [],
            }
        )
    return figs


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ExplainerAgent multimodal tester")
    parser.add_argument("--project-name", default="social_dynamics_combine", help="项目名（默认 social_dynamics_combine）")
    parser.add_argument("--fig-path", default=None, help="图像路径，默认查找 projects/{name}/analysis/figures/fig1.png")
    parser.add_argument("--outputs-dir", default=None, help="输出目录，默认使用环境变量 STAGE1_OUTPUTS_DIR 或 ./outputs")
    args = parser.parse_args(argv)

    project_name = args.project_name
    if args.outputs_dir:
        os.environ["STAGE1_OUTPUTS_DIR"] = args.outputs_dir

    fig_path = args.fig_path
    if not fig_path:
        default_dir = Path(resolve_project_paths(project_name)["figures_dir"])
        fig_candidate = default_dir / "fig1.png"
        fig_path = str(fig_candidate) if fig_candidate.exists() else None

    ws_path = Path(resolve_project_paths(project_name)["workflow_state"])
    workflow_state: Dict[str, Any] = {}
    try:
        with ws_path.open("r", encoding="utf-8") as f:
            workflow_state = json.load(f)
    except Exception as e:
        print(f"WARN: 加载 workflow_state 失败（{ws_path}）: {e}")

    fig_summaries: List[Dict[str, Any]] = []
    if fig_path:
        stem = Path(fig_path).stem
        fig_summaries = [{
            "id": stem,
            "title": stem.replace("_", " ").title(),
            "figure_path": fig_path,
            "referenced_data": [],
        }]

    agent = ExplainerAgent()
    result = agent.explain(fig_summaries, workflow_state)
    print(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
