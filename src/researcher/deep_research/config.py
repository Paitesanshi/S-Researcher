"""
Configuration for Deep Research Module
Adapted from OnePage/deep_research_agent with YuLan-OneSim integration
"""

import os
from typing import Optional
from loguru import logger


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


class Settings:
    """
    统一读取与暴露项目所需的环境变量。
    """

    def __init__(self):
        # Optional direct OpenAI-compatible endpoint for this module. When it
        # is not configured, deep research uses OneSim's selected model.
        self.model_base_url: str = (
            _get_env("SCI_MODEL_BASE_URL")
            or _get_env("LLM_BASE_URL")
            or _get_env("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        self.llm_model: Optional[str] = (
            _get_env("SCI_LLM_MODEL")
            or _get_env("LLM_MODEL")
            or _get_env("OPENAI_MODEL")
            or _get_env("DEEPSEEK_MODEL")
        )
        self.model_api_key: Optional[str] = (
            _get_env("SCI_MODEL_API_KEY")
            or _get_env("LLM_API_KEY")
            or _get_env("OPENAI_API_KEY")
            or _get_env("DEEPSEEK_API_KEY")
        )
        
        # Optional Semantic Scholar API key. Public rate limits are used when
        # the environment variable is not set.
        self.semantic_scholar_api_key: Optional[str] = _get_env(
            "SEMANTIC_SCHOLAR_API_KEY"
        )
        
        # Unpaywall email
        self.unpaywall_email: str = _get_env("UNPAYWALL_EMAIL", "research@example.com")
        
        # GROBID URL
        self.grobid_url: str = _get_env("GROBID_URL", "http://localhost:8070")

        # 并发配置
        try:
            self.pdf_parser_max_concurrency: int = int(_get_env("PDF_PARSER_MAX_CONCURRENCY", "2"))
            if self.pdf_parser_max_concurrency < 1:
                self.pdf_parser_max_concurrency = 4
        except Exception:
            self.pdf_parser_max_concurrency = 4

        # Executor 并发数
        try:
            self.max_workers: int = int(_get_env("EXECUTOR_MAX_WORKERS", "10"))
            if self.max_workers < 1:
                self.max_workers = 10
        except Exception:
            self.max_workers = 10

        # PaperSearch 并行下载数
        try:
            self.parallel_downloads: int = int(_get_env("PAPER_SEARCH_PARALLEL_DOWNLOADS", "4"))
            if self.parallel_downloads < 1:
                self.parallel_downloads = 4
        except Exception:
            self.parallel_downloads = 4

        # PaperSearch 默认返回数量
        try:
            self.paper_search_default_limit: int = int(_get_env("PAPER_SEARCH_DEFAULT_LIMIT", "6"))
            if self.paper_search_default_limit < 1:
                self.paper_search_default_limit = 6
        except Exception:
            self.paper_search_default_limit = 6


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
