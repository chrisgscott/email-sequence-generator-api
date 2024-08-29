import os
from pydantic_settings import BaseSettings
from typing import List
from datetime import timezone
from app.core.prompts import EMAIL_PROMPT, SECTIONS_PROMPT, SUBJECT_PROMPT

class EmailSection(BaseSettings):
    name: str
    description: str
    word_count: str

class Settings(BaseSettings):
    PROJECT_NAME: str = "Email Sequence Generator API"
    PROJECT_VERSION: str = "1.0.0"
    OPENAI_API_KEY: str
    DATABASE_URL: str
    BREVO_API_KEY: str
    BREVO_EMAIL_TEMPLATE_ID: int
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TOP_P: float = 1.0
    OPENAI_FREQUENCY_PENALTY: float = 0.0
    OPENAI_PRESENCE_PENALTY: float = 0.0
    SEQUENCE_LENGTH: int = 52 # Number of emails in the sequence    
    SEQUENCE_FREQUENCY_DAYS: int = 7  # How many days between emails   
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str 
    EMAIL_SECTIONS: List[EmailSection] = [
        EmailSection(name="intro_content", description="A brief introduction", word_count="30-50"),
        EmailSection(name="week_task", description="The main task or focus for the week", word_count="50-100"),
        EmailSection(name="quick_tip", description="A short, actionable tip related to the week's task", word_count="20-30"),
        EmailSection(name="cta", description="A call-to-action encouraging further engagement", word_count="20-30")
    ]
    BATCH_SIZE: int = 10

    # OpenAI prompt settings
    OPENAI_EMAIL_PROMPT: str = EMAIL_PROMPT
    OPENAI_SECTIONS_PROMPT: str = SECTIONS_PROMPT
    OPENAI_SUBJECT_PROMPT: str = SUBJECT_PROMPT

    class Config:
        env_file = ".env"

settings = Settings()

print("All settings loaded:")
for key, value in settings.dict().items():
    if key not in ['EMAIL_SECTIONS', 'OPENAI_API_KEY', 'BREVO_API_KEY']:  # Exclude sensitive or large data
        print(f"{key}: {value}")

TIMEZONE = timezone.utc