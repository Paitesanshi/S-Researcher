import json
import os
from typing import Any, Dict, Optional, List

# bag import SimpleChatLLM
try:
    from researcher.analysis.agent.llm.agent_client import SimpleChatLLM
except Exception:
    try:
        from ..llm.agent_client import SimpleChatLLM
    except Exception:
        from src.researcher.analysis.agent.agent_client import SimpleChatLLM  # type: ignore

# import TOOLS
try:
    from researcher.analysis.agent.utils.tool_registry import TOOLS
except Exception:
    try:
        from ..utils.tool_registry import TOOLS
    except Exception:
        from src.researcher.analysis.agent.tool_registry import TOOLS  # type: ignore

import argparse


class MethodChooserAgent:
    def __init__(
        self,
        config_name: Optional[str] = None,
        config_path: Optional[str] = None,
        llm: Optional[SimpleChatLLM] = None,
    ) -> None:
        # bag import SimpleChatLLM
        if llm is not None:
            self.llm = llm
        else:
            model_name = config_name or os.environ.get("ONESIM_MODEL_NAME") or "default-chat"
            model_config = config_path or os.environ.get("ONESIM_MODEL_CONFIG") or "config/model_config.json"
            self.llm = SimpleChatLLM(config_name=model_name, config_path=model_config)

    def choose_analysis_methods(
        self,
        research_paradigm: Optional[str],
        research_question: Optional[str],
        category: Optional[str] = None,
        time_field: Optional[str] = None,
        value_field: Optional[str] = None,
        group_fields: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        alpha: Optional[float] = 0.05,
        max_methods: int = 3,
        temperature: Optional[float] = 0.3,
    ) -> Dict[str, Any]:
        """
        request LLM to choose 1-3 statistical methods.
        return compact JSON: {"methods":[{"name":..., "params": {...}}, ...]}
        """
        # allowed_methods change to all TOOLS
        if allowed_methods is None:
            allowed_methods = sorted(list(TOOLS.keys()))

        # get full TOOLS list, helping LLM to choose methods
        tools_catalog = [
            {"name": name, "description": tool.get("description", ""), "args": tool.get("args", [])}
            for name, tool in TOOLS.items()
        ]

        context = {
            "research_paradigm": research_paradigm,
            "research_question": research_question,
            "category": category,
            "schema": {
                "time_field": time_field,
                "value_field": value_field,
                "group_fields": group_fields,
            },
            "constraints": {
                "allowed_methods": allowed_methods,
                "alpha": alpha,
                "max_methods": max_methods,
            },
            "tools_catalog": tools_catalog,
            "instruction": (
                "Select 1-3 methods strictly from allowed_methods/tools_catalog that best address the research_question. "
                "For each selected method, return JSON with: { 'methods': [ { 'name': <method_name>, 'params': { ... } } ] }. "
                "The 'name' MUST be one of allowed_methods. 'params' MUST include all required keys defined by tools_catalog args, "
                "excluding 'data' and any variadic marker like '*samples'. For example, fill 'group_col', 'value_col', 'x', 'y', 'formula', etc. "
                "Use provided schema fields when relevant: time_field, value_field, group_fields. If a field is categorical, wrap in C(...) within formulas. "
                "Do not use markdown code fences. Return ONLY valid JSON with top-level 'methods' and NO explanations."
            ),
        }

        system_prompt = (
            "You must return ONLY valid JSON with a top-level 'methods' list. "
            "Do NOT use markdown code fences."
        )
        user_query = json.dumps(context, ensure_ascii=False)

        try:
            plan = self.llm.chat_json(
                user_query=user_query,
                system_prompt=system_prompt,
                temperature=0.0,
            )
        except Exception:
            # 新增：当 JSON 解析失败时，打印原始 LLM 输出
            try:
                raw_content = self.llm.chat(
                    user_query=user_query,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                print("[MethodChooserAgent RAW]", raw_content)
            except Exception:
                raw_content = None
            plan = None

        methods: List[Dict[str, Any]] = []
        invalid_names: List[str] = []
        if isinstance(plan, dict) and isinstance(plan.get("methods"), list):
            for m in plan.get("methods")[:max_methods]:
                if isinstance(m, dict):
                    name = m.get("name")
                    params = m.get("params") if isinstance(m.get("params"), dict) else {}
                    if name in allowed_methods:
                        # 新增：缺参校验（按照 TOOLS[name].args，排除 'data' 与 '*samples'）
                        required_args = [a for a in TOOLS.get(name, {}).get("args", []) if a != "data" and not str(a).startswith("*")]
                        missing = [a for a in required_args if a not in params]
                        if missing:
                            # 构造一次修复提示，要求补齐缺失参数
                            repair_payload = {
                                "previous_plan": plan,
                                "method_to_repair": name,
                                "missing_params": missing,
                                "schema": {
                                    "time_field": time_field,
                                    "value_field": value_field,
                                    "group_fields": group_fields,
                                },
                                "tools_catalog": tools_catalog,
                                "instruction": (
                                    "Repair the JSON by adding the missing 'params' keys for the specified method. "
                                    "Use provided schema fields when relevant. Return ONLY the full corrected JSON object; no text. "
                                    "Do not use markdown code fences."
                                ),
                            }
                            try:
                                repaired = self.llm.chat_json(
                                    user_query=json.dumps(repair_payload, ensure_ascii=False),
                                    system_prompt=system_prompt,
                                    temperature=0.0,
                                )
                                if isinstance(repaired, dict) and isinstance(repaired.get("methods"), list):
                                    plan = repaired
                                    # 重新取该方法项（若存在）
                                    m = next((itm for itm in plan.get("methods", []) if isinstance(itm, dict) and itm.get("name") == name), m)
                                    params = m.get("params") if isinstance(m.get("params"), dict) else params
                            except Exception as e:
                                print("[MethodChooserAgent REPAIR] Repair failed:", str(e))
                        methods.append({"name": name, "params": params})
                    else:
                        invalid_names.append(name)
                elif isinstance(m, str):  # 允许字符串方法名，空参占位
                    if m in allowed_methods:
                        methods.append({"name": m, "params": {}})
                    else:
                        invalid_names.append(m)

        # 当方法为空或全被过滤，打印调试信息并回退
        if not methods:
            try:
                print("[MethodChooserAgent DEBUG] Methods were empty or filtered")
                print("[MethodChooserAgent DEBUG] plan:", json.dumps(plan, ensure_ascii=False))
            except Exception:
                print("[MethodChooserAgent DEBUG] Plan is not serializable:", plan)
            if invalid_names:
                print("[MethodChooserAgent DEBUG] Filtered method names:", invalid_names)
            print("[MethodChooserAgent DEBUG] allowed_methods_count:", len(allowed_methods) if allowed_methods else 0)
            # 再次打印原始 LLM 响应，辅助定位
            try:
                raw_content2 = self.llm.chat(
                    user_query=user_query,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                print("[MethodChooserAgent RAW2]", raw_content2)
            except Exception as e:
                print("[MethodChooserAgent RAW2 failed]", str(e))

            methods = [
                {
                    "name": "time_series_correlation",
                    "params": {
                        "x": (time_field or "time"),
                        "y": (value_field or "endpoint"),
                    },
                }
            ]

        return {"methods": methods}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MethodChooserAgent CLI")
    parser.add_argument("--research-paradigm", dest="research_paradigm", default=None)
    parser.add_argument("--research-question", dest="research_question", default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--time-field", dest="time_field", default="step")
    parser.add_argument("--value-field", dest="value_field", default="data")
    parser.add_argument("--group-fields", dest="group_fields", nargs="*", default=["group_name"])  # e.g., group_name
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--max-methods", dest="max_methods", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--config-name", dest="config_name", default=os.environ.get("ONESIM_MODEL_NAME", "default-chat"))
    parser.add_argument("--config-path", dest="config_path", default=os.environ.get("ONESIM_MODEL_CONFIG", "config/model_config.json"))
    parser.add_argument("--allowed", dest="allowed_methods", nargs="*", default=None, help="限制可选方法子集（不传则使用 TOOLS 全量）")

    args = parser.parse_args(argv)

    agent = MethodChooserAgent(config_name=args.config_name, config_path=args.config_path)
    result = agent.choose_analysis_methods(
        research_paradigm=args.research_paradigm,
        research_question=args.research_question,
        category=args.category,
        time_field=args.time_field,
        value_field=args.value_field,
        group_fields=args.group_fields,
        allowed_methods=args.allowed_methods,
        alpha=args.alpha,
        max_methods=args.max_methods,
        temperature=args.temperature,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
