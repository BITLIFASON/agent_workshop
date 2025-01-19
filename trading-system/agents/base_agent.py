from typing import Optional, Dict, Any
from pydantic import BaseModel
from loguru import logger
from abc import ABC, abstractmethod

class AgentState(BaseModel):
    """Base state model for agents"""
    is_active: bool = False
    last_action: Optional[str] = None
    last_error: Optional[str] = None
    context: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Base class for all agents in the system"""

    def __init__(self, name: str):
        self.name = name
        self.state = AgentState()
        self.tools = []
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger for the agent"""
        logger.add(
            f"logs/{self.name}.log",
            rotation="500 MB",
            level="INFO",
            format="{time} | {level} | {message}"
        )
        self.logger = logger.bind(agent=self.name)

    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main execution method for the agent"""
        pass

    @abstractmethod
    async def initialize(self):
        """Initialize agent's resources"""
        pass

    async def cleanup(self):
        """Cleanup agent's resources"""
        self.state.is_active = False
        self.logger.info(f"Agent {self.name} cleaned up")

    def add_tool(self, tool):
        """Add a tool to the agent"""
        self.tools.append(tool)
        self.logger.info(f"Tool {tool.__class__.__name__} added to agent {self.name}")

    def get_state(self) -> AgentState:
        """Get current agent state"""
        return self.state

    def update_context(self, key: str, value: Any):
        """Update agent's context"""
        self.state.context[key] = value
        self.logger.debug(f"Context updated: {key}={value}")
