from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from crewai import Agent, Task
from loguru import logger
from .tools.parser_tools import SignalParserTool


def create_signal_parser_agent(
    name: str,
    llm: Any,
) -> Agent:
    """Create signal parser agent"""
    # Initialize tools
    parser_tool = SignalParserTool()
    # Create and return agent
    agent = Agent(
        name=name,
        role="Signal Parser",
        goal="Parse and validate trading signals",
        backstory="""You are a signal parser responsible for monitoring Telegram channels,
        extracting trading signals, and validating their format and content. You ensure
        signals are properly formatted and contain all required information.""",
        tools=[parser_tool],
        llm=llm,
        verbose=True
    )

    return agent


async def cleanup_signal_tools(agent: Agent):
    """Cleanup signal module tools"""
    if not agent or not hasattr(agent, 'tools'):
        logger.warning("No agent or tools to cleanup")
        return

    cleanup_errors = []
    for tool in agent.tools:
        try:
            if hasattr(tool, 'cleanup'):
                logger.info(f"Cleaning up tool: {tool.name}")
                await tool.cleanup()
                logger.info(f"Successfully cleaned up tool: {tool.name}")
        except Exception as e:
            error_msg = f"Error cleaning up tool {tool.name}: {e}"
            logger.error(error_msg)
            cleanup_errors.append(error_msg)
    
    if cleanup_errors:
        raise Exception("Errors during signal tools cleanup: " + "; ".join(cleanup_errors)) 