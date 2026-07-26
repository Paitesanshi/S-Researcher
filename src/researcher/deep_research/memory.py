"""
Agent Memory for Deep Research Module
Adapted from OnePage/deep_research_agent
"""

from typing import List, Dict, Any
from loguru import logger


class AgentMemory:
    """存储论文和上下文的内存管理器"""
    
    def __init__(self):
        self.context_log: List[str] = []
        self.papers: Dict[str, Dict[str, Any]] = {}  # 存储论文，key 为 paperId

    def add_context(self, item: str) -> None:  
        self.context_log.append(item)
        logger.debug(f"Memory: Added context -> {item[:100]}...")

    def list_context(self) -> List[str]:
        return list(self.context_log)
    
    def store_papers_batch(self, papers: List[Dict[str, Any]]) -> List[str]:
        """
        批量存储论文到内存
        
        Args:
            papers: 论文列表，每个论文是一个字典
        
        Returns:
            存储的论文 ID 列表
        """
        stored_ids = []
        for paper in papers:
            paper_id = paper.get('paperId') or paper.get('id') or f"paper_{len(self.papers)}"
            self.papers[paper_id] = paper
            stored_ids.append(paper_id)
        
        logger.info(f"Memory: Stored {len(stored_ids)} papers")
        return stored_ids
    
    def get_all_papers(self) -> List[Dict[str, Any]]:
        """
        获取所有存储的论文
        
        Returns:
            论文列表
        """
        return list(self.papers.values())
    
    def clear(self) -> None:
        """清空内存"""
        self.context_log.clear()
        self.papers.clear()
        logger.debug("Memory: Cleared all data")
