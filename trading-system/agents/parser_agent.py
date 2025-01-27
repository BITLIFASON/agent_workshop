from datetime import datetime, timedelta
from crewai import Agent, Crew
from .base_agent import BaseAgent
from .tools.parser_tools import SignalData, SignalParserTool, TelegramListenerTool
import asyncio
from typing import Dict, Any, Callable, Optional
from loguru import logger


class ParserAgent(BaseAgent):
    """Agent for parsing trading signals from Telegram"""

    def __init__(
        self,
        name: str,
        api_id: int,
        api_hash: str,
        api_session_token: str,
        channel_url: str,
        message_callback: Optional[Callable] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize ParserAgent"""
        super().__init__(
            name=name,
            role="Signal Parser",
            goal="Parse and validate trading signals",
            backstory="""You are a signal parser responsible for monitoring Telegram channels,
            extracting trading signals, and validating their format and content. You ensure
            signals are properly formatted and contain all required information.""",
            llm_config=llm_config,
            tools=[]
        )

        # Initialize tools
        self.telegram_tool = TelegramListenerTool(
            api_id=api_id,
            api_hash=api_hash,
            session_token=api_session_token,
            channel_url=channel_url,
            message_callback=message_callback
        )
        
        self.parser_tool = SignalParserTool()
        self.tools = [self.telegram_tool, self.parser_tool]

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        llm = self.llm_provider.get_crew_llm(temperature=0.7)
        
        self.signal_parser = Agent(
            role="Signal Parser",
            goal="Extract accurate trading signals from messages",
            backstory="""You are an expert in analyzing trading signals from various sources.
            You can identify key trading information and filter out noise.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.parser_tool],
            llm=llm
        )

        self.signal_validator = Agent(
            role="Signal Validator",
            goal="Validate and enhance trading signals",
            backstory="""You are a trading signal validator who ensures signals are accurate,
            complete, and meaningful. You check for missing data and validate price levels.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.parser_tool],
            llm=llm
        )

        self.crew = Crew(
            agents=[self.signal_parser, self.signal_validator],
            tasks=[],
            verbose=True
        )

    async def process_message(self, event):
        """Process incoming Telegram message"""
        try:
            if not self.state.is_active:
                self.logger.warning("Agent not active, skipping message processing")
                return

            message_text = event.message.message.strip()
            self.logger.info(f"Processing message: {message_text}")

            # Parse signal using parser tool
            signal = await self.parser_tool._arun(message=message_text)
            
            if not signal:
                self.logger.warning("Failed to parse message as trading signal")
                return

            # Update agent state
            self.state.last_action = f"Parsed {signal.action} signal for {signal.symbol}"

            # Validate signal timing
            if self._is_signal_valid(signal):
                # Convert to dict and add timestamp
                signal_dict = signal.model_dump()
                signal_dict["timestamp"] = signal.timestamp
                
                await self.message_callback(signal_dict)
                self.logger.info(f"Signal processed: {signal_dict}")
            else:
                self.logger.warning(f"Signal outdated: {signal}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.state.last_error = str(e)

    def _is_signal_valid(self, signal: SignalData) -> bool:
        """Check if the signal is still valid based on timing"""
        try:
            now = datetime.now()
            signal_time = signal.timestamp

            # Buy signals valid for 30 minutes, sell signals for 24 hours
            if signal.action == 'buy':
                is_valid = now - signal_time < timedelta(minutes=30)
            else:
                is_valid = now - signal_time < timedelta(hours=24)

            if not is_valid:
                self.logger.warning(
                    f"Signal expired: {signal.action} signal for {signal.symbol} "
                    f"from {signal_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            return is_valid

        except Exception as e:
            self.logger.error(f"Error validating signal timing: {e}")
            return False

    async def run(self):
        """Run the agent's main loop"""
        try:
            logger.info(f"Starting {self.name}")
            await self.telegram_tool._arun()
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            raise

    async def initialize(self) -> bool:
        """Initialize agent and its tools"""
        try:
            logger.info(f"Initializing {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error initializing {self.name}: {e}")
            return False

    async def cleanup(self):
        """Cleanup agent resources"""
        try:
            logger.info(f"Cleaning up {self.name}")
            await self.telegram_tool.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up {self.name}: {e}")
            raise
