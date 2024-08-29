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
async def webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    logger.info("Webhook endpoint hit")
    try:
        # Log the raw incoming data
        raw_data = await request.body()
        logger.info(f"Received webhook data: {raw_data.decode()}")

        # Parse the incoming JSON data
        data = await request.json()
        logger.info(f"Parsed JSON data: {data}")

        # Extract the required fields, with fallbacks
        topic = data.get("topic") or data.get("form_fields", {}).get("topic") or data.get("topic_field")
        inputs = data.get("inputs") or data.get("form_fields") or {}
        recipient_email = data.get("recipient_email") or data.get("form_fields", {}).get("email") or data.get("email_field")

        if not topic or not recipient_email:
            raise ValueError("Missing required fields: topic and recipient_email")

        # Validate email
        class EmailValidator(BaseModel):
            email: EmailStr

        try:
            EmailValidator(email=recipient_email)
        except ValidationError:
            raise ValueError(f"Invalid email address: {recipient_email}")

        # Create SequenceCreate object
        sequence = sequence_schema.SequenceCreate(
            topic=topic,
            inputs=inputs,
            recipient_email=recipient_email
        )

        # Generate email sequence using OpenAI
        emails = openai_service.generate_email_sequence(sequence.topic, sequence.inputs)

        # Create new sequence in database
        db_sequence = sequence_service.create_sequence(db, sequence, emails)

        # Schedule emails using background tasks
        for email in db_sequence.emails:
            email_service.send_email_background(background_tasks, sequence.recipient_email, email, sequence.inputs)

        logger.info("Webhook processed successfully")
        return {"message": "Webhook received and processed successfully", "sequence_id": db_sequence.id}
    except ValueError as ve:
        logger.error(f"Validation error in webhook: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        # Create a test email
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
        
        # Send the email immediately to test the new send_email function
        recipient_email = "chrisgscott@gmail.com"  # Replace with your test email
        send_email(recipient_email, test_email, {"param1": "test_value"})
        
        return {"message": "Test email sent successfully"}
    except Exception as e:
        logger.error(f"Error in test_email_scheduling: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def check_and_schedule_emails():
    db = SessionLocal()
    try:
        sequences = db.query(Sequence).all()
        for sequence in sequences:
            schedule_next_batch_of_emails(sequence)
    finally:
        db.close()