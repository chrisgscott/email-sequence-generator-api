from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base
from zoneinfo import ZoneInfo
from sqlalchemy.sql import func
from .email import Email

class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, index=True)
    topic = Column(String)
    recipient_email = Column(String)
    brevo_list_id = Column(Integer)
    total_emails = Column(Integer)
    days_between_emails = Column(Integer)
    email_structure = Column(JSONB)
    inputs = Column(JSONB)
    is_active = Column(Boolean, default=True)
    next_email_date = Column(DateTime(timezone=True))
    progress = Column(Integer, default=0)
    status = Column(String, default="pending")
    error_message = Column(String, nullable=True)
    preferred_time = Column(Time, nullable=False, default=func.time('09:00:00'))
    timezone = Column(String, nullable=False, default='UTC')

    emails = relationship("Email", back_populates="sequence")
