from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class WebhookSubmission(Base):
    __tablename__ = "webhook_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String, index=True)
    topic = Column(String)
    recipient_email = Column(String)
    brevo_list_id = Column(Integer)
    brevo_template_id = Column(Integer)
    sequence_settings = Column(JSON)
    email_structure = Column(JSON)
    inputs = Column(JSON)
    topic_depth = Column(Integer)
    preferred_time = Column(String)
    timezone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_payload = Column(JSON)