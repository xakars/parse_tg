import asyncio
import json
import os.path
from typing import Any
from httpx import Limits

import aiofiles

from clients.async_dpseek_client import AsyncDeepseekClient
from clients.tg_client import tg_client
from config import get_settings
from utils.logger import logger
from utils.vacancy_filter import is_python_vacancy

settings = get_settings()


async def fetch_vacancies_from_channel(channel: str, limit: int):
    logger.info(f"Получение постов из канала {channel}")
    vacancies: dict[str, dict[int, Any]] = {}
    try:
        vacancies[channel] = {}
        async for message in tg_client.iter_messages(channel, limit=limit):
            if message.text and is_python_vacancy(text=message.text):
                vacancies[channel][message.id] = {
                    "text": message.text,
                    "post_date": message.date.isoformat(),
                    "post_link": f"https://t.me/{channel}/{message.id}",
                }

    except Exception as e:
        logger.error("Ошибка при обработке канала %s: %s", channel, e, exc_info=True)

    return vacancies


async def save_vacancies_to_file(
        filepath: str,
        new_vacancies: dict[str, dict[int, Any]],
) -> None:
    existing_data: dict[str, dict[str, Any]] = {}
    if os.path.exists(filepath):
        try:
            async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
                content = await f.read()
                existing_data = json.loads(content)
        except Exception as e:
            logger.error("Ошибка при чтении существующего файла %s: %s", filepath, e)

    for channel, posts in new_vacancies.items():
        if channel not in existing_data:
            existing_data[channel] = {}

        for post_id, post_content in posts.items():
            str_post_id = str(post_id)
            if str_post_id not in existing_data[channel]:
                existing_data[channel][str_post_id] = post_content

    try:
        async with aiofiles.open(filepath, mode="w", encoding="utf-8") as f:
            json_string = json.dumps(existing_data, ensure_ascii=False, indent=4)
            await f.write(json_string)
        logger.info("Данные успешно сохранены в файл: %s", filepath)
    except Exception as e:
        logger.error("Не удалось сохранить файл %s: %s", filepath, e, exc_info=True)


async def main() -> None:
    async with tg_client:
        await tg_client.start(phone=settings.TG.PHONE_NUMBER)
        target_channels: list[str] = settings.TG.TARGET_CHANNEL_USERNAME
        posts_limit: int = settings.TG.POSTS_LIMIT

        tasks = [
            fetch_vacancies_from_channel(channel, posts_limit)
            for channel in target_channels
        ]

        results = await asyncio.gather(*tasks)

        all_vacancies = {}
        for result in results:
            all_vacancies.update(result)

        await save_vacancies_to_file("processed_posts.json", all_vacancies)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Скрипт остановлен пользователем.")
