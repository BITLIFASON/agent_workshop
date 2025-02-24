from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger
import openai
import anthropic
import google.generativeai as genai
from mistralai import Mistral, UserMessage, SystemMessage, AssistantMessage
from enum import Enum
from crewai import LLM
import requests


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    OLLAMA = "ollama"


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
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
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

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url="https://api.anthropic.com/v1",
            api_key=self.api_key
        )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
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
    
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.api_key = api_key
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
            api_key=self.api_key,
            timeout=1
        )


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider"""
    
    def __init__(self, model: str = "llama3"):
        self.base_url = "http://ollama:11434"
        self.model = model
        
    async def initialize(self) -> bool:
        try:
            # Test API connection
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                if not models or self.model not in [m["name"] for m in models]:
                    logger.warning(f"Model {self.model} not found in available models")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "model": self.model
        }

    def get_crew_llm(self, temperature: float = 0.7) -> LLM:
        return LLM(
            model=self.model,
            temperature=temperature,
            base_url=self.base_url,
            api_key="not-needed"  # Ollama doesn't require API key
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
            elif provider_type == LLMProvider.OLLAMA:
                return OllamaProvider(
                    model=config.get("model", "llama3")
                )
            else:
                logger.error(f"Unknown LLM provider type: {provider_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create LLM provider: {e}")
            return None 