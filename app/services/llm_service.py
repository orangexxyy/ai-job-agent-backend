import json
from typing import Any, Dict, List, Optional

import requests

from app.config import settings


class LLMService:
    """封装 DeepSeek-compatible Chat Completions 调用。

    主要输入：OpenAI-compatible messages、temperature、timeout 和可选 model。
    主要输出：调用状态、模型文本、可选 JSON 解析结果和 debug 元信息。
    副作用：可能访问外部 LLM API；不写数据库，不发送 HR 消息，不自动投递。
    """

    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.api_key_configured = bool(settings.deepseek_api_key)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        timeout: int = 30,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        model_name = model or self.model
        if not settings.deepseek_api_key:
            return self._failure(
                message="api_key_missing",
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                messages_count=len(messages),
            )

        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            raw = response.json()
            content = (
                raw.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            parsed_json = _parse_json_content(content)
            return {
                "success": parsed_json is not None,
                "message": "ok" if parsed_json is not None else "json_parse_failed",
                "llm_used": True,
                "content": content,
                "parsed_json": parsed_json,
                "provider": self.provider,
                "model": model_name,
                "temperature": temperature,
                "timeout": timeout,
                "messages_count": len(messages),
                "raw_text": None if parsed_json is not None else content,
            }
        except (requests.RequestException, ValueError) as exc:
            return self._failure(
                message=str(exc),
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                messages_count=len(messages),
            )

    def _failure(
        self,
        *,
        message: str,
        model: str,
        temperature: float,
        timeout: int,
        messages_count: int,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "llm_used": False,
            "content": "",
            "parsed_json": None,
            "provider": self.provider,
            "model": model,
            "temperature": temperature,
            "timeout": timeout,
            "messages_count": messages_count,
        }


def _parse_json_content(content: str) -> Optional[Dict[str, Any]]:
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


llm_service = LLMService()
