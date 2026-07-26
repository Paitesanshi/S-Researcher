"""
Retry utilities for model calls.

This module provides a provider-agnostic retry mechanism intended for transient
failures (rate limits, timeouts, temporary server errors, etc.).
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Optional, Sequence, Set, Tuple, Type

from loguru import logger

from .model_base import ModelAdapterBase
from .model_response import ModelResponse


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retrying model calls."""

    enabled: bool = True
    max_attempts: int = 5
    initial_delay_s: float = 0.5
    max_delay_s: float = 30.0
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.1  # +/- 10%
    rate_limit_min_delay_s: float = 2.0  # minimum delay for 429 rate-limit errors

    # Retryable status codes (HTTP-like)
    retryable_status_codes: Set[int] = field(
        default_factory=lambda: {408, 409, 429, 500, 502, 503, 504}
    )

    # Retryable exception *class names* (avoid hard dependency on providers)
    retryable_exception_names: Set[str] = field(
        default_factory=lambda: {
            # OpenAI SDK (v1)
            "RateLimitError",
            "APITimeoutError",
            "APIConnectionError",
            "APIStatusError",
            "InternalServerError",
            # httpx / requests / stdlib-ish
            "TimeoutException",
            "ReadTimeout",
            "ConnectTimeout",
            "ConnectionError",
            "ConnectError",
            "ReadError",
            "RemoteProtocolError",
            "ProtocolError",
            "ChunkedEncodingError",
            "TimeoutError",
            "asyncio.TimeoutError",
        }
    )

    # If provider exposes Retry-After, respect it (best-effort).
    respect_retry_after: bool = True

    # If True, log retry attempts at warning level.
    log_retries: bool = True


def _safe_err_str(exc: BaseException, max_len: int = 300) -> str:
    """Best-effort sanitization/truncation for logs (avoid large payload dumps)."""
    try:
        s = str(exc)
    except Exception:
        s = repr(exc)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _get_exc_status_code(exc: BaseException) -> Optional[int]:
    """
    Extract status code from common exception shapes (OpenAI SDK, HTTP clients).
    """
    # OpenAI SDK: exc.status_code
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status

    # OpenAI SDK: exc.response.status_code
    resp = getattr(exc, "response", None)
    if resp is not None:
        status = getattr(resp, "status_code", None)
        if isinstance(status, int):
            return status
        # Some clients: resp.status
        status = getattr(resp, "status", None)
        if isinstance(status, int):
            return status

    return None


def _get_retry_after_s(exc: BaseException) -> Optional[float]:
    """
    Extract retry-after hint from common exception shapes.
    """
    resp = getattr(exc, "response", None)
    headers = None
    if resp is not None:
        headers = getattr(resp, "headers", None)
    if not headers:
        headers = getattr(exc, "headers", None)
    if not headers:
        return None

    # headers could be dict-like
    try:
        ra = headers.get("retry-after") or headers.get("Retry-After")
    except Exception:
        ra = None

    if ra is None:
        return None

    try:
        return float(ra)
    except Exception:
        return None


def is_retryable_exception(exc: BaseException, cfg: RetryConfig) -> Tuple[bool, str]:
    """
    Decide whether an exception should be retried.

    Returns (retryable, reason).
    """
    status = _get_exc_status_code(exc)
    if status is not None and status in cfg.retryable_status_codes:
        return True, f"status_code={status}"

    name = exc.__class__.__name__
    if name in cfg.retryable_exception_names:
        return True, f"exc={name}"

    # Some exceptions embed the underlying error type.
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        cause_name = cause.__class__.__name__
        if cause_name in cfg.retryable_exception_names:
            return True, f"cause={cause_name}"

    return False, "non-retryable"


