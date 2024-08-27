from pydantic import BaseModel, EmailStr
from typing import Dict, List
from datetime import datetime

class EmailContent(BaseModel):
    subject: str
    scheduled_for: datetime
    content: Dict[str, str]

class SequenceBase(BaseModel):
    topic: str
    inputs: Dict[str, str]
    recipient_email: EmailStr

class SequenceCreate(SequenceBase):
    pass

class Sequence(SequenceBase):
    id: int
    emails: List[EmailContent]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True