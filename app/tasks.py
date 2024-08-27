import logging
from app.worker import celery_app
from app.services import email_service
from app.db.database import SessionLocal
from app.models.sequence import Sequence
from app.models.email import Email
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@celery_app.task
def send_scheduled_emails():
    logger.info("send_scheduled_emails task started")
    db = SessionLocal()
    try:
        current_time = datetime.now(timezone.utc)
        logger.info(f"Checking for emails scheduled before {current_time}")
        emails_to_send = db.query(Email).join(Sequence).filter(
            Email.scheduled_for <= current_time,
            Email.sent == False
        ).all()
        
        logger.info(f"Found {len(emails_to_send)} emails to send")

        for email in emails_to_send:
            try:
                logger.info(f"Attempting to send email {email.id}")
                email_service.send_email(
                    to_email=email.sequence.recipient_email,
                    email_content=email,
                    params=email.sequence.inputs
                )
                email.sent = True
                email.sent_at = current_time
                db.commit()
                logger.info(f"Email {email.id} sent successfully")
            except Exception as e:
                db.rollback()
                logger.error(f"Error sending email {email.id}: {str(e)}")

    finally:
        db.close()
    logger.info("send_scheduled_emails task completed")