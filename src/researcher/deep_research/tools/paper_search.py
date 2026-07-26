"""
Deep Paper Research Tool for Deep Research Module
Adapted from OnePage/deep_research_agent with loguru logging
"""

import json
import requests
import time
import threading
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF (fitz) not installed, PDF text extraction will be disabled")

from ..schemas import ToolOutputSchema
from .base_tool import BaseTool
from ..config import get_settings

# Semantic Scholar API 速率限制
_S2_RATE_LOCK = threading.Lock()
_S2_LAST_CALL_TS = 0.0
_S2_MIN_INTERVAL_SEC = 1.1


class DeepPaperResearchTool(BaseTool):
    """
    深度学术论文研究工具。
    流程：
    1. 使用 Semantic Scholar 搜索论文
    2. 智能判断下载方式（ArXiv / Unpaywall / OpenAccess）
    3. 下载 PDF 并提取 Introduction 和 Related Work
    """
    
    def __init__(self, parallel_downloads: Optional[int] = None):
        if parallel_downloads is None:
            settings = get_settings()
            parallel_downloads = settings.parallel_downloads
        self.parallel_downloads = max(1, parallel_downloads)

    @property
    def name(self) -> str:
        return "paper_search"

    @property
    def description(self) -> str:
        return "深度学术论文研究工具"

    def run(self, **kwargs) -> ToolOutputSchema:
        """执行深度论文研究"""
        query = kwargs.get("query")
        if query is None:
            raise ValueError(f"{self.name}.run() requires 'query' parameter")

        logger.info(f"[PaperSearch] Starting search for: '{query}'")

        # 步骤 1: Semantic Scholar 搜索
        s2_results = self._search_semantic_scholar(query=query) or []

        enable_pdf_processing = kwargs.get("enable_pdf_processing", True)
        consolidated_results = []
        statistics = None

        if not s2_results:
            logger.warning(f"[PaperSearch] No results found")

        elif not enable_pdf_processing:
            logger.info(f"[PaperSearch] Skipping PDF processing")
            for paper in s2_results:
                external_ids = paper.get("externalIds", {})
                doi = external_ids.get("DOI")
                arxiv_id = external_ids.get("ArXiv")
                open_access_pdf = paper.get("openAccessPdf", {})

                oa_data = self._get_download_url(
                    arxiv_id=arxiv_id,
                    doi=doi,
                    open_access_pdf=open_access_pdf,
                )
                pdf_url = oa_data.get("best_oa_url")

                consolidated_results.append({
                    "paperId": paper.get("paperId", "N/A"),
                    "title": paper.get("title"),
                    "s2_abstract": paper.get("abstract"),
                    "s2_tldr": paper.get("tldr"),
                    "citationCount": paper.get("citationCount"),
                    "influentialCitationCount": paper.get("influentialCitationCount"),
                    "authors": paper.get("authors"),
                    "year": paper.get("year"),
                    "externalIds": paper.get("externalIds"),
                    "downloadable_url": pdf_url,
                    "download_source": oa_data.get("source"),
                    "introduction": None,
                    "related_work": None,
                })

        else:
            # 带 PDF 处理
            statistics = {
                "download_total": 0,
                "download_success": 0,
                "introduction_total": 0,
                "introduction_success": 0,
                "related_work_total": 0,
                "related_work_success": 0,
            }

            temp_dir = tempfile.mkdtemp(prefix="paper_search_")
            max_parallel = kwargs.get("parallel_downloads", self.parallel_downloads)
            stats_lock = threading.Lock()

            logger.info(f"[PaperSearch] Processing {len(s2_results)} papers with {max_parallel} workers")

            with ThreadPoolExecutor(max_workers=max_parallel or 1) as pool:
                future_to_paper = {
                    pool.submit(self._process_single_paper, paper, temp_dir, statistics, stats_lock): paper
                    for paper in s2_results
                }
                for future in as_completed(future_to_paper):
                    paper_result = future.result()
                    if paper_result:
                        consolidated_results.append(paper_result)

        final_output = {
            "source_pipeline": ["semantic_scholar", "arxiv_direct/unpaywall", "pdf_download", "text_extraction"],
            "query": query,
            "total_s2_results": len(consolidated_results),
            "results": consolidated_results,
        }
        if statistics is not None:
            final_output["statistics"] = statistics

        return ToolOutputSchema(raw_json=json.dumps(final_output, ensure_ascii=False, indent=2))

    def _process_single_paper(
        self,
        paper: Dict[str, Any],
        temp_dir: str,
        statistics: Optional[Dict[str, int]] = None,
        stats_lock: Optional[threading.Lock] = None,
    ) -> Optional[Dict[str, Any]]:
        """处理单篇论文"""
        paper_id = paper.get("paperId", "N/A")
        title = paper.get("title")

        try:
            external_ids = paper.get("externalIds", {})
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")
            open_access_pdf = paper.get("openAccessPdf", {})

            oa_data = self._get_download_url(
                arxiv_id=arxiv_id,
                doi=doi,
                open_access_pdf=open_access_pdf
            )

            introduction_text = None
            related_work_text = None
            pdf_url = oa_data.get("best_oa_url")

            if pdf_url and HAS_PYMUPDF:
                if statistics is not None and stats_lock is not None:
                    with stats_lock:
                        statistics["download_total"] += 1

                downloaded_pdf_path = self._download_pdf(pdf_url, dest_dir=temp_dir)
                if downloaded_pdf_path and os.path.exists(downloaded_pdf_path):
                    if statistics is not None and stats_lock is not None:
                        with stats_lock:
                            statistics["download_success"] += 1

                    # Introduction 抽取
                    if statistics is not None and stats_lock is not None:
                        with stats_lock:
                            statistics["introduction_total"] += 1
                    introduction_text = self._extract_introduction_text(downloaded_pdf_path)
                    if introduction_text:
                        logger.debug(f"[PaperSearch] Extracted Introduction ({len(introduction_text)} chars)")
                        if statistics is not None and stats_lock is not None:
                            with stats_lock:
                                statistics["introduction_success"] += 1

                    # Related Work 抽取
                    if statistics is not None and stats_lock is not None:
                        with stats_lock:
                            statistics["related_work_total"] += 1
                    related_work_text = self._extract_related_work_text(downloaded_pdf_path)
                    if related_work_text:
                        logger.debug(f"[PaperSearch] Extracted Related Work ({len(related_work_text)} chars)")
                        if statistics is not None and stats_lock is not None:
                            with stats_lock:
                                statistics["related_work_success"] += 1

            return {
                "paperId": paper_id,
                "title": title,
                "s2_abstract": paper.get("abstract"),
                "s2_tldr": paper.get("tldr"),
                "citationCount": paper.get("citationCount"),
                "influentialCitationCount": paper.get("influentialCitationCount"),
                "authors": paper.get("authors"),
                "year": paper.get("year"),
                "externalIds": paper.get("externalIds"),
                "downloadable_url": pdf_url,
                "download_source": oa_data.get("source"),
                "introduction": introduction_text,
                "related_work": related_work_text
            }
        except Exception as exc:
            logger.warning(f"[PaperSearch] Error processing '{title}': {exc}")
            return {
                "paperId": paper_id,
                "title": title,
                "s2_abstract": paper.get("abstract"),
                "s2_tldr": paper.get("tldr"),
                "citationCount": paper.get("citationCount"),
                "influentialCitationCount": paper.get("influentialCitationCount"),
                "authors": paper.get("authors"),
                "year": paper.get("year"),
                "externalIds": paper.get("externalIds"),
                "downloadable_url": None,
                "download_source": None,
                "introduction": None,
                "related_work": None,
                "error": str(exc)
            }

    def _respect_s2_rate_limit(self):
        """确保 Semantic Scholar 请求速率不超过 1/秒"""
        global _S2_LAST_CALL_TS
        with _S2_RATE_LOCK:
            now = time.time()
            wait_seconds = max(0.0, _S2_MIN_INTERVAL_SEC - (now - _S2_LAST_CALL_TS))
            if wait_seconds > 0:
                logger.debug(f"[PaperSearch] Throttling S2 request for {wait_seconds:.2f}s")
                time.sleep(wait_seconds)
            _S2_LAST_CALL_TS = time.time()

    def _download_pdf(self, pdf_url: str, dest_dir: Optional[str] = None) -> Optional[str]:
        """下载 PDF 文件"""
        try:
            response = requests.get(pdf_url, timeout=20)
            response.raise_for_status()
            
            filename = os.path.basename(pdf_url.split('?')[0])
            if not filename.endswith('.pdf'):
                filename = 'downloaded_paper.pdf'
            
            target_dir = dest_dir or tempfile.gettempdir()
            os.makedirs(target_dir, exist_ok=True)
            local_path = os.path.join(target_dir, filename)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"[PaperSearch] PDF downloaded: {local_path}")
            return local_path
        except Exception as e:
            logger.debug(f"[PaperSearch] PDF download failed: {e}")
            return None

    def _clean_block(self, block_text: str) -> str:
        """清洗文本块"""
        lines = [ln.rstrip() for ln in block_text.split("\n")]
        kept = []
        for ln in lines:
            line = ln.strip()
            if not line:
                kept.append(ln)
                continue

            if re.match(r"^(Figure|Fig\.|Table)\s+\d+", line, re.IGNORECASE):
                continue

            if re.match(r"^\s*[\[\(]?[x×\-\*]\]?\s+", line, re.IGNORECASE):
                continue

            if "/" in line and "..." in line and "." not in line.rstrip("."):
                continue

            if not re.search(r"[a-z]", line) and " " not in line and len(line) <= 20:
                continue

            if len(line) <= 3 and " " not in line:
                continue

            kept.append(ln)

        return "\n".join(kept).strip()

    def _is_paragraph_like(self, block_text: str) -> bool:
        """判断是否为段落"""
        text = block_text.strip()
        if not text:
            return False

        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            return False

        if any(re.match(r"^(Figure|Fig\.|Table)\s+\d+", ln, re.IGNORECASE) for ln in lines):
            return False

        total_len = sum(len(ln) for ln in lines)
        avg_len = total_len / len(lines)
        short_lines = sum(1 for ln in lines if len(ln) < 15)

        if len(lines) >= 3 and short_lines / len(lines) >= 0.6 and avg_len < 30:
            return False

        no_space_lines = sum(1 for ln in lines if " " not in ln)
        if len(lines) >= 3 and no_space_lines / len(lines) >= 0.6:
            return False

        punct_cnt = sum(1 for ch in text if ch in ".?!")
        if punct_cnt == 0 and total_len < 400 and len(lines) >= 3:
            return False

        if total_len < 80 and len(lines) >= 2:
            return False

        return True

    def _extract_introduction_text(self, pdf_path: str) -> Optional[str]:
        """提取 Introduction 部分"""
        if not HAS_PYMUPDF:
            return None
            
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.warning(f"[PaperSearch] Failed to open PDF: {e}")
            return None

        introduction_text = []
        capturing = False

        start_pattern = re.compile(r"^(I|1)\.?\s*INTRODUCTION\b", re.IGNORECASE)
        start_simple_pattern = re.compile(r"^\bINTRODUCTION\b$", re.IGNORECASE)
        end_pattern = re.compile(r"^\s*(II|2)\.?\s+", re.IGNORECASE)
        common_next_sections_pattern = re.compile(r"^\s*(\bRELATED WORK\b|\bBACKGROUND\b|\bPRELIMINARIES\b)", re.IGNORECASE)

        try:
            for page in doc:
                blocks = page.get_text("blocks", sort=True)
                for block in blocks:
                    if block[6] != 0:
                        continue

                    block_text = block[4].strip()
                    if not block_text:
                        continue

                    first_line_of_block = block_text.split('\n')[0].strip()

                    if capturing:
                        if end_pattern.match(first_line_of_block) or common_next_sections_pattern.match(first_line_of_block):
                            capturing = False
                            break
                        else:
                            if not block_text.isdigit():
                                cleaned = self._clean_block(block_text)
                                if cleaned and self._is_paragraph_like(cleaned):
                                    introduction_text.append(cleaned)
                    else:
                        if start_pattern.match(first_line_of_block) or start_simple_pattern.match(first_line_of_block):
                            capturing = True
                            lines = block_text.split('\n')
                            if len(lines) > 1:
                                content_after_title = "\n".join(lines[1:]).strip()
                                if content_after_title:
                                    cleaned = self._clean_block(content_after_title)
                                    if cleaned and self._is_paragraph_like(cleaned):
                                        introduction_text.append(cleaned)
                if not capturing:
                    break
        finally:
            doc.close()

        if not introduction_text:
            return None
        return "\n\n".join(introduction_text)

    def _extract_related_work_text(self, pdf_path: str) -> Optional[str]:
        """提取 Related Work 部分"""
        if not HAS_PYMUPDF:
            return None
            
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.warning(f"[PaperSearch] Failed to open PDF: {e}")
            return None

        related_work_text = []
        capturing = False
        max_chars = 4000
        found_end = False

        start_pattern = re.compile(r"^\s*((\d+|[IVXLCDM]+)\.?\s+)?RELATED\s+WORK(S)?\b", re.IGNORECASE)
        start_simple_pattern = re.compile(r"^\s*RELATED\s+WORK(S)?\b", re.IGNORECASE)
        end_pattern = re.compile(r"^\s*((III|IV|V|VI|VII|VIII|IX|X)|[3-9])\.?\s+", re.IGNORECASE)
        common_next_sections_pattern = re.compile(
            r"^\s*(\bMETHODS?\b|\bMETHODOLOGY\b|\bEXPERIMENTS?\b|\bEVALUATION\b|"
            r"\bCONCLUSION(S)?\b|\bREFERENCES?\b|\bAPPENDIX\b)",
            re.IGNORECASE
        )

        try:
            for page in doc:
                blocks = page.get_text("blocks", sort=True)
                for block in blocks:
                    if block[6] != 0:
                        continue

                    block_text = block[4].strip()
                    if not block_text:
                        continue

                    first_line_of_block = block_text.split("\n")[0].strip()
                    header_text = " ".join(line.strip() for line in block_text.split("\n") if line.strip())

                    if capturing:
                        if end_pattern.match(header_text) or common_next_sections_pattern.match(header_text):
                            found_end = True
                            capturing = False
                            continue

                        if not block_text.isdigit():
                            cleaned = self._clean_block(block_text)
                            if cleaned and self._is_paragraph_like(cleaned):
                                related_work_text.append(cleaned)

                    else:
                        start_matched = start_pattern.match(header_text) or start_simple_pattern.match(header_text)
                        loose_matched = re.search(r"\bRELATED\s+WORK(S)?\b", header_text, re.IGNORECASE)
                        if start_matched or loose_matched:
                            capturing = True
                            lines = block_text.split("\n")
                            if len(lines) > 1:
                                content_after_title = "\n".join(lines[1:]).strip()
                                if content_after_title:
                                    cleaned = self._clean_block(content_after_title)
                                    if cleaned and self._is_paragraph_like(cleaned):
                                        related_work_text.append(cleaned)
        finally:
            doc.close()

        if not related_work_text:
            return None

        full_text = "\n\n".join(related_work_text)
        if not found_end or len(full_text) > max_chars:
            return full_text[:max_chars]
        return full_text

    def _search_semantic_scholar(self, query, **kwargs):
        """搜索 Semantic Scholar"""
        search_url = 'https://api.semanticscholar.org/graph/v1/paper/search'

        default_fields = [
            'paperId', 'title', 'openAccessPdf', 'externalIds', 'isOpenAccess',
            'abstract', 'tldr', 'citationCount', 'influentialCitationCount', 'authors', 'year'
        ]
        fields_list = kwargs.get('fields', default_fields)
        fields_str = ','.join(fields_list)

        settings = get_settings()
        default_limit = settings.paper_search_default_limit
        limit = kwargs.get('limit', default_limit)
        offset = kwargs.get('offset', 0)

        params = {
            'query': query,
            'limit': limit,
            'offset': offset,
            'fields': fields_str
        }

        logger.info(f"[PaperSearch] Querying Semantic Scholar: limit={limit}")

        headers = {}
        if settings.semantic_scholar_api_key:
            headers['x-api-key'] = settings.semantic_scholar_api_key

        try:
            self._respect_s2_rate_limit()
            response = requests.get(search_url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                logger.info(f"[PaperSearch] Found {len(results)} papers")
                return results
            else:
                logger.warning(f"[PaperSearch] API failed: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[PaperSearch] Request failed: {e}")
            return None

    def _get_download_url(
        self,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
        open_access_pdf: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """获取下载 URL"""
        # 优先级 1: Semantic Scholar OpenAccess
        if open_access_pdf and open_access_pdf.get("url"):
            pdf_url = open_access_pdf.get("url")
            if pdf_url and pdf_url.strip():
                return {"best_oa_url": pdf_url, "source": "semantic_scholar_openaccess"}

        # 优先级 2: ArXiv
        if arxiv_id:
            arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return {"best_oa_url": arxiv_url, "source": "arxiv_direct"}

        # 优先级 3: Unpaywall
        if doi:
            return self._get_oa_url(doi=doi)

        return {"best_oa_url": None, "source": None}

    def _get_oa_url(self, doi: str) -> Dict[str, Any]:
        """通过 Unpaywall 获取开放获取链接"""
        base_url = "https://api.unpaywall.org/v2/"
        settings = get_settings()
        email = getattr(settings, "unpaywall_email", "placeholder@example.com")

        request_url = f"{base_url}{doi}"
        params = {"email": email}

        try:
            response = requests.get(request_url, params=params, timeout=10)
            if response.status_code == 404:
                return {"best_oa_url": None, "source": "unpaywall"}
            response.raise_for_status()
            data = response.json()

            best_location = data.get("best_oa_location") or {}
            pdf_url = best_location.get("url_for_pdf") or best_location.get("url")

            if not pdf_url and isinstance(data.get("oa_locations"), list):
                for location in data["oa_locations"]:
                    pdf_url = location.get("url_for_pdf") or location.get("url")
                    if pdf_url:
                        break

            if pdf_url:
                logger.debug(f"[PaperSearch] Found OA URL via Unpaywall: {pdf_url}")
                return {"best_oa_url": pdf_url, "source": "unpaywall"}

            return {"best_oa_url": None, "source": "unpaywall"}

        except requests.exceptions.RequestException as exc:
            logger.debug(f"[PaperSearch] Unpaywall failed: {exc}")
            return {"best_oa_url": None, "source": "unpaywall"}
