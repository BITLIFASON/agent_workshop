import sys
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from loguru import logger
import asyncio
from crewai import Crew


class TelegramParser:
    def __init__(self, config):
        """
        Initialize TelegramParser.
        """
        self.config = config
        self.crew = None
        self.telegram_client = None

    async def initialize(self) -> bool:
        """
        Initialize the parser service.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            self.telegram_client = await self._init_telegram_client()
            logger.info("Telegram client successfully initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            return False

    async def _init_telegram_client(self) -> TelegramClient:
        """
        Initialize the Telegram client.

        Returns:
            telethon.TelegramClient: The Telegram client.
        Raises:
            Exception: If an error occurs during initialization.
        """

        client = TelegramClient(StringSession(self.config.session_token),
                                self.config.api_id,
                                self.config.api_hash,
                                system_version='4.16.30-vxMANUAL')
        await client.start()
        return client

    async def set_crew(self, crew: Crew):
        """Setting crew"""
        self.crew = crew

    async def start_listening(self):
        """
        Start listening for new messages on the specified Telegram channel.

        Returns:
            None
        Raises:
            Exception: If an error occurs during setup.
        """
        try:
            @self.telegram_client.on(events.NewMessage(chats=[self.config.channel_url]))
            async def new_message_handler(event):
                message = event.message
                text_message = message.message
                await self.crew.kickoff({"message": text_message})

            if not self.telegram_client.is_connected():
                max_retries_telegram = 0
                while True:
                    logger.warning("Telegram connection lost, trying to reconnect...")
                    self.telegram_client = await self._init_telegram_client()
                    await asyncio.sleep(10)
                    if max_retries_telegram == self.config.max_retries:
                        raise Exception("Maximum retries reached")
                    max_retries_telegram += 1

            await self.telegram_client.run_until_disconnected()

        except Exception as e:
            logger.error(f"Error in Telegram listener: {e}")
            raise

    async def start(self):
        """
        Start the parser service.

        Returns:
            None
        Raises:
            Exception: If an error occurs during startup.
        """
        try:
            initialized = await self.initialize()
            if not initialized:
                raise Exception("Failed to initialize parser service")

            logger.info("Starting parser service...")
            await self.start_listening()
        except Exception as e:
            logger.error(f"Error starting parser service: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """
        Cleanup resources.

        Returns:
            None
        """
        if self.telegram_client:
            await self.telegram_client.disconnect()
            logger.info("Telegram client disconnected.")