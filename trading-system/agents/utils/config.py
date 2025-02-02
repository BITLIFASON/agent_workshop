import os
from typing import Dict, Any
from dotenv import load_dotenv

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    load_dotenv()

    return {
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", ""),
            "model": os.getenv("LLM_MODEL", ""),
            "api_key": os.getenv("LLM_API_KEY", ""),
        },
        
        "bybit": {
            "api_key": os.getenv("BYBIT_API_KEY", ""),
            "api_secret": os.getenv("BYBIT_API_SECRET", ""),
            "demo_mode": os.getenv("BYBIT_DEMO_MODE", "True"),
            "leverage": os.getenv("LEVERAGE", "1")
        },
        
        "telegram": {
            "api_id": int(os.getenv("API_ID"), 0),
            "api_hash": os.getenv("API_HASH", ""),
            "session_token": os.getenv("API_SESSION_TOKEN", ""),
            "channel_url": os.getenv("CHANNEL_URL", ""),
            "max_retries": int(os.getenv("MAX_RETRIES_TELEGRAM", 3))
        },
        
        "management_api": {
            "host": os.getenv("MANAGEMENT_API_HOST", "localhost"),
            "port": os.getenv("MANAGEMENT_API_PORT", "8080"),
            "token": os.getenv("MANAGEMENT_API_TOKEN", "")
        },
        
        "database": {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", ""),
            "user": os.getenv("POSTGRES_USER", ""),
            "password": os.getenv("POSTGRES_PASSWORD", "")
        }
    } 