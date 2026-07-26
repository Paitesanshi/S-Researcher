"""
Literature Review Generator with Deep Research Integration

This module generates comprehensive literature reviews using the Deep Research 
module which provides DAG-based planning and execution with Semantic Scholar 
paper search.

Debug Mode:
    设置环境变量 LITERATURE_REVIEW_DEBUG=1 可保存输入输出到 debug 目录
    或者直接调用 generate 时设置 self.debug_mode = True
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from onesim.models import SystemMessage, UserMessage
from ..core.config import ReportConfig
from ..core.context import ReportContext
from .base import SectionGenerator

# Deep Research Module
from researcher.deep_research import AgentMemory, Planner, Executor
from researcher.deep_research.tools import DeepPaperResearchTool, Compressor, ReportGenerator


class LiteratureReviewGenerator(SectionGenerator):
    """Generates comprehensive literature review with automated paper search using Deep Research"""

    def __init__(self, model_config_name: str = None, debug_mode: bool = None):
        super().__init__(model_config_name)
        
        # Debug mode: 可通过环境变量或参数控制
        if debug_mode is not None:
            self.debug_mode = debug_mode
        else:
            self.debug_mode = os.environ.get("LITERATURE_REVIEW_DEBUG", "0") == "1"
        
        self._debug_dir: Optional[Path] = None

    def _setup_debug_dir(self, context: ReportContext) -> Path:
        """设置调试输出目录"""
        if context.output_dir:
            debug_dir = Path(context.output_dir) / "debug" / "literature_review"
        else:
            debug_dir = Path(__file__).parents[4] / "debug" / "literature_review"
        
        debug_dir.mkdir(parents=True, exist_ok=True)
        self._debug_dir = debug_dir
        return debug_dir

    def _save_debug_input(self, context: ReportContext, config: ReportConfig):
        """保存输入数据用于调试"""
        if not self.debug_mode or not self._debug_dir:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        context_data = {
            "timestamp": timestamp,
            "research_question": context.research_question,
            "research_topic": context.research_topic,
            "scenario_description": context.scenario_description,
            "analysis_data_preview": context.analysis_data[:2000] if context.analysis_data else "",
            "analysis_data_length": len(context.analysis_data) if context.analysis_data else 0,
            "existing_citation_entries": list(context.citation_entries.keys()),
            "image_paths_count": len(context.image_paths),
        }
        
        context_file = self._debug_dir / f"input_context_{timestamp}.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2)
        
        config_data = {
            "timestamp": timestamp,
            "include_bibliography": config.include_bibliography,
            "max_literature_papers": config.max_literature_papers,
            "model_config_name": config.model_config_name,
            "language": config.language,
            "include_literature_review": config.include_literature_review,
        }
        
        config_file = self._debug_dir / f"input_config_{timestamp}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[DEBUG] Saved input to: {self._debug_dir}")

    def _save_debug_output(self, output: str, bibtex_entries: Dict[str, str], 
                           parts_summaries: List[str], parts_key_findings: List[str]):
        """保存输出数据用于调试"""
        if not self.debug_mode or not self._debug_dir:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存最终输出
        output_file = self._debug_dir / f"output_latex_{timestamp}.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        
        # 保存 BibTeX
        bibtex_file = self._debug_dir / f"output_bibtex_{timestamp}.bib"
        with open(bibtex_file, 'w', encoding='utf-8') as f:
            for key, entry in bibtex_entries.items():
                f.write(f"% Key: {key}\n")
                f.write(entry)
                f.write("\n\n")
        
        # 保存中间数据
        intermediate_data = {
            "timestamp": timestamp,
            "parts_summaries": parts_summaries,
            "parts_key_findings": parts_key_findings,
            "output_length": len(output),
            "bibtex_entries_count": len(bibtex_entries),
        }
        
        intermediate_file = self._debug_dir / f"intermediate_{timestamp}.json"
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            json.dump(intermediate_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[DEBUG] Saved output to: {self._debug_dir}")

    def get_section_name(self) -> str:
        return "literature_review"

    def generate(self, context: ReportContext, config: ReportConfig) -> str:
        """Generate literature review section using Deep Research module"""
        
        # Setup debug directory
        if self.debug_mode:
            self._setup_debug_dir(context)
            self._save_debug_input(context, config)
            logger.info("[DEBUG] Literature Review Generator running in DEBUG mode")

        logger.info("[LiteratureReview] Starting Deep Research pipeline...")

        # Step 1: Initialize tools and memory
        memory = AgentMemory()
        paper_search_tool = DeepPaperResearchTool()
        compressor = Compressor(memory=memory)
        report_generator = ReportGenerator(memory=memory)

        tools_registry = {
            paper_search_tool.name: paper_search_tool,
            compressor.name: compressor,
            report_generator.name: report_generator,
        }

        # Step 2: Generate research plan
        logger.info("[LiteratureReview] Generating research plan...")
        planner = Planner()
        plan = planner.generate_plan(context.research_question)

        # Step 3: Execute DAG
        logger.info("[LiteratureReview] Executing research DAG...")
        executor = Executor(tools_registry=tools_registry)
        executor.execute_dag(plan, initial_input=context.research_question)

        # Step 4: Collect results from executor
        parts_summaries, parts_key_findings = self._collect_results(executor)
        logger.info(f"[LiteratureReview] Collected {len(parts_summaries)} summaries, {len(parts_key_findings)} findings")

        # Step 5: Build references from memory
        references = report_generator._build_references_from_memory(max_refs=200)
        logger.info(f"[LiteratureReview] Found {len(references)} unique references")

        # Step 6: Generate Related Work (LaTeX)
        logger.info("[LiteratureReview] Generating Related Work section...")
        related_work_body = report_generator._generate_related_work(
            topic=context.research_question,
            parts_summaries=parts_summaries,
            parts_key_findings=parts_key_findings,
            references=references,
            output_format="latex"
        )

        # Step 7: Generate BibTeX entries (only for cited references)
        if config.include_bibliography:
            # Extract citation keys actually used in the LaTeX content
            cited_keys = self._extract_citation_keys(related_work_body)
            logger.info(f"[LiteratureReview] Found {len(cited_keys)} cited references in text")
            
            # Generate all BibTeX entries
            bibtex_content = report_generator._format_references_section_bibtex(references)
            all_bibtex_entries = self._parse_bibtex_to_dict(bibtex_content)
            
            # Filter to only include cited entries
            bibtex_entries = {k: v for k, v in all_bibtex_entries.items() if k in cited_keys}
            logger.info(f"[LiteratureReview] Filtered from {len(all_bibtex_entries)} to {len(bibtex_entries)} BibTeX entries")
            
            context.citation_entries.update(bibtex_entries)
            logger.info(f"[LiteratureReview] Added {len(bibtex_entries)} BibTeX entries")
        else:
            bibtex_entries = {}

        # Wrap with section header if not already present
        if not related_work_body.strip().startswith("\\section"):
            result = f"\\section{{Related Work}}\n{related_work_body}\n"
        else:
            result = related_work_body
        
        # Save debug output
        if self.debug_mode:
            self._save_debug_output(result, bibtex_entries, parts_summaries, parts_key_findings)
        
        logger.info("[LiteratureReview] Generation complete!")
        return result

    def _collect_results(self, executor: Executor) -> tuple:
        """从 Executor 结果中收集摘要和关键发现"""
        parts_summaries: List[str] = []
        parts_key_findings: List[str] = []

        for node_id, result_entry in executor.results.items():
            if result_entry.get("status") != "success":
                continue
            
            result = result_entry.get("result")
            if result is None:
                continue

            # 解析结果
            data = {}
            if hasattr(result, "raw_json"):
                try:
                    data = json.loads(result.raw_json)
                except Exception:
                    pass
            elif isinstance(result, dict) and "raw_json" in result:
                try:
                    data = json.loads(result["raw_json"])
                except Exception:
                    pass
            elif isinstance(result, dict):
                data = result

            # 提取摘要
            summary = data.get("summary")
            if summary and isinstance(summary, str) and summary.strip():
                parts_summaries.append(summary.strip())

            # 提取关键发现
            key_findings = data.get("key_findings") or []
            for finding in key_findings:
                if isinstance(finding, str) and finding.strip():
                    parts_key_findings.append(finding.strip())

        return parts_summaries, parts_key_findings

    def _extract_citation_keys(self, latex_content: str) -> set:
        """从 LaTeX 内容中提取引用的 citation keys"""
        import re
        # 匹配 \cite{key1, key2, ...} 格式
        pattern = r'\\cite\{([^}]+)\}'
        matches = re.findall(pattern, latex_content)
        
        cited_keys = set()
        for match in matches:
            # 处理多个 key 的情况，如 \cite{ref1, ref2}
            keys = [k.strip() for k in match.split(',')]
            cited_keys.update(keys)
        
        return cited_keys

    def _parse_bibtex_to_dict(self, bibtex_content: str) -> Dict[str, str]:
        """将 BibTeX 内容解析为字典"""
        entries = {}
        current_key = None
        current_entry_lines = []
        
        for line in bibtex_content.split('\n'):
            if line.startswith('@'):
                # 保存之前的条目
                if current_key and current_entry_lines:
                    entries[current_key] = '\n'.join(current_entry_lines)
                
                # 开始新条目
                import re
                match = re.match(r'@\w+\{(\w+),', line)
                if match:
                    current_key = match.group(1)
                    current_entry_lines = [line]
            elif current_key:
                current_entry_lines.append(line)
                if line.strip() == '}':
                    # 条目结束
                    entries[current_key] = '\n'.join(current_entry_lines)
                    current_key = None
                    current_entry_lines = []
        
        return entries