import json
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from pika import ConnectionParameters, PlainCredentials, BlockingConnection, BasicProperties
from pika.exceptions import StreamLostError
from loguru import logger


async def init_telegram_client() -> TelegramClient:
    """
    Initialize the Telegram client.

    Returns:
        telethon.TelegramClient: The Telegram client.
    Raises:
        Exception: If an error occurs during initialization.
    """

    client = TelegramClient("parsing_session",
                            int(os.getenv("API_ID", 0)),
                            os.getenv("API_HASH", ""))
    await client.start()
    return client

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        Override the JSON encoding for datetime objects.

        Args:
            obj (datetime): The datetime object to be encoded.

        Returns:
            str: The serialized datetime string.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime object to ISO format string
        elif isinstance(obj, timedelta):
            return str(obj)  # Convert timedelta object to string
        else:
            return super().default(obj)

class RabbitClient:
    def __init__(self):
        """
        Initialize the RabbitMQ client.

        Returns:
            None
        Raises:
            Exception: If an error occurs during initialization.
        """

        self.connection = None
        self.channel = None
        self.queue_name = os.getenv('QUEUE_NAME', '')

        self.rabbitmq_params = ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', ''),
            port=int(os.getenv('RABBITMQ_PORT', 5672)),
            credentials=PlainCredentials(os.getenv('RABBITMQ_DEFAULT_USER', 'guest'),
                                         os.getenv('RABBITMQ_DEFAULT_PASS', 'guest'))
        )

    async def _publish(self, msg):
        """
        Publish a message to the specified RabbitMQ queue.

        Args:
            msg (str): The message body to be published.

        Returns:
            None
        Raises:
            Exception: If an error occurs during publishing or connection.
        """
        self.channel.basic_publish(exchange='',
                                   routing_key=self.queue_name,
                                   body=msg,
                                   properties=BasicProperties(content_type='application/json'))

    async def publish(self, msg):
        """
        Publish a JSON-serialized message to the RabbitMQ queue.

        Args:
            msg: The message body to be published.

        Returns:
            None
        Raises:
            Exception: If an error occurs during publishing or connection.
        """

        json_msg = json.dumps(msg, cls=DateTimeEncoder)

        try:
            await self._publish(json_msg)
            logger.info(f"Message was published: {json_msg}")
        except StreamLostError:
            logger.error("RabbitMQ connection lost, trying to reconnect...")
            await self.connect()
            logger.info("RabbitMQ client successfully connected.")
            await self._publish(json_msg)

    async def connect(self):
        """
        Establish a connection to the RabbitMQ server and create a channel.

        Returns:
            None
        Raises:
            Exception: If an error occurs during connection setup or channel creation.
        """
        self.connection = BlockingConnection(self.rabbitmq_params)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name)

    async def close(self):
        """
        Close the RabbitMQ connection.

        Returns:
            None
        Raises:
            Exception: If an error occurs during closing.
        """
        if self.connection and self.connection.is_open:
            self.connection.close()
