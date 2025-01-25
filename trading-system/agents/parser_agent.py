from typing import Dict, Any
from datetime import datetime, timedelta
from telethon import events
from crewai import Agent, Task, Crew
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from .tools.parser_tools import SignalData, SignalParserTool, TelegramListenerTool


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
        self.add_tool(self.telegram_tool)

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        self.signal_parser = Agent(
            role="Signal Parser",
            goal="Extract accurate trading signals from messages",
            backstory="""You are an expert in analyzing trading signals from various sources.
            You can identify key trading information and filter out noise.""",
            verbose=True,
            allow_delegation=False,
            tools=[SignalParserTool()],
            llm_config={"api_key": self.openai_api_key}
        )

        self.signal_validator = Agent(
            role="Signal Validator",
            goal="Validate and enhance trading signals",
            backstory="""You are a trading signal validator who ensures signals are accurate,
            complete, and meaningful. You check for missing data and validate price levels.""",
            verbose=True,
            allow_delegation=False,
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
            # Create parsing task
            parsing_task = Task(
                description=f"Parse the following message into a trading signal: {event.message.message}",
                agent=self.signal_parser
            )

            # Create validation task
            validation_task = Task(
                description="Validate the parsed signal data and enhance it if needed",
                agent=self.signal_validator
            )

            # Execute tasks
            self.crew.tasks = [parsing_task, validation_task]
            result = await self.crew.kickoff()

            if isinstance(result, SignalData):
                # Update agent state
                self.state.last_action = f"Parsed signal for {result.symbol}"

                # Validate signal timing
                if self._is_signal_valid(result):
                    await self.message_callback(result.dict())
                    self.logger.info(f"Signal processed: {result}")
                else:
                    self.logger.warning(f"Signal outdated: {result}")
            else:
                self.logger.warning("Failed to parse signal from message")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.state.last_error = str(e)

    def _is_signal_valid(self, signal: SignalData) -> bool:
        """Check if the signal is still valid based on timing"""
        now = datetime.now()
        signal_time = signal.timestamp

        if signal.action == 'buy':
            return now - signal_time < timedelta(minutes=30)
        else:
            return now - signal_time < timedelta(hours=24)

    async def run(self):
        """Main execution loop"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            @self.telegram_tool.client.on(events.NewMessage(chats=[self.channel_url]))
            async def message_handler(event):
                await self.process_message(event)

            self.logger.info(f"Started listening to channel: {self.channel_url}")
            await self.telegram_tool.client.run_until_disconnected()

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            self.state.last_error = str(e)
            self.state.is_active = False

    async def initialize(self):
        """Initialize the parser agent"""
        self.logger.info("Initializing Parser Agent...")
        result = await self.telegram_tool.initialize()
        if not result.success:
            self.logger.error(f"Failed to initialize Telegram tool: {result.error}")
            return False

        self.state.is_active = True
        return True

    async def cleanup(self):
        """Cleanup resources"""
        await self.telegram_tool.cleanup()
        await super().cleanup()
