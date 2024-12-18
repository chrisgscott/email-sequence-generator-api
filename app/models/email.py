from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime

class EmailBase(BaseModel):
    subject: str
    content: Dict[str, str]
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    scheduled_for: Optional[datetime] = None
    image_url: Optional[str] = None
    photographer: Optional[str] = None
    pexels_url: Optional[str] = None

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("sequences.id"))
    subject = Column(String)
    content = Column(JSONB)  # This will store the dynamic content sections
    scheduled_for = Column(DateTime)
    sent_to_brevo = Column(Boolean, default=False)
    sent_to_brevo_at = Column(DateTime, nullable=True)
    brevo_message_id = Column(String, nullable=True)
    category = Column(String)
    tags = Column(JSONB)
    image_url = Column(String)
    photographer = Column(String)
    pexels_url = Column(String)

    sequence = relationship("Sequence", back_populates="emails")
