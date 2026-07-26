from typing import Any, Optional
from researcher.analysis.common import get_common_model_name, get_model_config_path

def build_llm(enable: bool, config_name: Optional[str], config_path: Optional[str]) -> Any:
    if not enable:
        return lambda prompt: "0.7"
    try:
        from .agent_client import SimpleChatLLM
    except Exception:
        try:
            from src.researcher.analysis.agent.agent_client import SimpleChatLLM
        except Exception:
            return lambda prompt: "0.7"
    try:
        name = (config_name or get_common_model_name()).strip()
        path = config_path or get_model_config_path()
        cli = SimpleChatLLM(config_name=name, config_path=path)
        if getattr(cli, "client", None) is None:
            return lambda prompt: "0.7"
        return lambda prompt: cli.chat(user_query=prompt, system_prompt="Return ONLY a number between 0 and 1", temperature=0.3)
    except Exception:
        return lambda prompt: "0.7"
