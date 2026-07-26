"""
This module defines the ModelResponse class which encapsulates different types of model responses.
"""

from typing import Any, AsyncGenerator, Dict, Generator, Optional, Sequence, Tuple, Union
import json

class ModelResponse:
    """
    Encapsulates data returned by a model.
    
    This class provides a standardized structure for model responses across different model types,
    acting as a bridge between models and agents.
    """

    def __init__(
        self,
        text: str = None,
        embedding: Sequence = None,
        raw: Any = None,
        parsed: Any = None,
        stream: Optional[Generator[str, None, None]] = None,
        astream: Optional[AsyncGenerator[str, None]] = None,
        usage: Optional[Dict[str, Any]] = None,
        model_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the model response.

        Args:
            text: The text response from the model.
            embedding: Vector embeddings from the model.
            raw: The raw unparsed response from the model.
            parsed: The parsed response data (typically parsed JSON).
            stream: A generator for streaming responses.
            usage: Token usage information.
            model_info: Information about the model that generated the response.
        """
        self._text = text
        self.embedding = embedding
        self.raw = raw
        self.parsed = parsed
        self._stream = stream
        self._astream = astream
        self._is_stream_exhausted = False
        self._is_astream_exhausted = False
        self.usage = usage or {}
        self.model_info = model_info or {}

    @property
    def text(self) -> str:
        """
        Get the text response, processing the stream if needed.
        
        Returns:
            The text response from the model.
        """
        if self._text is None and self._stream is not None:
            for chunk in self._stream:
                self._text = chunk
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set the text field."""
        self._text = value

    @property
    def stream(self) -> Union[None, Generator[Tuple[bool, str], None, None]]:
        """
        Get the stream generator with status information.
        
        Returns:
            A generator that yields (is_finished, text_chunk) tuples or None if no stream.
        """
        if self._stream is None:
            return None
        else:
            return self._stream_generator_wrapper()

    @property
    def astream(self) -> Union[None, AsyncGenerator[Tuple[bool, str], None]]:
        """
        Get the async stream generator with status information.

        Returns:
            An async generator that yields (is_finished, text_chunk) tuples,
            or None if no async stream is available.
        """
        if self._astream is None:
            return None
        return self._astream_generator_wrapper()

    @property
    def is_stream_exhausted(self) -> bool:
        """Check if the stream has been fully processed."""
        return self._is_stream_exhausted

    @property
    def is_astream_exhausted(self) -> bool:
        """Check if the async stream has been fully processed."""
        return self._is_astream_exhausted

    def _stream_generator_wrapper(self) -> Generator[Tuple[bool, str], None, None]:
        """
        Process the stream generator and update the text field.
        
        Yields:
            Tuples of (is_finished, text_chunk).
        """
        if self._is_stream_exhausted:
            raise RuntimeError(
                "The stream has been processed already. Access the result from the text field."
            )

        if self._stream is None:
            return

        try:
            # Get the first chunk
            last_text = next(self._stream)

            # Process remaining chunks
            for text in self._stream:
                self._text = last_text
                yield False, last_text
                last_text = text
                
            # Mark the final chunk
            self._text = last_text
            yield True, last_text
            
            # Mark stream as exhausted
            self._is_stream_exhausted = True
            
        except StopIteration:
            self._is_stream_exhausted = True
            return

    async def _astream_generator_wrapper(self) -> AsyncGenerator[Tuple[bool, str], None]:
        """
        Process the async stream generator and update the text field.

        Yields:
            Tuples of (is_finished, text_chunk).
        """
        if self._is_astream_exhausted:
            raise RuntimeError(
                "The async stream has been processed already. Access the result from the text field."
            )
        if self._astream is None:
            return

        try:
            # Get first chunk
            last_text = await self._astream.__anext__()
            async for text in self._astream:
                self._text = last_text
                yield False, last_text
                last_text = text

            self._text = last_text
            yield True, last_text
            self._is_astream_exhausted = True
        except StopAsyncIteration:
            self._is_astream_exhausted = True
            return

    def __str__(self) -> str:
        """String representation of the model response for debugging."""
        fields = {
            "text": self.text,
            "embedding": self.embedding,
            "parsed": self.parsed,
            "raw": self.raw,
            "usage": self.usage,
            "model_info": self.model_info
        }
        return json.dumps(
            self._to_json_serializable(fields),
            indent=4,
            ensure_ascii=False,
        )

    @classmethod
    def _to_json_serializable(cls, obj: Any) -> Any:
        """Convert provider SDK objects into safe diagnostic JSON values."""
        if cls._is_json_serializable(obj):
            return obj
        if hasattr(obj, "model_dump"):
            try:
                return cls._to_json_serializable(obj.model_dump())
            except Exception:
                pass
        if isinstance(obj, dict):
            return {
                str(key): cls._to_json_serializable(value)
                for key, value in obj.items()
            }
        if isinstance(obj, (list, tuple, set)):
            return [cls._to_json_serializable(value) for value in obj]
        return str(obj)
        
    @staticmethod
    def _is_json_serializable(obj: Any) -> bool:
        """Check if an object is JSON serializable."""
        if obj is None:
            return True
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError):
            return False 
