from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, index=True)
    topic = Column(String, index=True)
    recipient_email = Column(String, index=True)
    brevo_list_id = Column(Integer)
    total_emails = Column(Integer)
    days_between_emails = Column(Integer)
    email_structure = Column(JSON)
    inputs = Column(JSON)
    is_active = Column(Boolean, default=True)
    next_email_date = Column(DateTime(timezone=True))
    progress = Column(Integer, default=0)
    status = Column(String, default="pending")
    error_message = Column(String, nullable=True)

    emails = relationship("Email", back_populates="sequence")
