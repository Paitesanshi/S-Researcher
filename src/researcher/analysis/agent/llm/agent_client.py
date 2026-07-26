import json
import re
from typing import Any, Dict, Optional
from onesim.models.core.model_manager import ModelManager

class SimpleChatLLM:
    def __init__(self, config_name: str, config_path: str):
        # 初始化模型管理器
        self.model_manager = ModelManager.get_instance()
        self.model_manager.initialize(config_path)

        # 获取模型实例
        self.model = self.model_manager.get_model(config_name=config_name)
        self.model_name = getattr(self.model, "model_name", config_name)

        # client 是对接到具体 API 的
        self.client = getattr(self.model, "client", None)

    def chat(self, user_query: str, system_prompt: str = "You are a helpful assistant", temperature: Optional[float] = None, extra_body: Optional[Dict[str, Any]] = None):
        if not self.client:
            raise RuntimeError("No client available for chat")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        req_extra = {"chat_template_kwargs": {"enable_thinking": False}}
        if isinstance(extra_body, dict):
            req_extra.update(extra_body)
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=(0.9 if temperature is None else float(temperature)),
            extra_body=req_extra,
        )
        return resp.choices[0].message.content

    def _strip_code_fences(self, text: str) -> str:
        import re
        if not isinstance(text, str):
            return text
        cleaned = re.sub(r"^\s*```(?:json|python|[\w-]+)?\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        return cleaned.strip()

    def chat_json(self, user_query: str, system_prompt: str = "You are a helpful assistant", temperature: Optional[float] = None) -> Dict[str, Any]:
        content = self.chat(user_query=user_query, system_prompt=system_prompt, temperature=temperature)
        # 新增：先去除 Markdown 代码块包裹
        content_clean = self._strip_code_fences(content)
        try:
            return json.loads(content_clean)
        except Exception as e:
            print("chat_json: initial JSON parsing failed:", str(e))
            if isinstance(content_clean, str):
                print("chat_json: unparsed model output:", content_clean)
        if isinstance(content_clean, str):
            start = content_clean.find("{")
            end = content_clean.rfind("}")
            if start != -1 and end != -1 and end > start:
                substr = content_clean[start : end + 1]
                try:
                    return json.loads(substr)
                except Exception as e2:
                    print("chat_json: substring parsing failed:", str(e2))
                    print("chat_json: attempted substring:", substr)
        raise ValueError("The model response is not valid JSON.")

    def choose_analysis_methods(
        self,
        research_paradigm: Optional[str],
        research_question: Optional[str],
        category: Optional[str] = None,
        time_field: Optional[str] = None,
        value_field: Optional[str] = None,
        group_fields: Optional[list] = None,
        allowed_methods: Optional[list] = None,
        alpha: Optional[float] = 0.05,
        max_methods: int = 3,
        temperature: Optional[float] = 0.3,
    ) -> Dict[str, Any]:
        """
        Ask the LLM to select 1-3 statistical methods with minimal, low-bias prompting.
        Returns a compact JSON: {"methods":[{"name":..., "params": {...}}, ...]}.
        """
        if allowed_methods is None:
            allowed_methods = ["group_mean_compare", "robust_ols", "trend_correlation"]

        # Minimal context to reduce bias and over-correction
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
            "instruction": (
                "Select 1-3 statistical methods that directly address the research_question within the given research_paradigm. "
                "Use only names from allowed_methods. Prefer parameters using available schema fields when relevant. "
                "Avoid clustering methods. Return ONLY compact JSON: {'methods': [...]} with no explanations."
            ),
        }

        system_prompt = "Return ONLY valid JSON with a top-level 'methods' list. No explanations."
        user_query = json.dumps(context, ensure_ascii=False)

        try:
            plan = self.chat_json(user_query=user_query, system_prompt=system_prompt, temperature=temperature)
        except Exception:
            plan = None

        # Very light validation and fallback to avoid heavy fix-ups
        methods = []
        if isinstance(plan, dict) and isinstance(plan.get("methods"), list):
            for m in plan.get("methods")[:max_methods]:
                if isinstance(m, dict) and m.get("name") in allowed_methods:
                    params = m.get("params") if isinstance(m.get("params"), dict) else {}
                    methods.append({"name": m["name"], "params": params})

        # Minimal fallback if LLM failed to return usable methods
        if not methods:
            methods = [
                {
                    "name": "trend_correlation",
                    "params": {
                        "x": (time_field or "time"),
                        "y": "endpoint",
                        "method": "spearman",
                    },
                }
            ]

        return {"methods": methods}

    def _encode_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_image_extension(self, image_path: str) -> str:
        import os
        ext = os.path.splitext(image_path)[1].lower().strip(".")
        return ext or "png"

    def chat_multimodal(
        self,
        user_text: str = "",
        image_paths: Optional[list] = None,
        system_prompt: str = "You are a helpful assistant that can see images",
        temperature: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        content_parts: Optional[list] = None,
    ) -> str:
        """
        多模态聊天：支持文本 + 多张图片（本地路径）。
        图片会被读取并转为 base64 data URL，以符合 OpenAI 兼容接口的 image_url 格式。
        """
        if not self.client:
            raise RuntimeError("No client available for chat")
        import os
        parts = []
        if isinstance(user_text, str) and user_text.strip():
            parts.append({"type": "text", "text": user_text})
        if isinstance(content_parts, list):
            parts.extend(content_parts)
        for p in (image_paths or []):
            if isinstance(p, str) and os.path.exists(p):
                ext = self._get_image_extension(p)
                data = self._encode_image(p)
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{ext};base64,{data}"},
                })
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": parts if parts else user_text},
        ]
        req_extra = {"chat_template_kwargs": {"enable_thinking": False}}
        if isinstance(extra_body, dict):
            req_extra.update(extra_body)
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=(0.9 if temperature is None else float(temperature)),
            extra_body=req_extra,
        )
        return resp.choices[0].message.content

    def chat_multimodal_json(
        self,
        user_text: str = "",
        image_paths: Optional[list] = None,
        system_prompt: str = "Return ONLY valid JSON.",
        temperature: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        content_parts: Optional[list] = None,
    ) -> Dict[str, Any]:
        content = self.chat_multimodal(
            user_text=user_text,
            image_paths=image_paths,
            system_prompt=system_prompt,
            temperature=temperature,
            extra_body=extra_body,
            content_parts=content_parts,
        )
        content_clean = self._strip_code_fences(content)
        try:
            return json.loads(content_clean)
        except Exception:
            if isinstance(content_clean, str):
                start = content_clean.find("{")
                end = content_clean.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return json.loads(content_clean[start : end + 1])
        raise ValueError("The model response is not valid JSON.")

if __name__ == "__main__":
    llm = SimpleChatLLM(config_name="default-chat", config_path="config/model_config.json")
    reply = llm.chat("hello")
    print("Model response:", reply)
