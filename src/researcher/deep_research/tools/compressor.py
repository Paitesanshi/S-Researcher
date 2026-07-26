"""
Compressor Tool for Deep Research Module
Adapted from OnePage/deep_research_agent with loguru logging
"""

import json
from loguru import logger

from ..schemas import ToolOutputSchema, CompressedResult
from ..memory import AgentMemory
from .base_tool import BaseTool
from ..llm import chat


class Compressor(BaseTool):
    """压缩和总结工具"""
    
    def __init__(self, memory: AgentMemory):
        logger.debug("Compressor initialized")
        self.memory = memory

    @property
    def name(self) -> str:
        return "compressor"

    @property
    def description(self) -> str:
        return "压缩和总结工具输出数据，提取关键信息"

    def run(self, **kwargs) -> ToolOutputSchema:
        """执行压缩"""
        raw_outputs = kwargs.get("raw_outputs")
        raw_output = kwargs.get("raw_output")
        if raw_outputs is None:
            if raw_output is None:
                raise ValueError("Compressor.run() requires 'raw_output' or 'raw_outputs' parameter")
            raw_outputs = [raw_output]
        
        compressed_result = self.compress(raw_outputs, context=kwargs.get("context"))
        
        result_dict = {
            "summary": compressed_result.summary,
            "key_findings": compressed_result.key_findings
        }
        raw_json = json.dumps(result_dict, ensure_ascii=False)
        
        return ToolOutputSchema(raw_json=raw_json)

    def compress(self, raw_outputs: list, context: str | None = None) -> CompressedResult:
        """压缩和总结输出数据"""
        self.memory.add_context("Compressor: Starting compression")
        
        try:
            all_papers: list = []
            summaries_to_merge: list[dict] = []
            inferred_query = None

            for output in raw_outputs:
                if hasattr(output, "raw_json"):
                    data = json.loads(output.raw_json)
                elif isinstance(output, dict) and "raw_json" in output:
                    data = json.loads(output["raw_json"])
                else:
                    data = output if isinstance(output, dict) else {}

                if inferred_query is None:
                    inferred_query = data.get("query")

                if isinstance(data.get("results"), list):
                    all_papers.extend(data.get("results") or [])
                elif "summary" in data and "key_findings" in data:
                    summaries_to_merge.append({
                        "summary": data.get("summary", ""),
                        "key_findings": data.get("key_findings", []) or [],
                    })

            query = inferred_query or (context or "unknown query")

            if all_papers:
                self.memory.store_papers_batch(all_papers)
                self.memory.add_context(f"Compressor: Cached {len(all_papers)} papers")

                papers_text = self._build_papers_text(all_papers)
                prompt = self._build_compression_prompt(query, papers_text, len(all_papers))
                messages = [
                    {"role": "system", "content": "You are an expert research assistant specializing in academic literature analysis."},
                    {"role": "user", "content": prompt}
                ]
                llm_response = chat(messages=messages, temperature=0.3)

                compressed = self._parse_llm_response(llm_response)
                self.memory.add_context(f"Compressor: Generated summary with {len(compressed.key_findings)} key findings")
                return compressed

            if summaries_to_merge:
                merged_findings = []
                parts_text = []
                for idx, item in enumerate(summaries_to_merge, 1):
                    parts_text.append(f"[Part {idx} Summary]\n{item['summary']}")
                    for f in item["key_findings"]:
                        if isinstance(f, str):
                            merged_findings.append(f.strip())

                merge_prompt = f"""You are merging multiple synthesized reports about: "{query}".

Below are summaries from different branches:

{chr(10).join(parts_text)}

Please provide:
1. One integrated, non-redundant summary (1-2 paragraphs).
2. A deduplicated list of 5-10 key findings.

FORMAT STRICTLY:
SUMMARY:
[Your integrated summary]

KEY_FINDINGS:
- [Finding 1]
- [Finding 2]
- [Finding 3]"""
                messages = [
                    {"role": "system", "content": "You are an expert research assistant specializing in synthesizing multi-source summaries."},
                    {"role": "user", "content": merge_prompt}
                ]
                llm_response = chat(messages=messages, temperature=0.2)
                compressed = self._parse_llm_response(llm_response)
                
                if not compressed.key_findings or compressed.key_findings == ["Unable to extract structured findings from the response"]:
                    seen = set()
                    deduped = []
                    for f in merged_findings:
                        if f and f not in seen:
                            seen.add(f)
                            deduped.append(f)
                    compressed.key_findings = deduped[:10] or ["No key findings extracted"]

                self.memory.add_context(f"Compressor: Generated summary with {len(compressed.key_findings)} key findings (merge)")
                return compressed

            self.memory.add_context("Compressor: No inputs to compress")
            return CompressedResult(
                summary="No papers found for the given query.",
                key_findings=[]
            )
            
        except Exception as e:
            logger.error(f"Compressor error: {e}")
            self.memory.add_context(f"Compressor: Error during compression - {str(e)}")
            return CompressedResult(
                summary=f"Error processing papers: {str(e)[:200]}",
                key_findings=["Compression failed due to technical error"]
            )
    
    def _build_papers_text(self, papers: list, max_papers: int = None) -> str:
        """构建论文摘要文本"""
        papers_text_parts = []
        
        for i, paper in enumerate(papers if max_papers is None else papers[:max_papers], 1):
            title = paper.get('title', 'Untitled')
            abstract = paper.get('s2_abstract') or paper.get('abstract', 'No abstract available')
            
            tldr = ""
            if 's2_tldr' in paper and paper['s2_tldr']:
                tldr_data = paper['s2_tldr']
                if isinstance(tldr_data, dict) and 'text' in tldr_data:
                    tldr = tldr_data['text']
            
            introduction = paper.get('introduction')
            related_work = paper.get('related_work')
            
            paper_text = f"Paper {i}: {title}\n"
            if tldr:
                paper_text += f"TL;DR: {tldr}\n"
            paper_text += f"Abstract: {abstract[:500]}...\n"
            
            if introduction:
                intro_text = introduction[:800] if len(introduction) > 800 else introduction
                paper_text += f"Introduction: {intro_text}"
                if len(introduction) > 800:
                    paper_text += "..."
                paper_text += "\n"
            
            if related_work:
                rw_text = related_work[:800] if len(related_work) > 800 else related_work
                paper_text += f"Related Work: {rw_text}"
                if len(related_work) > 800:
                    paper_text += "..."
                paper_text += "\n"
            
            papers_text_parts.append(paper_text)
        
        if max_papers is not None and len(papers) > max_papers:
            papers_text_parts.append(f"\n... and {len(papers) - max_papers} more papers")
        
        return "\n\n".join(papers_text_parts)
    
    def _build_compression_prompt(self, query: str, papers_text: str, total_count: int) -> str:
        """构建压缩提示词"""
        return f"""You are analyzing academic papers related to the query: "{query}"

Total papers found: {total_count}

Papers information:
{papers_text}

Note: Each paper may include Introduction and Related Work sections extracted from the PDF. These provide valuable context about the research background, motivation, and related studies. Use this information to better understand the papers' contributions and relationships.

Please provide:
1. A comprehensive summary (2-3 paragraphs) synthesizing the main themes and contributions across these papers.
2. A list of 3-7 key findings or insights extracted from these papers.

Format your response EXACTLY as follows:

SUMMARY:
[Your comprehensive summary here]

KEY_FINDINGS:
- [Finding 1]
- [Finding 2]
- [Finding 3]
...

Be concise, accurate, and focus on the most important information. Pay special attention to how papers relate to each other based on their Introduction and Related Work sections."""
    
    def _parse_llm_response(self, llm_response: str) -> CompressedResult:
        """解析LLM响应"""
        summary = ""
        key_findings = []
        
        parts = llm_response.split("KEY_FINDINGS:")
        
        if len(parts) >= 2:
            summary_part = parts[0].replace("SUMMARY:", "").strip()
            summary = summary_part
            
            findings_part = parts[1].strip()
            for line in findings_part.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    finding = line[1:].strip()
                    if finding:
                        key_findings.append(finding)
        else:
            summary = llm_response.strip()
            key_findings = ["Unable to extract structured findings from the response"]
        
        if not summary:
            summary = "Summary generation failed"
        if not key_findings:
            key_findings = ["No key findings extracted"]
        
        return CompressedResult(
            summary=summary,
            key_findings=key_findings
        )
