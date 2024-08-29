from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from datetime import datetime

class EmailBase(BaseModel):
    subject: str
    content: Dict[str, str]
    scheduled_for: datetime

class EmailContent(EmailBase):
    pass

class SequenceCreate(BaseModel):
    topic: str
    inputs: Dict[str, str]
    recipient_email: EmailStr

class SequenceResponse(BaseModel):
    id: int
    topic: str
    inputs: Dict[str, str]
    recipient_email: EmailStr
    created_at: datetime
    updated_at: datetime
    status: str
    progress: int
    emails: List[EmailContent]