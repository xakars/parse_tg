import pandas as pd

from utils.json_tools import load_json
from utils.logger import logger


async def export_to_excel(json_path: str, excel_path: str = "parsed_vacancies.xlsx") -> None:
    data = await load_json(json_path)
    if not data:
        logger.warning(f"База данных {json_path} пуста или не существует. Экспорт отменен.")
        return

    flattened_rows = []

    for channel, posts in data.items():
        for post_id, post_content in posts.items():
            if not post_content.get("is_extracted"):
                continue

            extracted_info = post_content.get("extracted_info", {})

            if extracted_info.get("is_python") is False:
                continue

            row = {
                "Канал": channel,
                "Ссылка на пост": post_content.get("post_link", ""),
                "Дата публикации": post_content.get("post_date", ""),
                "Компания": extracted_info.get("company", "Не указана"),
                "Должность": extracted_info.get("position", "Не указана"),
                "Зарплата": extracted_info.get("salary", "Не указана"),
                "Обязанности": extracted_info.get("job_responsibilities", ""),
                "Краткое описание": extracted_info.get("summary", ""),
                "Контакты": extracted_info.get("contact", ""),
                "Сопроводительное письмо": post_content.get("cover_letter", "Не генерировалось"),
            }
            flattened_rows.append(row)

    if not flattened_rows:
        logger.warning("После фильтрации не найдено ни одной валидной Python-вакансии для экспорта.")
        return

    df = pd.DataFrame(flattened_rows)

    if "Дата публикации" in df.columns:
        df["Дата публикации"] = pd.to_datetime(df["Дата публикации"], errors="coerce")
        df = df.sort_values(by="Дата публикации", ascending=False)
        df["Дата публикации"] = df["Дата публикации"].dt.strftime("%Y-%m-%d %H:%M")

    try:
        df.to_excel(excel_path, index=False, engine="openpyxl")
        logger.info(f"Успешно экспортировано {len(flattened_rows)} вакансий в Excel: {excel_path}")
    except Exception as e:
        logger.error(f"Не удалось сохранить Excel файл {excel_path}: {e}", exc_info=True)
