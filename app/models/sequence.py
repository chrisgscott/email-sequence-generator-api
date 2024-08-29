from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    inputs = Column(JSON)
    recipient_email = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    next_email_date = Column(DateTime(timezone=True), nullable=True)

    emails = relationship("Email", back_populates="sequence", cascade="all, delete-orphan")