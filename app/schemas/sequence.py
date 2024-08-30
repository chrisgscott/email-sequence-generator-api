from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from datetime import datetime

class EmailSection(BaseModel):
    name: str
    word_count: str

class EmailBase(BaseModel):
    subject: str
    content: Dict[str, str]
    scheduled_for: datetime

class EmailContent(EmailBase):
    pass

class SequenceCreate(BaseModel):
    form_id: str
    topic: str
    recipient_email: EmailStr
    brevo_list_id: int
    total_emails: int
    days_between_emails: int
    email_structure: List[EmailSection]
    inputs: Dict[str, str]

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