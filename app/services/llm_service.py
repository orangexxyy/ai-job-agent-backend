from typing import Any, Dict, List, Optional

from app.config import settings


class LLMService:
    """Minimal placeholder wrapper for future DeepSeek-compatible calls."""

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
        return {
            "success": False,
            "message": "LLM calls are intentionally not implemented in Step 1.",
            "provider": self.provider,
            "model": model or self.model,
            "temperature": temperature,
            "timeout": timeout,
            "messages_count": len(messages),
        }


llm_service = LLMService()
