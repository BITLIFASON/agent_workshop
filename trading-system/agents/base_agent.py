from typing import Optional, Dict, Any
from pydantic import BaseModel
from loguru import logger
from abc import ABC, abstractmethod
from utils.llm_providers import LLMProvider, LLMFactory

class AgentState(BaseModel):
    """Base state model for agents"""
    is_active: bool = False
    last_action: Optional[str] = None
    last_error: Optional[str] = None
    context: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Base class for all agents in the system"""

    def __init__(self, name: str, llm_config: Dict[str, Any]):
        self.name = name
        self.state = AgentState()
        self.tools = []
        self._setup_logger()
        
        # Initialize LLM provider
        provider_type = LLMProvider(llm_config.get("provider", "openai"))
        self.llm_provider = LLMFactory.create_provider(provider_type, llm_config)
        if not self.llm_provider:
            raise ValueError(f"Failed to create LLM provider: {provider_type}")

    def _setup_logger(self):
        """Setup logger for the agent"""
        logger.add(
            f"logs/{self.name}.log",
            rotation="500 MB",
            level="INFO",
            format="{time} | {level} | {message}"
        )
        self.logger = logger.bind(agent=self.name)

    async def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for CrewAI"""
        if not self.llm_provider:
            raise ValueError("LLM provider not initialized")
        return await self.llm_provider.get_llm_config()

    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main execution method for the agent"""
        pass

    @abstractmethod
    async def initialize(self):
        """Initialize agent's resources"""
        # Initialize LLM provider first
        if not await self.llm_provider.initialize():
            self.logger.error("Failed to initialize LLM provider")
            return False
        return True

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
