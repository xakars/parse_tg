# parse-tg

Парсер вакансий из Telegram-каналов с фильтрацией Python-позиций, извлечением структурированных данных через DeepSeek и генерацией сопроводительных писем.

## Что делает проект

Скрипт проходит по заданным Telegram-каналам, забирает последние посты и оставляет только те, что похожи на Python-вакансии. Дальше данные обогащаются в несколько этапов:

1. **Сбор постов** — Telethon читает каналы параллельно, сохраняет текст, дату и ссылку на пост.
2. **Предфильтр** — эвристики по ключевым словам (`utils/vacancy_filter.py`): Python-стек, маркеры вакансии, стоп-слова (курсы, «ищу работу» и т.п.), исключение явно не-Python ролей.
3. **Извлечение полей (LLM)** — DeepSeek через LangChain заполняет схему `JobVacancy` (компания, должность, зарплата, обязанности, контакты, флаг `is_python`).
4. **Сопроводительные письма** — для вакансий с `is_python: true` генерируется короткое письмо на основе `resume.txt`.
5. **Экспорт** — итоговая таблица в `parsed_vacancies.xlsx`.

Повторные запуски не дублируют посты: в `processed_posts.json` уже обработанные записи помечаются флагами `is_extracted` и `is_covered`.

## Структура репозитория

```
parse_tg/
├── main.py                 # точка входа, весь пайплайн
├── config.py               # настройки из .env (Pydantic Settings)
├── prompt.py               # системные промпты для LLM
├── clients/
│   ├── tg_client.py        # Telethon-клиент
│   └── async_dpseek_client.py  # HTTP-клиент + LangChain ChatOpenAI
├── schemas/
│   └── job_schemas.py      # Pydantic-модель вакансии
└── utils/
    ├── vacancy_filter.py   # ключевые слова для отбора постов
    ├── json_tools.py       # чтение/запись JSON
    ├── save_to.py          # экспорт в Excel
    └── logger.py
```

## Требования

- Python **≥ 3.13**
- [uv](https://docs.astral.sh/uv/) (рекомендуется) или другой менеджер зависимостей
- Аккаунт Telegram и API-ключи с [my.telegram.org](https://my.telegram.org)
- API-ключ [DeepSeek](https://platform.deepseek.com)

## Установка

```bash
git clone <url-репозитория>
cd parse_tg
uv sync
```

Создайте файл `.env` в корне проекта:

```env
# DeepSeek
DEEPSEEK__API_KEY=sk-...
DEEPSEEK__MAX_CONNECTIONS=5
DEEPSEEK__TIMEOUT=20

# Telegram (my.telegram.org)
TG__API_ID=12345678
TG__API_HASH=your_api_hash
TG__PHONE_NUMBER=+79001234567
TG__SESSION_NAME=job_parser
TG__POSTS_LIMIT=50

# Список каналов без @, через запятую в JSON или несколько переменных — см. pydantic-settings
# Пример для одного канала (в .env как JSON-массив):
TG__TARGET_CHANNEL_USERNAME=["python_jobs","remote_python"]
```

Положите текст резюме в `resume.txt` (файл в `.gitignore`, в репозиторий не коммитится).

## Запуск

```bash
uv run python main.py
```

При первом запуске Telethon запросит код подтверждения из Telegram; сессия сохранится в файл `{TG__SESSION_NAME}.session`.

### Результаты работы

| Файл | Описание |
|------|----------|
| `processed_posts.json` | Накопительная база постов по каналам |
| `parsed_vacancies.xlsx` | Таблица с извлечёнными полями и cover letter |
| `*.session` | Сессия Telegram (не коммитить) |

## Настройка каналов и фильтров

- **Каналы** — `TG__TARGET_CHANNEL_USERNAME`: username канала без `@` (публичные каналы).
- **Глубина** — `TG__POSTS_LIMIT`: сколько последних сообщений читать с каждого канала.
- **Предфильтр** — списки `PYTHON_KEYWORDS`, `JOB_KEYWORDS`, `STOP_KEYWORDS`, `NON_PYTHON_ROLES` в `utils/vacancy_filter.py`.
- **Повторная обработка LLM** — в JSON можно вручную сбросить `is_extracted` / `is_covered` у нужного поста, чтобы перезапустить этап.

## Поведение LLM

- **Извлечение** (`extract_vacancies_with_llm`): temperature `0.0`, structured output через tool `JobVacancy`, до 5 параллельных запросов.
- **Cover letter** (`generate_cover_letter`): temperature `0.7`, до 3 параллельных запросов; вакансии с `is_python: false` пропускаются.

Промпты задаются в `prompt.py`.

## Разработка

```bash
# линтер (в Makefile указан путь ./app — при необходимости запускайте напрямую)
uv run ruff check .
uv run ruff check --fix .

# pre-commit (если установлен dev-зависимости)
uv sync --extra dev
pre-commit install
```

Зависимости описаны в `pyproject.toml`, lock-файл — `uv.lock`.

## Ограничения

- Нужен доступ к каналам (подписка или публичный канал).
- Предфильтр по ключевым словам может пропустить нетипичные формулировки или, наоборот, принять лишнее — финальная проверка роли делается полем `is_python` у LLM.
- Расход API DeepSeek зависит от числа новых постов и генерации писем.
- Секреты и персональные данные (`.env`, `resume.txt`, сессии, выгрузки) не должны попадать в git — они уже в `.gitignore`.
