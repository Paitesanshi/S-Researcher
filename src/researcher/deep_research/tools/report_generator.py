"""
Report Generator Tool for Deep Research Module
Adapted from OnePage/deep_research_agent - LaTeX output only
"""

import json
import re
from typing import Any, Dict, List
from loguru import logger

from ..schemas import ToolOutputSchema
from .base_tool import BaseTool
from ..llm import chat
from ..memory import AgentMemory


class ReportGenerator(BaseTool):
    """报告生成工具 - 生成 Related Work LaTeX 输出"""
    
    def __init__(self, memory: AgentMemory):
        self.memory = memory

    @property
    def name(self) -> str:
        return "report_generator"

    @property
    def description(self) -> str:
        return "生成 Related Work 章节的 LaTeX 输出"

    def run(self, **kwargs) -> ToolOutputSchema:
        """执行报告生成"""
        raw_outputs = kwargs.get("raw_outputs")
        raw_output = kwargs.get("raw_output")
        context = kwargs.get("context") or "Unknown topic"

        if raw_outputs is None:
            if raw_output is None:
                raise ValueError("report_generator.run() requires 'raw_outputs' or 'raw_output'")
            raw_outputs = [raw_output]

        # 解析上游结果
        parts_summaries: List[str] = []
        parts_key_findings: List[str] = []

        for output in raw_outputs:
            data = self._parse_output_to_dict(output)
            summary = (data.get("summary") or "").strip()
            if summary:
                parts_summaries.append(summary)
            kf = data.get("key_findings") or []
            for item in kf:
                if isinstance(item, str) and item.strip():
                    parts_key_findings.append(item.strip())

        # 获取参考文献
        references = self._build_references_from_memory(max_refs=200)

        # 生成 Related Work
        report_body = self._generate_related_work(
            topic=context,
            parts_summaries=parts_summaries,
            parts_key_findings=parts_key_findings,
            references=references,
            output_format="latex"
        )

        result = {
            "summary": report_body,
            "key_findings": parts_key_findings[:10],
        }
        return ToolOutputSchema(raw_json=json.dumps(result, ensure_ascii=False))

    def _parse_output_to_dict(self, output: Any) -> Dict[str, Any]:
        """解析输出为字典"""
        if hasattr(output, "raw_json"):
            try:
                return json.loads(output.raw_json)
            except Exception:
                return {}
        if isinstance(output, dict):
            if "raw_json" in output:
                try:
                    return json.loads(output["raw_json"])
                except Exception:
                    return {}
            return output
        return {}

    def _build_references_from_memory(self, max_refs: int = 200) -> List[Dict[str, Any]]:
        """从内存获取参考文献"""
        papers = self.memory.get_all_papers() if hasattr(self.memory, "get_all_papers") else []
        
        def norm_title(s: str) -> str:
            s = (s or "").strip().lower()
            s = re.sub(r"\s+", " ", s)
            s = re.sub(r"[^a-z0-9\s:\-_/.,()]+", "", s)
            return s

        def norm_doi(s: str) -> str:
            s = (s or "").strip().lower()
            s = s.replace("https://doi.org/", "").replace("http://doi.org/", "")
            return s

        def norm_arxiv(s: str) -> str:
            s = (s or "").strip().lower()
            s = re.sub(r"^arxiv:", "", s)
            s = re.sub(r"v\d+$", "", s)
            return s

        def norm_url(s: str) -> str:
            s = (s or "").strip()
            if not re.match(r"^https?://[^\s]+$", s):
                return ""
            return s.lower()

        seen = set()
        deduped: List[Dict[str, Any]] = []
        for p in papers:
            title = norm_title(p.get("title") or "")
            external_ids = p.get("externalIds") or {}
            doi = norm_doi(external_ids.get("DOI"))
            arxiv_id = norm_arxiv(external_ids.get("ArXiv"))
            url = norm_url((p.get("downloadable_url") or p.get("url") or ""))
            key = (title, doi, arxiv_id, url)
            if key in seen:
                continue
            seen.add(key)
            cleaned = dict(p)
            cleaned["title"] = p.get("title") or "Untitled"
            cleaned["externalIds"] = {"DOI": doi or None, "ArXiv": arxiv_id or None}
            if url:
                cleaned["downloadable_url"] = url
            deduped.append(cleaned)

        return deduped[:max_refs]

    def _format_single_reference_bibtex(self, idx: int, paper: Dict[str, Any]) -> str:
        """格式化单篇论文为 BibTeX"""
        title = paper.get("title") or "Untitled"
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI") or ""
        arxiv_id = external_ids.get("ArXiv") or ""
        url = paper.get("downloadable_url") or paper.get("url") or ""
        year = paper.get("year") or ""
        journal_data = paper.get("journal") or {}
        venue = (
            paper.get("venue")
            or (journal_data.get("name") if isinstance(journal_data, dict) else "")
            or ""
        )
        
        authors_list = paper.get("authors") or []
        if authors_list:
            author_names = [a.get("name", "Unknown") for a in authors_list if a.get("name")]
            authors_str = " and ".join(author_names) if author_names else "Unknown"
        else:
            authors_str = "Unknown"
        
        cite_key = f"ref{idx}"
        
        def escape_bibtex(s: str) -> str:
            for char in ['&', '%', '#', '_']:
                s = s.replace(char, '\\' + char)
            return s
        
        title_escaped = escape_bibtex(title)
        authors_escaped = escape_bibtex(authors_str)
        venue_escaped = escape_bibtex(venue)
        
        entry_type = "article" if venue_escaped else "misc"
        lines = [f"@{entry_type}{{{cite_key},"]
        lines.append(f"  title = {{{title_escaped}}},")
        lines.append(f"  author = {{{authors_escaped}}},")
        if year:
            lines.append(f"  year = {{{year}}},")
        if venue_escaped:
            lines.append(f"  journal = {{{venue_escaped}}},")
        if doi:
            lines.append(f"  doi = {{{doi}}},")
        if arxiv_id:
            lines.append(f"  eprint = {{{arxiv_id}}},")
            lines.append(f"  archiveprefix = {{arXiv}},")
        if url:
            lines.append(f"  url = {{{url}}},")
        lines.append("}")
        
        return "\n".join(lines)

    def _format_references_section_bibtex(self, references: List[Dict[str, Any]]) -> str:
        """生成完整 BibTeX 文件"""
        if not references:
            return "% No references available\n"
        
        used_keys = set()
        unique_refs: List[Dict[str, Any]] = []
        for p in references:
            title = (p.get("title") or "").strip().lower()
            external_ids = p.get("externalIds") or {}
            doi = (external_ids.get("DOI") or "").strip().lower()
            arxiv_id = (external_ids.get("ArXiv") or "").strip().lower()
            url = ((p.get("downloadable_url") or "") or (p.get("url") or "")).strip().lower()
            key = (title, doi, arxiv_id, url)
            if key in used_keys:
                continue
            used_keys.add(key)
            unique_refs.append(p)
        
        unique_refs = unique_refs[:150]
        
        entries = []
        entries.append("% BibTeX references generated by Deep Research Agent")
        entries.append(f"% Total references: {len(unique_refs)}")
        entries.append("")
        
        for i, paper in enumerate(unique_refs, 1):
            entries.append(self._format_single_reference_bibtex(i, paper))
            entries.append("")
        
        return "\n".join(entries)

    def _generate_related_work(
        self,
        topic: str,
        parts_summaries: List[str],
        parts_key_findings: List[str],
        references: List[Dict[str, Any]],
        user_contribution: str = "",
        output_format: str = "latex",
    ) -> str:
        """
        生成 Related Work（LaTeX 格式）
        """
        logger.info(f"[ReportGenerator] Generating Related Work (LaTeX mode)")

        # 精选前40篇引用
        max_refs = min(40, len(references))
        curated_refs = references[:max_refs]
        
        # 准备引用列表
        refs_for_prompt = []
        for i, p in enumerate(curated_refs, 1):
            title = p.get("title") or "Untitled"
            refs_for_prompt.append(f"[{i}] (Cite Key: ref{i}) {title}")
        refs_text = "\n".join(refs_for_prompt) if refs_for_prompt else "None"

        # 准备证据
        evidence_text = ""
        if parts_summaries:
            evidence_text += "Summaries:\n" + "\n\n".join(f"- {s}" for s in parts_summaries[:10]) + "\n\n"
        if parts_key_findings:
            evidence_text += "Key Findings:\n" + "\n".join(f"- {k}" for k in parts_key_findings[:20]) + "\n\n"

        # 用户贡献（可选）
        contribution_section = ""
        if user_contribution and user_contribution.strip():
            contribution_section = f"""
**Our Contribution** (highlight gaps that our work addresses):
{user_contribution.strip()}

When writing, identify specific limitations in existing work that our contribution addresses.
"""
        
        # LaTeX 格式指令
        format_instructions = """
**OUTPUT SPECIFICATIONS (LATEX)**:
- Target length: 1500-2500 English words
- Structure: Use LaTeX commands `\\section{Related Work}`, `\\subsection{Theme Title}`
- Citations: MUST use `\\cite{refN}` format validation. 
  - Example: "Recent work \\cite{ref1, ref2} shows..."
  - DO NOT use `[1]` or `(Author, Year)` manually.
- Formatting: Use `\\textbf{}`, `\\textit{}` for emphasis.
- Escape special characters: Ensure `%`, `&`, `_`, `$`, `#` are properly escaped (e.g., `\\%`).
"""
        output_template = """
**Output Format**:
\\section{Related Work}

\\subsection{[Theme 1 Title]}

[300-500 words: introduce the theme, summarize key approaches with \\cite{refN}, analyze limitations]

\\subsection{[Theme 2 Title]}

[... content ...]

[Continue for 3-5 themes total]
"""
        citation_style = """
3. **Citation Style**:
   - Cite extensively using `\\cite{refN}` keys provided in the reference list.
   - Example string: "Axelrod's model \\cite{ref19} demonstrates..."
"""

        prompt = f"""You are a senior researcher writing the "Related Work" section for an academic paper on: "{topic}".

{format_instructions}
{contribution_section}
**CRITICAL REQUIREMENTS**:

1. **Thematic Organization**: Group related work into 3-5 coherent themes. Each theme should:
   - Have a clear focus (methodology, application domain, or research direction)
   - Synthesize 5-10 related papers
   - Be 300-500 words

2. **Critical Analysis**: For each theme:
   - Summarize the main approaches and findings
   - Identify limitations, gaps, or contradictions
   - End with a transition to the next theme or (for the last theme) highlight what remains unsolved

{citation_style}

4. **Academic Tone**:
   - Professional, objective language
   - Avoid superlatives ("groundbreaking", "revolutionary")
   - Use hedging appropriately ("appears to", "suggests that", "may")

**Available Evidence**:
{evidence_text[:4000]}

**Numbered References** (cite these using keys provided):
{refs_text}

{output_template}

**FINAL INSTRUCTION**: 
- Write naturally flowing academic prose
- End with a paragraph summarizing what gaps remain (this sets up motivation for the paper's contribution)
- Do NOT include a separate references section (it will be appended automatically)
"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert academic writer who creates focused, critical literature reviews. Write in natural academic English suitable for top-tier venues."
            },
            {"role": "user", "content": prompt}
        ]
        
        result = chat(messages=messages, temperature=0.3, extra={"max_tokens": 4096}).strip()
        logger.info(f"[ReportGenerator] Related work generated: ~{len(result)} characters")
        return result

    def _strip_references_from_body(self, body: str) -> str:
        """去除正文中的参考文献段落"""
        lines = body.splitlines()
        cut_idx = None
        for idx, line in enumerate(lines):
            s = line.strip()
            s_lower = s.lower()
            if re.match(r"^#{0,6}\s*(references|参考文献)\b", s_lower):
                cut_idx = idx
                break
        if cut_idx is not None:
            return "\n".join(lines[:cut_idx]).rstrip()
        return body.strip()
