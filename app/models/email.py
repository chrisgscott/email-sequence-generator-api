from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base

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

    sequence = relationship("Sequence", back_populates="emails")