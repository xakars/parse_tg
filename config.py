from functools import lru_cache

from pydantic import BaseModel, Field, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeepSeekSettings(BaseModel):
    API_KEY: str | SecretStr = Field(description="Your API Key")
    MAX_CONNECTIONS: PositiveInt = Field(default=5, description="Maximum number of connections")
    TIMEOUT: PositiveInt = Field(default=20, description="Connection timeout")


class TelegramSettings(BaseSettings):
    API_ID: int = Field(description="API ID от my.telegram.org")
    API_HASH: str = Field(description="API Hash от my.telegram.org")
    PHONE_NUMBER: str = Field(description="Номер телефона в международном формате")
    SESSION_NAME: str = Field(default="job_parser", description="Your session name")
    TARGET_CHANNEL_USERNAME: list[str] = Field(default_factory=list, description="Target channel username")
    POSTS_LIMIT: PositiveInt = Field(default=10, description="Кол-во последних постов")


class Settings(BaseSettings):
    DEEPSEEK: DeepSeekSettings
    TG: TelegramSettings
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
