from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger
import openai
import anthropic
import google.generativeai as genai
from mistralai import Mistral, UserMessage, SystemMessage, AssistantMessage
from enum import Enum
from crewai import LLM


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

    @abstractmethod
    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        """Get CrewAI LLM configuration"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider"""
    
    AVAILABLE_MODELS = ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {model} not in available models {self.AVAILABLE_MODELS}, using default gpt-4")
            model = "gpt-4"
        self.model = model
        
    async def initialize(self) -> bool:
        try:
            openai.api_key = self.api_key
            # Test API connection
            await openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "api_key": self.api_key,
            "model": self.model
        }

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url="https://api.openai.com/v1",
            api_key=self.api_key
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider"""
    
    AVAILABLE_MODELS = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240229"]
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {model} not in available models {self.AVAILABLE_MODELS}, using default claude-3-opus")
            model = "claude-3-opus-20240229"
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

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url="https://api.anthropic.com/v1",
            api_key=self.api_key
        )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider"""
    
    AVAILABLE_MODELS = ["gemini-pro", "gemini-pro-vision"]
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {model} not in available models {self.AVAILABLE_MODELS}, using default gemini-pro")
            model = "gemini-pro"
        self.model = model
        self.client = None
        
    async def initialize(self) -> bool:
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "google_api_key": self.api_key,
            "model": self.model
        }

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url="https://generativelanguage.googleapis.com/v1",
            api_key=self.api_key
        )


class MistralProvider(BaseLLMProvider):
    """Mistral AI LLM provider"""
    
    AVAILABLE_MODELS = ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"]
    
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.api_key = api_key
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {model} not in available models {self.AVAILABLE_MODELS}, using default mistral-large")
            model = "mistral-large-latest"
        self.model = model
        self.client = None
        
    async def initialize(self) -> bool:
        try:
            self.client = Mistral(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Mistral: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "mistral_api_key": self.api_key,
            "model": self.model
        }

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url="https://api.mistral.ai/v1",
            api_key=self.api_key
        )


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