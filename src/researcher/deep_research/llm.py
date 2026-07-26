"""
LLM utilities for Deep Research Module
Adapted from OnePage/deep_research_agent with YuLan-OneSim integration
"""

import json
from typing import Any, Dict, Optional, Sequence, AsyncGenerator
from loguru import logger

try:
    from openai import OpenAI, AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("OpenAI package not installed, using onesim models as fallback")

from .config import get_settings

# Try to use onesim models as fallback
try:
    from onesim.models import get_model_manager
    HAS_ONESIM = True
except ImportError:
    HAS_ONESIM = False

Message = Dict[str, str]  # {"role": "user" | "assistant" | "system", "content": str}


def chat(
    messages: Sequence[Message],
    model: Optional[str] = None,
    temperature: float = 0.2,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """
    通用聊天完成（兼容 OpenAI / v1/chat/completions 风格）
    返回 assistant 的文本内容。
    """
    settings = get_settings()
    
    # 优先使用 OpenAI 兼容接口
    if HAS_OPENAI and settings.model_api_key and (model or settings.llm_model):
        client = OpenAI(api_key=settings.model_api_key, base_url=settings.model_base_url)
        kwargs: Dict[str, Any] = {}
        if extra:
            kwargs.update(extra)
        try:
            resp = client.chat.completions.create(
                model=model or settings.llm_model,
                messages=list(messages),
                temperature=temperature,
                **kwargs,
            )
            content = resp.choices[0].message.content
            return content if content is not None else ""
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}, trying fallback...")
    
    # 回退到 onesim models
    if HAS_ONESIM:
        try:
            from onesim.models import SystemMessage, UserMessage
            model_manager = get_model_manager()
            llm = model_manager.get_model(None)  # 使用默认模型
            
            # 转换消息格式
            formatted_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    formatted_messages.append(SystemMessage(content=msg["content"]))
                else:
                    formatted_messages.append(UserMessage(content=msg["content"]))
            
            response = llm(llm.format(*formatted_messages))
            return response.text.strip()
        except Exception as e:
            logger.error(f"OneSim model call failed: {e}")
            raise
    
    raise RuntimeError("No LLM backend available. Please install openai or configure onesim models.")


async def chat_stream(
    messages: Sequence[Message],
    model: Optional[str] = None,
    temperature: float = 0.2,
    extra: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """
    异步流式聊天完成
    """
    settings = get_settings()
    
    if not HAS_OPENAI or not settings.model_api_key or not (model or settings.llm_model):
        # 非流式回退
        result = chat(messages, model, temperature, extra)
        yield result
        return
    
    client = AsyncOpenAI(
        api_key=settings.model_api_key,
        base_url=settings.model_base_url
    )
    kwargs: Dict[str, Any] = {"stream": True}
    if extra:
        kwargs.update(extra)
    
    stream = await client.chat.completions.create(
        model=model or settings.llm_model,
        messages=list(messages),
        temperature=temperature,
        **kwargs,
    )
    
    async for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta_content = chunk.choices[0].delta.content
            if delta_content:
                yield delta_content
