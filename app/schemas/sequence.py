from pydantic import BaseModel, EmailStr
from typing import Dict, List
from datetime import datetime
from typing import Optional

class EmailContent(BaseModel):
    subject: str
    scheduled_for: datetime
    content: Dict[str, str]
    sent_to_brevo: bool = False
    sent_to_brevo_at: Optional[datetime] = None
    brevo_message_id: Optional[str] = None

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

class SequenceResponse(BaseModel):
    id: int
    topic: str
    inputs: Dict[str, str]
    recipient_email: str
    emails: List[EmailContent]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True