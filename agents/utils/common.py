from typing import Dict, Any
import json
from datetime import datetime
from decimal import Decimal

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special types"""

    def default(self, obj):
        """
        Override the JSON encoding for datetime objects.

        Args:
            obj (datetime): The datetime object to be encoded.

        Returns:
            str: The serialized datetime string.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def serialize_message(message: Dict[str, Any]) -> str:
    """Serialize message to JSON string"""
    return json.dumps(message, cls=DateTimeEncoder)

def deserialize_message(message: str) -> Dict[str, Any]:
    """Deserialize message from JSON string"""
    return json.loads(message)

class MessageValidator:
    """Validator for inter-agent messages"""

    @staticmethod
    def validate_trading_signal(signal: Dict[str, Any]) -> bool:
        required_fields = ['symbol', 'action', 'price']
        return all(field in signal for field in required_fields)

    @staticmethod
    def validate_balance_command(command: Dict[str, Any]) -> bool:
        required_fields = ['action', 'amount']
        return all(field in command for field in required_fields)
