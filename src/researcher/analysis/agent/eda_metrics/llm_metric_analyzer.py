from typing import Callable

from ..llm.agent_client import SimpleChatLLM


def build_metric_type_llm(config_name: str = "default-chat", config_path: str = "config/model_config.json") -> Callable[[str], str]:
    client = SimpleChatLLM(config_name=config_name, config_path=config_path)

    def _fn(prompt: str) -> str:
        return client.chat(
            user_query=prompt,
            system_prompt="Return ONLY one of: time_series or distribution.",
            temperature=0.2,
        )

    return _fn


__all__ = ["build_metric_type_llm"]
