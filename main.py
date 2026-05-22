import asyncio
import json
import os.path
from typing import Any

import aiofiles
from httpx import Limits
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.runnables import RunnableConfig

from clients.async_dpseek_client import AsyncDeepseekClient
from clients.tg_client import tg_client
from config import get_settings
from prompt import cover_letter_prompt_template, extract_prompt_template
from schemas.job_schemas import JobVacancy
from utils.json_tools import load_json, save_json
from utils.logger import logger
from utils.vacancy_filter import is_python_vacancy

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
                    "is_extracted": False,
                    "is_covered": False,
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


async def extract_vacancies_with_llm(json_path: str):
    vacancies = await load_json(json_path)

    pending_tasks = []  # Посты которые еще не обрабатывались LLM
    task_keys = []

    for channel, posts in vacancies.items():
        for post_id, post in posts.items():
            if not post.get("is_extracted"):
                pending_tasks.append(HumanMessage(content=post["text"]))
                task_keys.append((channel, post_id))

    if not pending_tasks:
        logger.info("Нет новых вакансий для обработки LLM.")
        return

    llm = AsyncDeepseekClient.create_langchain_adapter(default_temperature=0.0)

    chain = (
            extract_prompt_template
            | llm.bind_tools(tools=[JobVacancy], tool_choice="JobVacancy")
            | PydanticToolsParser(tools=[JobVacancy])
    )

    logger.info(f"Отправка {len(pending_tasks)} постов в DeepSeek...")
    inputs = [{"messages": [msg]} for msg in pending_tasks]
    results = await chain.abatch(inputs, config=RunnableConfig(max_concurrency=5))

    extracted_data = []
    for (channel, post_id), res in zip(task_keys, results):
        if res:
            item = res[0] if isinstance(res, list) else res
            vacancies[channel][post_id]["extracted_info"] = item.model_dump()
            vacancies[channel][post_id]["is_extracted"] = True
            extracted_data.append(item.model_dump())

    await save_json(json_path, vacancies)


async def generate_cover_letter(json_path: str, resume_path: str = "resume.txt"):
    vacancies = await load_json(json_path)
    if not os.path.exists(resume_path):
        logger.error(f"Файл с резюме не найден по пути: {resume_path}")
        return

    async with aiofiles.open(resume_path, mode="r", encoding="utf-8") as f:
        resume_content = await f.read()

    to_process = []
    task_keys = []
    for channel, posts in vacancies.items():
        for post_id, post in posts.items():
            if post.get("is_extracted") and not post.get("is_covered"):
                vacancy_summary = post.get("extracted_info", {})
                if vacancy_summary.get("is_python") is False:
                    logger.info(f"Пропуск вакансии {post_id}: LLM определила её как не-Python.")
                    vacancies[channel][post_id]["is_covered"] = True
                    vacancies[channel][post_id]["cover_letter"] = "Пропущено: не относится к Python."
                    continue
                user_message_content = (
                    f"### РЕЗЮМЕ КАНДИДАТА:\n{resume_content}\n\n"
                    f"### ДАННЫЕ ВАКАНСИИ:\n{vacancy_summary}\n\n"
                )
                to_process.append(HumanMessage(content=user_message_content))
                task_keys.append((channel, post_id))

    if not to_process:
        logger.info("Нет новых вакансий для добавления Cover letter.")
        return

    logger.info(f"Запуск генерации сопроводительных писем для {len(to_process)} вакансий...")

    llm = AsyncDeepseekClient.create_langchain_adapter(default_temperature=0.7)

    chain = cover_letter_prompt_template | llm

    inputs = [{"messages": [msg]} for msg in to_process]

    try:
        results = await chain.abatch(inputs, config=RunnableConfig(max_concurrency=3))

        for (channel, post_id), response in zip(task_keys, results):
            vacancies[channel][post_id]["cover_letter"] = response.content.strip()
            vacancies[channel][post_id]["is_covered"] = True
        await save_json(json_path, vacancies)
        logger.info("Все сопроводительные письма успешно добавлены в JSON базу.")

    except Exception as e:
        logger.error(f"Ошибка при генерации писем через abatch: {e}", exc_info=True)


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

        jons_db = "processed_posts.json"

        await save_vacancies_to_file(filepath=jons_db, new_vacancies=all_vacancies)

        await extract_vacancies_with_llm(json_path=jons_db)

        await generate_cover_letter(json_path=jons_db)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Скрипт остановлен пользователем.")
