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

    model_config = {"env_file": ".env"}


settings = Settings()
