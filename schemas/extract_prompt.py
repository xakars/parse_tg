from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Ты — AI-ассистент для извлечения структурированной информации из текста вакансий.

            Правила:
            - Извлекай только информацию, которая явно присутствует в тексте.
            - Не придумывай отсутствующие данные.
            - Если поле отсутствует — верни None.
            - salary извлекай как указано в тексте.
            - summary напиши кратко (1–2 предложения).
            - job_responsibilities сформулируй кратко.
            - contact извлекай полностью, как указано в вакансии.
            """,

        ),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Извлеки данные и верни ответ строго в структуре JobVacancy.."),
    ],
)
