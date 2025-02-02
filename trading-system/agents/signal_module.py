from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from crewai import Agent
from loguru import logger
from .tools.parser_tools import SignalParserTool, TelegramListenerTool
from .utils.llm_providers import LLMProvider, LLMFactory


def create_signal_parser_agent(
    name: str,
    telegram_config: Dict[str, Any],
    message_callback: Optional[Callable] = None,
    llm_config: Optional[Dict[str, Any]] = None
) -> Agent:
    """Create signal parser agent"""
    # Initialize tools
    parser_tool = SignalParserTool()
    telegram_tool = TelegramListenerTool(
        api_id=telegram_config.get('api_id'),
        api_hash=telegram_config.get('api_hash'),
        session_token=telegram_config.get('session_token'),
        channel_url=telegram_config.get('channel_url'),
        message_callback=message_callback
    )

    # Initialize LLM provider
    provider_type = LLMProvider(llm_config.get("provider", "openai"))
    llm_provider = LLMFactory.create_provider(provider_type, llm_config)
    if not llm_provider:
        raise ValueError(f"Failed to create LLM provider: {provider_type}")

    # Create and return agent
    return Agent(
        name=name,
        role="Signal Parser",
        goal="Parse and validate trading signals",
        backstory="""You are a signal parser responsible for monitoring Telegram channels,
        extracting trading signals, and validating their format and content. You ensure
        signals are properly formatted and contain all required information.""",
        tools=[telegram_tool, parser_tool],
        llm=llm_provider.get_crew_llm(temperature=llm_config.get("temperature", 0.7)),
        verbose=True
    )


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