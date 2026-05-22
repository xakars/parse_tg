import json
import os
from typing import Any

import aiofiles

from utils.logger import logger


async def load_json(filepath: str) -> dict[str, Any]:
    if not os.path.exists(filepath):
        return {}
    try:
        async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content) if content else {}
    except Exception as e:
        logger.error(f"Ошибка чтения {filepath}: {e}")
        return {}


async def save_json(filepath: str, data: dict[str, Any]):
    try:
        async with aiofiles.open(filepath, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    except Exception as e:
        logger.error(f"Ошибка сохранения {filepath}: {e}")
