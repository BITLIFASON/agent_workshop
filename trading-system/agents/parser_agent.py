from datetime import datetime, timedelta
from crewai import Agent, Crew
from .base_agent import BaseAgent
from .tools.parser_tools import SignalData, SignalParserTool, TelegramListenerTool
import asyncio


class ParserAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        api_id: int,
        api_hash: str,
        api_session_token: str,
        channel_url: str,
        message_callback,
        openai_api_key: str
    ):
        super().__init__(name)
        self.channel_url = channel_url
        self.message_callback = message_callback
        self.openai_api_key = openai_api_key

        # Initialize Telegram tool
        self.telegram_tool = TelegramListenerTool(api_id, api_hash, api_session_token)
        self.telegram_tool.add_message_handler(self.process_message)
        self.add_tool(self.telegram_tool)

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        # Create tools
        self.parser_tool = SignalParserTool()
        
        self.signal_parser = Agent(
            role="Signal Parser",
            goal="Extract accurate trading signals from messages",
            backstory="""You are an expert in analyzing trading signals from various sources.
            You can identify key trading information and filter out noise.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.parser_tool],
            llm_config={"api_key": self.openai_api_key}
        )

        self.signal_validator = Agent(
            role="Signal Validator",
            goal="Validate and enhance trading signals",
            backstory="""You are a trading signal validator who ensures signals are accurate,
            complete, and meaningful. You check for missing data and validate price levels.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.parser_tool],  # Use the same tool for validation
            llm_config={"api_key": self.openai_api_key}
        )

        self.crew = Crew(
            agents=[self.signal_parser, self.signal_validator],
            tasks=[],
            verbose=True
        )

    async def process_message(self, event):
        """Process incoming Telegram message using Crew AI"""
        try:
            if not self.state.is_active:
                self.logger.warning("Agent not active, skipping message processing")
                return

            message_text = event.message.message.strip()
            self.logger.info(f"Processing message: {message_text}")

            # Parse signal using parser tool
            signal = await self.parser_tool._arun(message_text)
            
            if not signal:
                self.logger.warning("Failed to parse message as trading signal")
                return

            # Update agent state
            self.state.last_action = f"Parsed {signal.action} signal for {signal.symbol}"

            # Validate signal timing
            if self._is_signal_valid(signal):
                # Convert to dict and add timestamp
                signal_dict = signal.dict()
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
        """Main execution loop"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            result = await self.telegram_tool.start_listening(self.channel_url)
            if not result['success']:
                self.logger.error(f"Failed to start listening: {result.get('error')}")
                return

            # Keep the agent running
            while self.state.is_active:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            self.state.last_error = str(e)
            self.state.is_active = False

    async def initialize(self):
        """Initialize the parser agent"""
        self.logger.info("Initializing Parser Agent...")
        result = await self.telegram_tool.initialize()
        if not result['success']:
            self.logger.error(f"Failed to initialize Telegram tool: {result.get('error')}")
            return False

        self.state.is_active = True
        return True

    async def cleanup(self):
        """Cleanup resources"""
        await self.telegram_tool.cleanup()
        await super().cleanup()
