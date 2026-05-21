from pydantic import BaseModel, Field


class JobVacancy(BaseModel):
    company: str = Field(default=None, description="Название компании")
    position: str = Field(default=None, description="Название должности")
    salary: str = Field(default=None, description="Заработная плата или вилка, если указана")
    job_responsibilities: str = Field(default=None, description="Кратко что надо делать")
    summary: str = Field(default=None, description="Краткое описание сути вакансии (1-2 предложения)")
    contact: str = Field(default=None, description="Контакт кому и куда писать, если указан")
