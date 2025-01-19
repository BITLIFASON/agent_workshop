import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    return {
        'telegram': {
            'api_id': int(os.getenv('API_ID', 0)),
            'api_hash': os.getenv('API_HASH', ''),
            'api_session_token': os.getenv('API_SESSION_TOKEN', ''),
            'channel_url': os.getenv('CHANNEL_URL', ''),
        },
        'database': {
            'host': 'postgres_db1',
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', ''),
            'password': os.getenv('POSTGRES_PASSWORD', ''),
            'database': os.getenv('POSTGRES_DB', ''),
        },
        'management_api': {
            'host': 'management1',  # имя контейнера
            'port': int(os.getenv('MANAGEMENT_API_PORT', 8080)),
            'token': os.getenv('MANAGEMENT_API_TOKEN', '')
        },
        'bybit': {
            'api_key': os.getenv('BYBIT_API_KEY', ''),
            'api_secret': os.getenv('BYBIT_API_SECRET', ''),
            'demo_mode': os.getenv('BYBIT_DEMO_MODE', 'True')
        }
    }