def compute_backoff_s(cfg: RetryConfig, attempt_index: int, exc: Optional[BaseException] = None) -> float:
    """
    Compute backoff time for a given attempt index (1-based).

    For 429 rate-limit errors, uses a higher minimum delay
    (``rate_limit_min_delay_s``) so that the caller backs off long enough
    for the provider's rate window to reset.
    """
    initial = cfg.initial_delay_s

    # For 429 rate-limit errors, enforce a higher minimum starting delay
    if exc is not None:
        status = _get_exc_status_code(exc)
        if status == 429:
            initial = max(initial, cfg.rate_limit_min_delay_s)

    if attempt_index <= 1:
        base = initial
    else:
        base = initial * (cfg.backoff_multiplier ** (attempt_index - 1))

    base = min(base, cfg.max_delay_s)

    if cfg.respect_retry_after and exc is not None:
        ra = _get_retry_after_s(exc)
        if ra is not None and ra > 0:
            base = max(base, min(ra, cfg.max_delay_s))

    if cfg.jitter_ratio and cfg.jitter_ratio > 0:
        jitter = base * cfg.jitter_ratio
        base = random.uniform(max(0.0, base - jitter), base + jitter)

    return base


class RetryingModelAdapter(ModelAdapterBase):
    """
    Adapter wrapper that retries transient failures for both sync and async calls.

    Notes:
    - Retries only cover the initial call. If you request streaming and the stream
      fails mid-iteration, that exception will not be retried.
    """

    def __init__(self, inner: ModelAdapterBase, retry_config: Optional[RetryConfig] = None):
        self._inner = inner
        self._retry_config = retry_config or RetryConfig()
        super().__init__(config_name=inner.config_name, model_name=getattr(inner, "model_name", None))

    @property
    def inner(self) -> ModelAdapterBase:
        return self._inner

    @property
    def retry_config(self) -> RetryConfig:
        return self._retry_config

    def __getattr__(self, item: str) -> Any:
        # Delegate unknown attributes to inner adapter.
        return getattr(self._inner, item)

    def format(self, *args, **kwargs) -> Any:
        return self._inner.format(*args, **kwargs)

    def list_models(self) -> Sequence[str]:
        return self._inner.list_models()

    async def alist_models(self) -> Sequence[str]:
        return await self._inner.alist_models()

    def __call__(self, *args, **kwargs) -> ModelResponse:
        cfg = self._retry_config
        if not cfg.enabled or cfg.max_attempts <= 1:
            return self._inner(*args, **kwargs)

        last_exc: Optional[BaseException] = None
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                return self._inner(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                retryable, reason = is_retryable_exception(exc, cfg)
                if not retryable or attempt >= cfg.max_attempts:
                    raise

                delay_s = compute_backoff_s(cfg, attempt, exc=exc)
                if cfg.log_retries:
                    logger.warning(
                        "Model call failed (will retry): config_name={} model_name={} attempt={}/{} reason={} delay_s={} err={}",
                        getattr(self._inner, "config_name", None),
                        getattr(self._inner, "model_name", None),
                        attempt,
                        cfg.max_attempts,
                        reason,
                        round(delay_s, 3),
                        _safe_err_str(exc),
                    )
                time.sleep(delay_s)

        # Should never reach here.
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Retry loop exited unexpectedly")

    async def acall(self, *args, **kwargs) -> ModelResponse:
        cfg = self._retry_config
        if not cfg.enabled or cfg.max_attempts <= 1:
            return await self._inner.acall(*args, **kwargs)

        last_exc: Optional[BaseException] = None
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                return await self._inner.acall(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                retryable, reason = is_retryable_exception(exc, cfg)
                if not retryable or attempt >= cfg.max_attempts:
                    raise

                delay_s = compute_backoff_s(cfg, attempt, exc=exc)
                if cfg.log_retries:
                    logger.warning(
                        "Async model call failed (will retry): config_name={} model_name={} attempt={}/{} reason={} delay_s={} err={}",
                        getattr(self._inner, "config_name", None),
                        getattr(self._inner, "model_name", None),
                        attempt,
                        cfg.max_attempts,
                        reason,
                        round(delay_s, 3),
                        _safe_err_str(exc),
                    )
                await asyncio.sleep(delay_s)

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Retry loop exited unexpectedly")


