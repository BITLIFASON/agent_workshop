from typing import Dict, Any, Optional, Callable
from crewai import Agent, Task
from loguru import logger
from .tools.bybit_tools import BybitTradingTool, BybitBalanceTool
from .tools.balance_tools import ReadDatabaseTool, ManagementServiceTool
from .tools.write_info_tools import WriteDatabaseTool


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
    read_db_tool = ReadDatabaseTool(
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
        goal="Calculation of the best quantity of the transaction",
        backstory="""You are responsible for calculating the quantity of the transaction
        based on information from the management system
        and the parameters of the coin on bybit following the restrictions.
        You also need to manage the information in the database.
        Your course of action:
        1) Check management system status
        (if system is disable you must set quantity to zero)
        2) Check limitation of management system (available balance, available lots, price limit)
        (if system limitation is not follow you must set quantity to zero)
        3) Check lots in database
        (if you have a lot the coin in database you must set quantity to zero)
        4) Check the parameters of the coin on bybit
        (if coin parameters is not follow (maxOrderQty, minOrderQty, minNotionalValue) you must set quantity to zero)
        5) Calculate the best coin quantity based on the available information
        (if coin quantity is calculated, it's must less maxOrderQty, greater minOrderQty, also coin price multiply calculated coin quantity greater minNotionalValue)
        (distribute the balance uniform between the lots)
        """,
        tools=[management_tool, read_db_tool, balance_tool],
        llm=llm,
        verbose=True,
        max_iter=15
    )

    return agent


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
        (if quantity is zero you must use skip operation)""",
        tools=[trading_tool],
        llm=llm,
        verbose=True,
        max_iter=3
    )
    
    return agent


def create_write_info_agent(
    name: str,
    config: Dict[str, Dict[str, Any]],
    llm: Any
) -> Agent:
    """Create write info agent"""
    # Initialize tool
    db_config = config.get('database', {})
    write_db_tool = WriteDatabaseTool(
        host=db_config.get('host'),
        port=db_config.get('port'),
        user=db_config.get('user'),
        password=db_config.get('password'),
        database=db_config.get('database')
    )

    # Create and return agent
    agent = Agent(
        name=name,
        role="Info Database Writer",
        goal="Write information about order to database",
        backstory="""You perform actions to record information about the result of the system.
        Your instruction of actions:
        1) Create active lot and history lot if order is buy
        2) Delete active lot and create history lot if order is sell
        (if quantity is zero you must skip any operation)
        """,
        tools=[write_db_tool],
        llm=llm,
        verbose=True,
        max_iter=5
    )
    
    return agent