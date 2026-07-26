"""
Implementation of vLLM chat model adapter with both sync and async support.
"""

import json
from typing import Any, Dict, Generator, List, Optional, Sequence, Union
import asyncio

from loguru import logger

from ..core.model_base import ModelAdapterBase
from ..core.model_response import ModelResponse
from ..core.message import Message


class VLLMChatAdapter(ModelAdapterBase):
    """
    Adapter for vLLM-powered models and compatible APIs.
    
    This class provides an interface to vLLM's API via its OpenAI-compatible
    endpoint. It supports both synchronous and asynchronous calls, and can handle
    local model deployments or remote vLLM endpoints.
    """

    def __init__(
        self,
        config_name: str,
        model_name: str = None,
        api_key: str = None,  # Not required but kept for API compatibility
        client_args: dict = None,
        stream: bool = False,
        generate_args: dict = None,
        **kwargs
    ):
        """
        Initialize the vLLM chat model adapter.
        
        Args:
            config_name: Configuration name for this model.
            model_name: The name of the model or path to model.
            api_key: Not used for vLLM directly but kept for interface compatibility.
            client_args: Additional arguments for the client (base_url, etc).
            stream: Whether to stream responses by default.
            generate_args: Default parameters for generation requests.
            **kwargs: Additional parameters.
        """
        super().__init__(config_name=config_name, model_name=model_name, **kwargs)

        self.stream = stream
        self.generate_args = generate_args or {}
        self._requires_thinking = False

        # Initialize the OpenAI client to use for vLLM's OpenAI-compatible endpoint
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not found. Please install it using: pip install openai"
            )

        # Set a default base_url if not provided
        client_args = client_args or {}
        if "base_url" not in client_args:
            client_args["base_url"] = "http://localhost:8000/v1"
            logger.warning(f"No base_url provided, using default: {client_args['base_url']}")

        # Create client - note we use the OpenAI client but pointed to our vLLM endpoint
        self.client = openai.OpenAI(
            api_key=api_key or "EMPTY",  # vLLM often doesn't need API key
            **client_args
        )

        # Initialize the async client
        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning(
                "OpenAI async package not found. Async calls will use the sync client in an event loop."
            )
            self.async_client = None
        else:
            self.async_client = AsyncOpenAI(
                api_key=api_key or "EMPTY",
                **client_args
            )

    def __call__(
        self,
        messages: List[Dict],
        stream: Optional[bool] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Synchronous call to the vLLM API through the OpenAI-compatible endpoint.
        
        Args:
            messages: List of formatted message dictionaries.
            stream: Whether to stream the response.
            **kwargs: Additional parameters for the API call.
            
        Returns:
            ModelResponse: The response from the model.
        """
        # Merge default arguments with provided ones
        call_kwargs = {**self.generate_args, **kwargs}

        # Validate the messages format
        self._validate_messages(messages)

        # Determine streaming mode
        stream_mode = self.stream if stream is None else stream

        # Set up API call parameters
        extra_body = call_kwargs.pop("extra_body", {}) or {}
        extra_body.setdefault("chat_template_kwargs", {}).setdefault(
            "enable_thinking", self._requires_thinking
        )
        call_kwargs.update({
            "model": self.model_name,
            "messages": messages,
            "stream": stream_mode,
            "timeout": 300,
            "extra_body": extra_body
        })

        if stream_mode:
            call_kwargs["stream_options"] = {"include_usage": True}

        try:
            response = self.client.chat.completions.create(**call_kwargs)
        except Exception as e:
            if self._is_thinking_required_error(e) and not extra_body.get("chat_template_kwargs", {}).get("enable_thinking"):
                logger.info(f"Model '{self.model_name}' requires enable_thinking=True, retrying")
                self._requires_thinking = True
                call_kwargs["extra_body"]["chat_template_kwargs"]["enable_thinking"] = True
                try:
                    response = self.client.chat.completions.create(**call_kwargs)
                except Exception as e2:
                    logger.error(f"Error calling vLLM API: {e2}")
                    raise
            else:
                logger.error(f"Error calling vLLM API: {e}")
                raise

        if stream_mode:
            def generate_stream() -> Generator[str, None, None]:
                text = ""
                last_chunk = {}
                for chunk in response:
                    chunk_data = chunk.model_dump()
                    if self._has_content_in_delta(chunk_data):
                        content_chunk = chunk_data["choices"][0]["delta"]["content"]
                        text += content_chunk
                        yield text
                    last_chunk = chunk_data
                if "usage" in last_chunk:
                    self._track_token_usage(last_chunk["usage"])

            return ModelResponse(
                stream=generate_stream(),
                model_info={
                    "model_name": self.model_name,
                    "config_name": self.config_name
                }
            )
        else:
            response_data = response.model_dump()
            if "usage" in response_data:
                self._track_token_usage(response_data["usage"])
            if self._has_content_in_message(response_data):
                content = response_data["choices"][0]["message"]["content"]
                return ModelResponse(
                    text=content,
                    raw=response_data,
                    usage=response_data.get("usage"),
                    model_info={
                        "model_name": self.model_name,
                        "config_name": self.config_name
                    }
                )
            else:
                raise ValueError(f"Invalid response format: {response_data}")

    async def acall(
        self,
        messages: List[Dict],
        stream: Optional[bool] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Asynchronous call to the vLLM API.
        
        Args:
            messages: List of formatted message dictionaries.
            stream: Whether to stream the response.
            **kwargs: Additional parameters for the API call.
            
        Returns:
            ModelResponse: The response from the model.
        """
        # Merge default arguments with provided ones
        call_kwargs = {**self.generate_args, **kwargs}

        # Validate messages format
        self._validate_messages(messages)

        # Determine streaming mode
        use_stream = self.stream if stream is None else stream

        # Set up API call parameters
        extra_body = call_kwargs.pop("extra_body", {}) or {}
        extra_body.setdefault("chat_template_kwargs", {}).setdefault(
            "enable_thinking", self._requires_thinking
        )
        call_kwargs.update({
            "model": self.model_name,
            "messages": messages,
            "stream": use_stream,
            "timeout": 300,
            "extra_body": extra_body
        })

        if use_stream:
            call_kwargs["stream_options"] = {"include_usage": True}

        try:
            if self.async_client:
                response = await self.async_client.chat.completions.create(**call_kwargs)
            else:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(**call_kwargs)
                )
        except Exception as e:
            if self._is_thinking_required_error(e) and not extra_body.get("chat_template_kwargs", {}).get("enable_thinking"):
                logger.info(f"Model '{self.model_name}' requires enable_thinking=True, retrying")
                self._requires_thinking = True
                call_kwargs["extra_body"]["chat_template_kwargs"]["enable_thinking"] = True
                try:
                    if self.async_client:
                        response = await self.async_client.chat.completions.create(**call_kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            None,
                            lambda: self.client.chat.completions.create(**call_kwargs)
                        )
                except Exception as e2:
                    logger.error(f"Error calling vLLM API asynchronously: {e2}")
                    raise
            else:
                logger.error(f"Error calling vLLM API asynchronously: {e}")
                raise

        if use_stream:
            async def generate_stream_async():
                text = ""
                last_chunk = {}
                async for chunk in response:
                    chunk_data = chunk.model_dump()
                    if self._has_content_in_delta(chunk_data):
                        content = chunk_data["choices"][0]["delta"]["content"]
                        text += content
                        yield text
                    last_chunk = chunk_data
                if "choices" not in last_chunk or not last_chunk["choices"]:
                    last_chunk["choices"] = [
                        {"message": {"role": "assistant", "content": text}}
                    ]
                else:
                    last_chunk["choices"][0]["message"] = {
                        "role": "assistant",
                        "content": text,
                    }
                if "usage" in last_chunk:
                    self._track_token_usage(last_chunk["usage"])

            return ModelResponse(
                astream=generate_stream_async(),
                model_info={
                    "model_name": self.model_name,
                    "config_name": self.config_name
                }
            )
        else:
            response_data = response.model_dump()
            if "usage" in response_data:
                self._track_token_usage(response_data["usage"])
            if self._has_content_in_message(response_data):
                content = response_data["choices"][0]["message"]["content"]
                return ModelResponse(
                    text=content,
                    raw=response_data,
                    usage=response_data.get("usage"),
                    model_info={
                        "model_name": self.model_name,
                        "config_name": self.config_name
                    }
                )
            else:
                raise ValueError(f"Invalid response format: {response_data}")

    def list_models(self) -> List[str]:
        """
        vLLM endpoint doesn’t support /v1/models, so we just
        return the configured model name.
        """
        return [self.model_name]

    async def alist_models(self) -> List[str]:
        """
        Async version: same fallback to single model name.
        """
        return [self.model_name]

    @staticmethod
    def _is_thinking_required_error(exc: Exception) -> bool:
        """Check if the error means the model requires enable_thinking=True."""
        status = getattr(exc, "status_code", None)
        if status != 400:
            return False
        err_str = str(exc).lower()
        return "enable_thinking" in err_str or "thinking" in err_str

    def _validate_messages(self, messages: List[Dict]) -> None:
        """Validate that the messages have the required format."""
        if not isinstance(messages, list):
            raise ValueError("Messages must be a list")

        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a dictionary")

            if "role" not in message:
                raise ValueError("Each message must have a 'role' field")

            if "content" not in message:
                raise ValueError("Each message must have a 'content' field")

    def format(self, *args: Union[Message, Sequence[Message]]) -> List[Dict]:
        """
        Format the input messages into the format expected by the vLLM API.
        
        Args:
            *args: Message objects or sequences of Message objects.
            
        Returns:
            List of dictionaries in the vLLM API format.
        """
        formatted_messages = []

        for arg in args:
            if isinstance(arg, Message):
                # Single message
                formatted_messages.append({
                    "role": arg.role,
                    "content": self._convert_to_str(arg.content)
                })
            elif hasattr(arg, "__iter__"):
                # Sequence of messages
                for message in arg:
                    if isinstance(message, Message):
                        formatted_messages.append({
                            "role": message.role,
                            "content": self._convert_to_str(message.content)
                        })
                    else:
                        raise ValueError(f"Expected Message object, got {type(message)}")
            else:
                raise ValueError(f"Expected Message object or sequence, got {type(arg)}")

        return formatted_messages

    @staticmethod
    def _convert_to_str(content: Any) -> str:
        """Convert content to string if needed."""
        if content is None:
            return ""
        elif isinstance(content, (str, int, float, bool)):
            return str(content)
        elif isinstance(content, (dict, list)):
            return json.dumps(content)
        else:
            return str(content)

    @staticmethod
    def _has_content_in_delta(response: Dict) -> bool:
        """Check if a streaming response chunk contains content."""
        try:
            return (
                response.get("choices")
                and response["choices"][0].get("delta")
                and "content" in response["choices"][0]["delta"]
                and response["choices"][0]["delta"]["content"] is not None # Added check for None content
            )
        except (KeyError, IndexError):
            return False

    @staticmethod
    def _has_content_in_message(response: Dict) -> bool:
        """Check if a response contains a message with content."""
        try:
            return (
                response.get("choices")
                and response["choices"][0].get("message")
                and "content" in response["choices"][0]["message"]
            )
        except (KeyError, IndexError):
            return False


