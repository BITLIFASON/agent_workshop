from typing import Dict, Any, Optional, Callable
from crewai import Agent, Task
from loguru import logger
from .tools.bybit_tools import BybitTradingTool, BybitBalanceTool
from .tools.balance_tools import DatabaseTool, ManagementServiceTool


def create_trading_executor_agent(
    name: str,
    bybit_config: Dict[str, Any],
    llm: Any
) -> Agent:
    """Create trading executor agent"""
    # Initialize trading tool
    trading_tool = BybitTradingTool(
        api_key=bybit_config.get('api_key'),
        api_secret=bybit_config.get('api_secret'),
        demo_mode=bybit_config.get('demo_mode', True)
    )

    # Create and return agent
    agent = Agent(
        name=name,
        role="Trading Executor",
        goal="Execute trades on exchange accurately and efficiently",
        backstory="""You are a trading executor responsible for placing and managing orders
        on the Bybit exchange. You ensure trades are executed with proper parameters and
        monitor their execution status.""",
        tools=[trading_tool],
        llm=llm,
        verbose=True,
        max_iter=2
    )
    
    return agent


def create_balance_controller_agent(
    name: str,
    config: Dict[str, Dict[str, Any]],
    llm: Any
) -> Agent:
    """Create balance controller agent"""
    # Initialize tools
    management_config = config.get('management_api', {})
    management_tool = ManagementServiceTool(
        host=management_config.get('host'),
        port=management_config.get('port'),
        token=management_config.get('token')
    )

    db_config = config.get('database', {})
    db_tool = DatabaseTool(
        host=db_config.get('host'),
        port=db_config.get('port'),
        user=db_config.get('user'),
        password=db_config.get('password'),
        database=db_config.get('database')
    )

    bybit_config = config.get('bybit', {})
    balance_tool = BybitBalanceTool(
        api_key=bybit_config.get('api_key'),
        api_secret=bybit_config.get('api_secret'),
        demo_mode=bybit_config.get('demo_mode', True)
    )

    # Create and return agent
    agent = Agent(
        name=name,
        role="Balance Controller",
        goal="Monitor and control trading balance",
        backstory="""You are responsible for managing trading balances and ensuring
        compliance with system limits. You monitor system status, verify price limits,
        and manage trading lots.""",
        tools=[management_tool, db_tool, balance_tool],
        llm=llm,
        verbose=True,
        max_iter=6
    )
    
    return agent