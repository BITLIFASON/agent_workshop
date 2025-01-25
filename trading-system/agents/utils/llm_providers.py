from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger
import openai
from langchain.chat_models import ChatOpenAI
import anthropic
import google.generativeai as genai
import mistralai
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MISTRAL = "mistral"


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the LLM provider"""
        pass

    @abstractmethod
    async def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for CrewAI"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
    async def initialize(self) -> bool:
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "openai_api_key": self.api_key,
            "model": self.model
        }


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider"""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
    async def initialize(self) -> bool:
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "anthropic_api_key": self.api_key,
            "model": self.model
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        
    async def initialize(self) -> bool:
        try:
            genai.configure(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "google_api_key": self.api_key,
            "model": self.model
        }


class MistralProvider(BaseLLMProvider):
    """Mistral AI LLM provider"""
    
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
    async def initialize(self) -> bool:
        try:
            self.client = mistralai.MistralClient(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Mistral: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "mistral_api_key": self.api_key,
            "model": self.model
        }


class LLMFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_type: LLMProvider, config: Dict[str, Any]) -> Optional[BaseLLMProvider]:
        try:
            if provider_type == LLMProvider.OPENAI:
                return OpenAIProvider(
                    api_key=config["api_key"],
                    model=config.get("model", "gpt-4")
                )
            elif provider_type == LLMProvider.ANTHROPIC:
                return AnthropicProvider(
                    api_key=config["api_key"],
                    model=config.get("model", "claude-3-opus-20240229")
                )
            elif provider_type == LLMProvider.GEMINI:
                return GeminiProvider(
                    api_key=config["api_key"],
                    model=config.get("model", "gemini-pro")
                )
            elif provider_type == LLMProvider.MISTRAL:
                return MistralProvider(
                    api_key=config["api_key"],
                    model=config.get("model", "mistral-large-latest")
                )
            else:
                logger.error(f"Unknown LLM provider type: {provider_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create LLM provider: {e}")
            return None 