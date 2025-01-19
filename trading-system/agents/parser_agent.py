from typing import Dict, Any
from datetime import datetime, timedelta
from telethon import events
from .base_agent import BaseAgent
from .tools.parser_tools import TelegramListenerTool, SignalParserTool

class ParserAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        api_id: int,
        api_hash: str,
        api_session_token: str,
        channel_url: str,
        message_callback
    ):
        super().__init__(name)
        self.channel_url = channel_url
        self.message_callback = message_callback

        # Initialize tools
        self.telegram_tool = TelegramListenerTool(api_id, api_hash, api_session_token)
        self.parser_tool = SignalParserTool()

        self.add_tool(self.telegram_tool)
        self.add_tool(self.parser_tool)

    async def initialize(self):
        """Initialize the parser agent"""
        self.logger.info("Initializing Parser Agent...")
        result = await self.telegram_tool.initialize()
        if not result.success:
            self.logger.error(f"Failed to initialize Telegram tool: {result.error}")
            return False

        self.state.is_active = True
        return True

    async def process_message(self, event):
        """Process incoming Telegram message"""
        try:
            # Parse the message
            result = await self.parser_tool.execute(event.message.message)
            if not result.success:
                self.logger.error(f"Failed to parse message: {result.error}")
                return

            signal = result.data
            if signal:
                # Update agent state
                self.state.last_action = f"Parsed signal for {signal['symbol']}"

                # Validate signal timing
                if self._is_signal_valid(signal):
                    # Send signal to callback
                    await self.message_callback(signal)
                    self.logger.info(f"Signal processed: {signal}")
                else:
                    self.logger.warning(f"Signal outdated: {signal}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.state.last_error = str(e)

    def _is_signal_valid(self, signal: Dict[str, Any]) -> bool:
        """Check if the signal is still valid based on timing"""
        now = datetime.now()
        signal_time = signal['timestamp']

        if signal['action'] == 'buy':
            # Buy signals valid for 30 minutes
            return now - signal_time < timedelta(minutes=30)
        else:
            # Sell signals valid for 24 hours
            return now - signal_time < timedelta(hours=24)

    async def run(self):
        """Main execution loop"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            # Setup message handler
            @self.telegram_tool.client.on(events.NewMessage(chats=[self.channel_url]))
            async def message_handler(event):
                await self.process_message(event)

            self.logger.info(f"Started listening to channel: {self.channel_url}")
            await self.telegram_tool.client.run_until_disconnected()

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            self.state.last_error = str(e)
            self.state.is_active = False

    async def cleanup(self):
        """Cleanup resources"""
        await self.telegram_tool.cleanup()
        await super().cleanup()
