import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import EmailStr, ValidationError, BaseModel
from app.db.database import get_db, SessionLocal
from app.schemas import sequence as sequence_schema
from app.schemas.sequence import SequenceCreate, SequenceResponse, EmailContent  # Add EmailContent here
from app.services import openai_service, email_service, sequence_service
from datetime import datetime, timedelta, timezone
from app.services.email_service import send_email
from app.core.config import settings
from loguru import logger

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    logger.info("Webhook endpoint hit")
    try:
        raw_data = await request.body()
        logger.info(f"Received webhook data: {raw_data.decode()}")

        data = await request.json()
        logger.info(f"Parsed JSON data: {data}")

        topic = data.get("topic") or data.get("form_fields", {}).get("topic") or data.get("topic_field")
        inputs = data.get("inputs") or data.get("form_fields") or {}
        recipient_email = data.get("recipient_email") or data.get("form_fields", {}).get("email") or data.get("email_field")

        logger.info(f"Extracted fields - topic: {topic}, recipient_email: {recipient_email}, inputs: {inputs}")

        if not topic or not recipient_email:
            raise ValueError("Missing required fields: topic and recipient_email")

        class EmailValidator(BaseModel):
            email: EmailStr

        try:
            EmailValidator(email=recipient_email)
        except ValidationError:
            raise ValueError(f"Invalid email address: {recipient_email}")

        sequence = sequence_schema.SequenceCreate(
            topic=topic,
            inputs=inputs,
            recipient_email=recipient_email
        )

        # Create a database session
        db = SessionLocal()
        try:
            # Create a placeholder sequence in the database
            db_sequence = sequence_service.create_empty_sequence(db, sequence)

            # Start the email generation as a background task
            background_tasks.add_task(generate_and_store_email_sequence, db_sequence.id, sequence)

            logger.info("Webhook processed successfully")
            return {"message": "Webhook processed successfully", "sequence_id": db_sequence.id}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate):
    db = SessionLocal()
    try:
        emails = []
        for batch in range(0, settings.SEQUENCE_LENGTH, settings.BATCH_SIZE):
            batch_emails = openai_service.generate_email_sequence(
                sequence.topic, 
                sequence.inputs, 
                start_index=batch, 
                batch_size=settings.BATCH_SIZE
            )
            emails.extend(batch_emails)
            # Update sequence progress in the database
            sequence_service.update_sequence_progress(db, sequence_id, len(emails))

        sequence_service.finalize_sequence(db, sequence_id, emails)
        # Schedule emails
        for email in emails:
            email_service.send_email_background(db, sequence.recipient_email, email, sequence.inputs)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating email sequence: {str(e)}")
        sequence_service.mark_sequence_failed(db, sequence_id, str(e))
    finally:
        db.close()

@router.post("/sequences", response_model=SequenceResponse)
def create_sequence(sequence: SequenceCreate, db: Session = Depends(get_db)):
    try:
        emails = openai_service.generate_email_sequence(sequence.topic, sequence.inputs)
        db_sequence = sequence_service.create_sequence(db, sequence, emails)
        
        current_time = datetime.now(timezone.utc)
        db_sequence.created_at = current_time
        db_sequence.updated_at = current_time
        
        for i, email in enumerate(db_sequence.emails):
            scheduled_for = current_time + timedelta(days=i * settings.SEQUENCE_FREQUENCY_DAYS)
            email.scheduled_for = scheduled_for
            try:
                api_response = email_service.send_email(sequence.recipient_email, email, sequence.inputs)
                email.sent_to_brevo = True
                email.sent_to_brevo_at = current_time
                email.brevo_message_id = api_response.message_id
            except Exception as e:
                logger.error(f"Failed to schedule email {email.id} with Brevo: {str(e)}")
        
        db.commit()
        return db_sequence
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating sequence: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating sequence")

def schedule_next_batch_of_emails(sequence, days=30):
    cutoff_date = datetime.now() + timedelta(days=days)
    emails_to_schedule = [email for email in sequence.emails if email.scheduled_for <= cutoff_date and not email.sent_to_brevo]
    
    for email in emails_to_schedule:
        try:
            api_response = email_service.send_email(sequence.recipient_email, email, sequence.inputs)
            email.sent_to_brevo = True
            email.sent_to_brevo_at = datetime.now(timezone.utc)
            email.brevo_message_id = api_response.message_id
        except Exception as e:
            logger.error(f"Failed to schedule email {email.id} with Brevo: {str(e)}")
    
    db.commit()

@router.post("/test_email_scheduling")
def test_email_scheduling(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        current_time = datetime.utcnow()
        test_email = EmailContent(
            subject="Test Email Scheduling",
            content={
                "intro_content": "This is a test email for scheduling",
                "week_task": "Test the email scheduling system",
                "quick_tip": "Always test your code",
                "cta": "Check if this email arrives on time"
            },
            scheduled_for=current_time + timedelta(minutes=1)
        )
        
        recipient_email = "chrisgscott@gmail.com"
        send_email(recipient_email, test_email, {"param1": "test_value"})
        
        return {"message": "Test email sent successfully"}
    except Exception as e:
        logger.error(f"Error in test_email_scheduling: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
