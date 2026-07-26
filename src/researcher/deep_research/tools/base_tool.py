"""
Base Tool for Deep Research Module
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @abstractmethod
    def run(self, **kwargs) -> Any:
        """执行工具"""
        pass
