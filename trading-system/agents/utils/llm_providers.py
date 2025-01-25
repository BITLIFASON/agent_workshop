from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger
import openai
from langchain.chat_models import ChatOpenAI
import anthropic
import google.generativeai as genai
from mistralai import Mistral, UserMessage, SystemMessage, AssistantMessage
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

    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate response from the model"""
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

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await openai.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return ""


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
            # Test API connection
            await self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "anthropic_api_key": self.api_key,
            "model": self.model
        }

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error generating Anthropic response: {e}")
            return ""


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
            # Test API connection
            response = self.client.generate_content("test")
            response.text
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "google_api_key": self.api_key,
            "model": self.model
        }

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages to Gemini format
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return ""


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
            # Test API connection
            messages = [{"role": "user", "content": "test"}]
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Mistral: {e}")
            return False
            
    async def get_llm_config(self) -> Dict[str, Any]:
        return {
            "mistral_api_key": self.api_key,
            "model": self.model
        }

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            # Convert messages to Mistral format
            mistral_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    mistral_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    mistral_messages.append(UserMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    mistral_messages.append(AssistantMessage(content=msg["content"]))

            response = await self.client.chat.complete_async(
                model=self.model,
                messages=mistral_messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating Mistral response: {e}")
            return ""


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