class VLLMEmbeddingAdapter(ModelAdapterBase):
    """
    Adapter for embedding models hosted via vLLM's OpenAI-compatible API.
    """

    def __init__(
        self,
        config_name: str,
        model_name: str = None,
        api_key: str = None,
        client_args: dict = None,
        generate_args: dict = None,
        **kwargs
    ):
        """
        Initialize the vLLM embedding model adapter.
        
        Args:
            config_name: Configuration name for this model.
            model_name: The name of the model or path to model.
            api_key: Not used for vLLM directly but kept for interface compatibility.
            client_args: Additional arguments for the client (base_url, etc).
            generate_args: Default parameters for generation requests.
            **kwargs: Additional parameters.
        """
        super().__init__(config_name=config_name, model_name=model_name, **kwargs)

        self.generate_args = generate_args or {}

        # Initialize the OpenAI client
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not found. Please install it using: pip install openai"
            )

        # Set a default base_url if not provided
        client_args = client_args or {}
        if "base_url" not in client_args:
            client_args["base_url"] = "http://localhost:8000/v1"
            logger.warning(f"No base_url provided, using default: {client_args['base_url']}")

        # Create client - note we use the OpenAI client but pointed to our vLLM endpoint
        self.client = openai.OpenAI(
            api_key=api_key or "EMPTY",  # vLLM often doesn't need API key
            **client_args
        )

        # Initialize the async client
        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning(
                "OpenAI async package not found. Async calls will use the sync client in an event loop."
            )
            self.async_client = None
        else:
            self.async_client = AsyncOpenAI(
                api_key=api_key or "EMPTY",
                **client_args
            )

    def __call__(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> ModelResponse:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Text or list of texts to embed.
            **kwargs: Additional parameters for the embedding request.
            
        Returns:
            ModelResponse: The embeddings.
        """
        # Convert to list if a single string
        if isinstance(texts, str):
            texts = [texts]

        # Ensure all texts are strings
        texts = [self._convert_to_str(text) for text in texts]

        # Merge default arguments with provided ones
        call_args = {**self.generate_args, **kwargs}

        try:
            # Call the embeddings API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
                **call_args
            )
            response_data = response.model_dump()

            # Extract embeddings
            if "data" in response_data and len(response_data["data"]) > 0:
                embeddings = [item["embedding"] for item in response_data["data"]]

                # Record usage information if available - using _track_token_usage
                if "usage" in response_data:
                    self._track_token_usage(
                        response_data["usage"]
                    )  # Align with openai.py

                return ModelResponse(
                    embedding=embeddings,  # Return list directly
                    raw=response_data,
                    usage=response_data.get("usage"),
                    model_info={
                        "model_name": self.model_name,
                        "config_name": self.config_name,
                    },
                )
            else:
                raise ValueError(f"Invalid response format: {response_data}")

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return error response
            raise # Re-raise exception
            # return ModelResponse(
            #     text=f"Error: {e}",
            #     raw={
            #         "model": self.model_name,
            #         "config_name": self.config_name,
            #         "error": str(e)
            #     },
            #     embeddings=[]
            # )

    async def acall(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> ModelResponse:
        """
        Asynchronously generate embeddings for text(s).
        
        Args:
            texts: Text or list of texts to embed.
            **kwargs: Additional parameters for the embedding request.
            
        Returns:
            ModelResponse: The embeddings.
        """
        # Convert to list if a single string
        if isinstance(texts, str):
            texts = [texts]

        # Ensure all texts are strings
        texts = [self._convert_to_str(text) for text in texts]

        # Merge default arguments with provided ones
        call_args = {**self.generate_args, **kwargs}

        try:
            # If we don't have an async client, run the sync method in the event loop
            if self.async_client is None:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor( # Run the sync __call__
                    None, lambda: self.client.embeddings.create(model=self.model_name, input=texts, **call_args)
                )
            else:
                # Call the embeddings API asynchronously
                response = await self.async_client.embeddings.create(
                    model=self.model_name, input=texts, **call_args
                )

            response_data = response.model_dump()

            # Extract embeddings
            if "data" in response_data and len(response_data["data"]) > 0:
                embeddings = [item["embedding"] for item in response_data["data"]]

                # Record usage information if available - using _track_token_usage
                if "usage" in response_data:
                    self._track_token_usage(
                        response_data["usage"]
                    )  # Align with openai.py

                return ModelResponse(
                    embedding=embeddings,  # Return list directly
                    raw=response_data,
                    usage=response_data.get("usage"),
                    model_info={
                        "model_name": self.model_name,
                        "config_name": self.config_name,
                    },
                )
            else:
                raise ValueError(f"Invalid response format: {response_data}")

        except Exception as e:
            logger.error(f"Error generating embeddings asynchronously: {e}")
            # Return error response
            raise  # Re-raise exception

    def format(self, *args: Union[str, Message, Sequence[Union[str, Message]]]) -> List[str]:
        """
        Format the input messages or texts into the format expected by the embeddings API.
        
        Args:
            *args: String, Message objects, or sequences of them.
            
        Returns:
            List of strings to embed.
        """
        formatted_texts = []

        for arg in args:
            if isinstance(arg, str):
                # Single text string
                formatted_texts.append(arg)
            elif isinstance(arg, Message):
                # Single message
                formatted_texts.append(self._convert_to_str(arg.content))
            elif hasattr(arg, "__iter__"):
                # Sequence of texts or messages
                for item in arg:
                    if isinstance(item, str):
                        formatted_texts.append(item)
                    elif isinstance(item, Message):
                        formatted_texts.append(self._convert_to_str(item.content))
                    else:
                        raise ValueError(f"Expected str or Message, got {type(item)}")
            else:
                raise ValueError(f"Expected str, Message, or sequence, got {type(arg)}")

        return formatted_texts

    def list_models(self) -> List[str]:
        """
        vLLM endpoint doesn’t support /v1/models, so we just
        return the configured model name.
        """
        return [self.model_name]

    async def alist_models(self) -> List[str]:
        """
        Async version: same fallback to single model name.
        """
        return [self.model_name]

    @staticmethod
    def _convert_to_str(content: Any) -> str:
        """Convert content to string if needed."""
        if content is None:
            return ""
        elif isinstance(content, (str, int, float, bool)):
            return str(content)
        elif isinstance(content, (dict, list)):
            return json.dumps(content)
        else:
            return str(content)
