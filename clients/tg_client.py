from telethon import TelegramClient

from config import get_settings
from utils.logger import logger

settings = get_settings()


def create_telegram_client() -> TelegramClient:
    logger.info(f"Инициализация Telegram сессии: {settings.TG.SESSION_NAME}")
    return TelegramClient(
        session=settings.TG.SESSION_NAME,
        api_id=settings.TG.API_ID,
        api_hash=settings.TG.API_HASH,
    )


tg_client = create_telegram_client()
