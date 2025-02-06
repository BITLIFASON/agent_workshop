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
        goal="Execute trades on exchange reliable",
        backstory="""You are a trading executor responsible for placing and managing orders
        on the Bybit exchange. You ensure trades are executed with proper parameters and
        monitor their execution status.
        (if you have a lot the coin in database you don't must execute "Buy" the trade)
        (if quantity coin is zero you must execute skip the trade)""",
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
        goal="Formation of the best terms of the transaction",
        backstory="""You are responsible for forming the terms of the transaction
        based on information from the management system
        and the parameters of the coin on bybit following the restrictions.
        You also need to manage the information in the database.
        Your course of action:
        1) Check management system status
        (if system is disable you must install coin quantity is zero and don't add lot to database)
        2) Check limitation of management system
        (if system limitation is not follow you must install coin quantity is zero)
        3) Check lots in database
        (if you have a lot the coin in database you must install coin quantity is zero)
        4) Check the parameters of the coin on bybit
        5) Form the best terms of the transaction
        (distribute the balance evenly between the lots)
        6) Add lot to "active_lots" and "history_lots" tables in database
        (if coin quantity is zero you don't have lot to database)
        """,
        
        tools=[management_tool, db_tool, balance_tool],
        llm=llm,
        verbose=True,
        max_iter=6
    )
    
    return agent