from typing import Dict, Any, List, Optional
from crewai import Agent
from loguru import logger
from crewai.tools import BaseTool


class BaseAgent:
    """Base class for all agents in the system"""

    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        llm_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[BaseTool]] = None
    ):
        """Initialize base agent"""
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm_config = llm_config or {}
        self.tools = tools or []

        # Create CrewAI agent
        self.agent = Agent(
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            llm_config=self.llm_config,
            tools=self.tools,
            verbose=True
        )

    def add_tool(self, tool: BaseTool):
        """Add tool to agent"""
        try:
            self.tools.append(tool)
            logger.info(f"Tool {tool.name} added to agent {self.name}")
        except Exception as e:
            logger.error(f"Error adding tool to agent {self.name}: {e}")
            raise

    async def initialize(self) -> bool:
        """Initialize agent"""
        try:
            logger.info(f"Initializing agent {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error initializing agent {self.name}: {e}")
            return False

    async def run(self):
        """Run agent's main loop"""
        raise NotImplementedError("Subclasses must implement run()")

    async def cleanup(self):
        """Cleanup agent resources"""
        try:
            logger.info(f"Cleaning up agent {self.name}")
        except Exception as e:
            logger.error(f"Error cleaning up agent {self.name}: {e}")
            raise
