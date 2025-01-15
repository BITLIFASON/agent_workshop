import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv('envs/parsing.env')

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')

client = TelegramClient('parsing_session', API_ID, API_HASH)

client.start()
client.disconnect()


