from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List, ClassVar, Optional, Dict, Any
from datetime import timezone
from app.core.prompts import EMAIL_PROMPT, SECTIONS_PROMPT, SUBJECT_PROMPT
import os
from pydantic import validator

# Load the .env file
load_dotenv(override=True)

class EmailSection(BaseSettings):
    """
    Defines the structure for each section of the email content.
    """
    name: str  # The name of the section (e.g., "intro_content", "week_task")
    description: str  # A brief description of what this section should contain
    word_count: str  # The target word count for this section, as a string (e.g., "30-50")

class Settings(BaseSettings):
    """
    Contains all the configuration settings for the Email Sequence Generator API.
    These settings can be overridden by environment variables.
    """
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Email Sequence Generator API")
    PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    
    @validator("DATABASE_URL", pre=True)
    def set_database_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if values.get("ENVIRONMENT") == "dev":
            return values.get("DEV_DATABASE_URL") or v
        return v

    # API Keys and Authentication
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY")
    BREVO_EMAIL_TEMPLATE_ID: int = int(os.getenv("BREVO_EMAIL_TEMPLATE_ID", "1"))
    BREVO_PASSWORD_RESET_TEMPLATE_ID: int = int(os.getenv("BREVO_PASSWORD_RESET_TEMPLATE_ID", "4"))

    # OpenAI Model Configuration
    OPENAI_MODEL: str = "gpt-4o-mini"  # The OpenAI model to use for generating email content
    OPENAI_MAX_TOKENS: int = 12000  # Maximum number of tokens to generate in each API call
    OPENAI_TEMPERATURE: float = 0.7  # Controls randomness in generation (0.0 - 1.0)
    OPENAI_TOP_P: float = 1.0  # Controls diversity of word choices
    OPENAI_FREQUENCY_PENALTY: float = 0.0  # Reduces repetition of token sequences (-2.0 to 2.0)
    OPENAI_PRESENCE_PENALTY: float = 0.0  # Encourages the model to talk about new topics (-2.0 to 2.0)

    # Email Sequence Configuration
    SEQUENCE_LENGTH: int = 52  # Total number of emails in a sequence
    SEQUENCE_FREQUENCY_DAYS: int = 7  # Number of days between each email in the sequence

    # Email Sender Configuration
    EMAIL_FROM: str = "chris@chrisgscott.me"  # Email address used as the sender
    EMAIL_FROM_NAME: str = "Chris Scott"  # Name to be displayed as the sender

    # Email Content Structure
    EMAIL_SECTIONS: List[EmailSection] = [
        EmailSection(name="intro_content", description="A brief introduction", word_count="30-50"),
        EmailSection(name="week_task", description="The main task or focus for the week", word_count="50-100"),
        EmailSection(name="quick_tip", description="A short, actionable tip related to the week's task", word_count="20-30"),
        EmailSection(name="cta", description="A call-to-action encouraging further engagement", word_count="20-30")
    ]

    # API and Processing Configuration
    BATCH_SIZE: int = 10  # Number of emails to generate in each batch
    OPENAI_REQUEST_TIMEOUT: int = 240  # Timeout for OpenAI API requests in seconds

    # OpenAI Prompt Settings
    OPENAI_EMAIL_PROMPT: ClassVar[str] = """Generate {batch_size} unique emails for an email sequence about {topic}. Each email should be different and cover aspects of the topic according to the depth setting.

{depth_instruction}

Previously covered topics:
{previous_topics}

Please consider these topics and generate content according to the depth setting.

Use the following inputs to personalize the content:
{inputs}

For each email, generate the following sections:
{sections_prompt}

{subject_prompt}

Return the result as a JSON array with {batch_size} items.
"""
    OPENAI_SECTIONS_PROMPT: ClassVar[str] = "Section {index}: {name}\nDescription: {description}\nWord Count: {word_count}"  # Prompt for generating individual email sections
    OPENAI_SUBJECT_PROMPT: ClassVar[str] = SUBJECT_PROMPT  # Prompt for generating email subject lines

    # API Key Settings
    API_KEY_LENGTH: int = 32

    # Authentication Settings
    SECRET_KEY: str = "cyrus-and-chris-and-adrienne-like-horses-and-like-stuff-69"  # Change this to a secure random string
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")  # Connection string for the database
    DEV_DATABASE_URL: Optional[str] = None

    # Sentry DSN
    SENTRY_DSN: str = os.getenv("SENTRY_DSN")

    # WordPress Credentials
    WORDPRESS_URL: Optional[str] = None
    WORDPRESS_USERNAME: Optional[str] = None
    WORDPRESS_PASSWORD: Optional[str] = None

    # Password Reset Configuration
    BASE_URL: str = "https://plankton-app-qivtq.ondigitalocean.app/admin"  # Replace with your actual base URL
    BREVO_PASSWORD_RESET_TEMPLATE_ID: int = 2  # Replace with your actual template ID for password reset emails
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24

    # Pexels API Key
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY")

    class Config:
        env_file = (".env", ".env.dev")  # Specifies the files to load environment variables from

settings = Settings()

TIMEZONE = timezone.utc