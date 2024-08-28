import os
from pydantic_settings import BaseSettings
from typing import List

class EmailSection(BaseSettings):
    name: str
    description: str
    word_count: str

class Settings(BaseSettings):
    PROJECT_NAME: str = "Email Sequence Generator API"
    PROJECT_VERSION: str = "1.0.0"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
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
    SEQUENCE_LENGTH: int = 12
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str  # Add this line
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    EMAIL_SECTIONS: List[EmailSection] = [
        EmailSection(name="intro_content", description="A brief introduction", word_count="30-50"),
        EmailSection(name="week_task", description="The main task or focus for the week", word_count="50-100"),
        EmailSection(name="quick_tip", description="A short, actionable tip related to the week's task", word_count="20-30"),
        EmailSection(name="cta", description="A call-to-action encouraging further engagement", word_count="20-30")
    ]

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"Loaded REDIS_URL: {self.REDIS_URL}")
        print(f"Environment REDIS_URL: {os.environ.get('REDIS_URL', 'Not set')}")

settings = Settings()

print("All settings loaded:")
for key, value in settings.dict().items():
    if key not in ['EMAIL_SECTIONS', 'OPENAI_API_KEY', 'BREVO_API_KEY']:  # Exclude sensitive or large data
        print(f"{key}: {value}")