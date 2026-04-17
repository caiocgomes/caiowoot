from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    database_path: str = "data/caiowoot.db"
    app_password: str = ""
    session_max_age: int = 604800  # 7 days in seconds
    operators: str = ""  # comma-separated list of operator names
    admin_operator: str = ""  # operator name with admin privileges (default: first in OPERATORS)
    evolution_webhook_secret: str = ""  # empty = disabled
    timezone: str = "America/Sao_Paulo"
    rewarm_auto_send: bool = False  # quando True, pipeline de rewarm envia sem revisão humana
    cold_mentoria_monthly_cap: int = 15  # cap de ofertas de mentoria por mês no cold rewarm

    model_config = {"env_file": ".env"}

    @property
    def operator_list(self) -> list[str]:
        if not self.operators:
            return []
        return [name.strip() for name in self.operators.split(",") if name.strip()]


settings = Settings()


def now_local() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))
