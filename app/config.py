from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="sqlite:///db/agent.db",
        alias="DATABASE_URL",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    developer_prompt_path: Path = Field(
        default=Path("prompts/developer.md"),
        alias="DEVELOPER_PROMPT_PATH",
    )
    chat_history_run_limit: int = Field(
        default=10,
        alias="CHAT_HISTORY_RUN_LIMIT",
        gt=0,
    )
    agent_loop_max_rounds: int = Field(
        default=10,
        alias="AGENT_LOOP_MAX_ROUNDS",
        gt=0,
    )
    oss_access_key_id: str = Field(default="", alias="OSS_ACCESS_KEY_ID")
    oss_access_key_secret: str = Field(default="", alias="OSS_ACCESS_KEY_SECRET")
    oss_region: str = Field(default="", alias="OSS_REGION")
    oss_bucket: str = Field(default="", alias="OSS_BUCKET")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
