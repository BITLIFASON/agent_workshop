import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession


load_dotenv('../envs/parsing.env')

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')

with TelegramClient(StringSession(), API_ID, API_HASH, system_version="4.16.30-vxAUTO") as client:
    print(client.session.save())


