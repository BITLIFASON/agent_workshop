import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    return {
        'telegram': {
            'api_id': int(os.getenv('API_ID', 0)),
            'api_hash': os.getenv('API_HASH', ''),
            'channel_url': os.getenv('CHANNEL_URL', '')
        },
        'database': {
            'host': 'postgres_db1',
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', ''),
            'password': os.getenv('POSTGRES_PASSWORD', ''),
            'database': os.getenv('POSTGRES_DB', ''),
        },
        'queue': {
            'host': 'rabbitmq1',  # Updated container name
            'port': int(os.getenv('RABBITMQ_PORT', 5672)),
            'user': os.getenv('RABBITMQ_DEFAULT_USER', ''),
            'password': os.getenv('RABBITMQ_DEFAULT_PASS', ''),
            'queue_name': os.getenv('QUEUE_NAME', '')
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
