from pathlib import Path

import os

from dotenv import load_dotenv


if os.getenv("PYTHON_DOTENV_DISABLED", "").lower() not in {"1", "true", "yes"}:
    load_dotenv()


class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    database_path: str = os.getenv("DATABASE_PATH", "data/ai_job_agent.db")

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


settings = Settings()
