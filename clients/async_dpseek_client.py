from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from pydantic import SecretStr

DEFAULT_API_BASE = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


class AsyncDeepseekClient(httpx.AsyncClient):
    _initialized_instance: Optional['AsyncDeepseekClient'] = None

    def __init__(
        self,
        deepseek_api_key: str | SecretStr,
        deepseek_base_url: str = DEFAULT_API_BASE,
        deepseek_model: str = DEFAULT_DEEPSEEK_MODEL,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(base_url=deepseek_base_url, *args, **kwargs)
        self.deepseek_model = deepseek_model
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_base_url = deepseek_base_url

    @classmethod
    def initialize(cls, *args: Any, **kwargs: Any) -> 'AsyncDeepseekClient':
        if cls._initialized_instance is None:
            cls._initialized_instance = cls(*args, **kwargs)
        return cls._initialized_instance


    @classmethod
    def get_initialized_instance(cls) -> 'AsyncDeepseekClient':
        if cls._initialized_instance is None:
            raise ValueError("Клиент еще не был инициализирован! Сначала вызовите AsyncDeepseekClient.initialize(...)")
        return cls._initialized_instance
