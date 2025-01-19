from typing import Any, Optional
from pydantic import BaseModel
from abc import ABC, abstractmethod

class ToolResult(BaseModel):
    """Base model for tool execution results"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

class BaseTool(ABC):
    """Base class for all tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, *args, **kwargs) -> ToolResult:
        """Execute the tool's main functionality"""
        pass

    def get_description(self) -> str:
        """Get tool description"""
        return self.description
