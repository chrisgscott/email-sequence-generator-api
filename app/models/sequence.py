from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    inputs = Column(JSON)
    recipient_email = Column(String)
    is_active = Column(Boolean, default=True)
    next_email_date = Column(DateTime(timezone=True))
    progress = Column(Integer, default=0)
    status = Column(String, default="pending")
    error_message = Column(String, nullable=True)
    
    emails = relationship("Email", back_populates="sequence")