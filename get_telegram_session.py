import os
from telethon import TelegramClient

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')

client = TelegramClient('backtesting_session', API_ID, API_HASH)

client.start()
client.disconnect()


