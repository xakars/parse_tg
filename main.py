import asyncio
import json
import os.path
from typing import Any

import aiofiles
import pandas as pd
from httpx import Limits
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_openai import ChatOpenAI

from clients.async_dpseek_client import AsyncDeepseekClient
from clients.tg_client import tg_client
from config import get_settings
from schemas.extract_prompt import prompt_template
from schemas.job_schemas import JobVacancy
from utils.logger import logger
from utils.vacancy_filter import is_python_vacancy
from utils.json_tools import load_json, save_json

settings = get_settings()


async def fetch_vacancies_from_channel(channel: str, limit: int):
    logger.info(f"Получение постов из канала {channel}")
    found_vacancies: dict[str, dict[int, Any]] = {}
    try:
        found_vacancies[channel] = {}
        async for message in tg_client.iter_messages(channel, limit=limit):
            if message.text and is_python_vacancy(text=message.text):
                found_vacancies[channel][message.id] = {
                    "text": message.text,
                    "post_date": message.date.isoformat(),
                    "post_link": f"https://t.me/{channel}/{message.id}",
                    "is_extracted": False
                }

    except Exception as e:
        logger.error("Ошибка при обработке канала %s: %s", channel, e, exc_info=True)

    return found_vacancies


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


async def extract_vacancies(json_path: str, excel_path: str):
    vacancies = await load_json(json_path)

    pending_tasks = [] #Посты которые еще не обрабатывались LLM
    task_keys = []

    for channel, posts in vacancies.items():
        for post_id, post in posts.items():
            if not post.get("is_extracted"):
                pending_tasks.append(HumanMessage(content=post["text"]))
                task_keys.append((channel, post_id))

    if not pending_tasks:
        logger.info("Нет новых вакансий для обработки LLM.")
        return

    http_async_client = AsyncDeepseekClient.get_initialized_instance()
    llm = ChatOpenAI(
        model=http_async_client.deepseek_model,
        api_key=http_async_client.deepseek_api_key,
        base_url=str(http_async_client.base_url),
        http_async_client=http_async_client,
        temperature=0,
    )

    chain = (
            prompt_template
            | llm.bind_tools(tools=[JobVacancy], tool_choice="JobVacancy")
            | PydanticToolsParser(tools=[JobVacancy])
    )

    logger.info(f"Отправка {len(pending_tasks)} постов в DeepSeek...")
    inputs = [{"messages": [msg]} for msg in pending_tasks]
    results = await chain.abatch(inputs, config={"max_concurrency": 5})

    extracted_data = []
    for (channel, post_id), res in zip(task_keys, results):
        if res:
            item = res[0] if isinstance(res, list) else res
            vacancies[channel][post_id]["extracted_info"] = item.model_dump()
            vacancies[channel][post_id]["is_extracted"] = True
            extracted_data.append(item.model_dump())

    await save_json(json_path, vacancies)

    all_results = []
    for ch in vacancies.values():
        for p in ch.values():
            if p.get("is_extracted") and "extracted_info" in p:
                all_results.append(p["extracted_info"])

    if all_results:
        pd.DataFrame(all_results).to_excel(excel_path, index=False)
        logger.info(f"Excel обновлен: {excel_path}")

async def main() -> None:
    AsyncDeepseekClient.initialize(
        deepseek_api_key=settings.DEEPSEEK.API_KEY,
        timeout=settings.DEEPSEEK.TIMEOUT,
        limits=Limits(max_connections=settings.DEEPSEEK.MAX_CONNECTIONS),
    )

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

        await extract_vacancies("processed_posts.json", excel_path="parsed_vacancies.xlsx")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Скрипт остановлен пользователем.")
