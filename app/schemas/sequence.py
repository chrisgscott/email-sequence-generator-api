from pydantic import BaseModel, Field, EmailStr, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

class EmailSection(BaseModel):
    name: str
    word_count: Union[int, str]
    description: str

    @validator('word_count')
    def validate_word_count(cls, v):
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            if '-' in v:
                min_count, max_count = map(str.strip, v.split('-'))
                if min_count.isdigit() and max_count.isdigit():
                    return v
            elif v.isdigit():
                return int(v)
        raise ValueError('word_count must be an integer or a range (e.g., "75 - 150")')

class EmailBase(BaseModel):
    subject: str
    content: Dict[str, str]
    scheduled_for: datetime

class EmailContent(EmailBase):
    pass

class SequenceCreate(BaseModel):
    topic: str
    recipient_email: str
    form_id: str
    brevo_list_id: int
    total_emails: int
    days_between_emails: int
    email_structure: List[EmailSection]
    inputs: Dict[str, str]
    topic_depth: int = Field(default=5, ge=1, le=10)

class SequenceResponse(BaseModel):
    id: int
    form_id: str
    topic: str
    recipient_email: EmailStr
    brevo_list_id: int
    total_emails: int
    days_between_emails: int
    email_structure: List[EmailSection]
    inputs: Dict[str, str]
    is_active: bool
    next_email_date: Optional[datetime]
    progress: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    emails: List[EmailContent]