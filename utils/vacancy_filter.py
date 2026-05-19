
PYTHON_KEYWORDS = ["python", "питон", "fastapi", "django", "flask", "asyncio"]
STOP_KEYWORDS = ["бесплатный", "практикум", "собес", "эфир", "ищу работу", "ищу middle", "подборка курсов", "обучение"]
JOB_KEYWORDS = ["вакансия", "job", "hiring", "ищем", "требуется", "позиция", "fulltime", "удаленка"]


def is_python_vacancy(text: str) -> bool:
    text_lower = text.lower()

    if any(stop_word in text_lower for stop_word in STOP_KEYWORDS):
        return False

    has_python = any(py_word in text_lower for py_word in PYTHON_KEYWORDS)

    has_job = any(job_word in text_lower for job_word in JOB_KEYWORDS)

    return has_python and has_job
