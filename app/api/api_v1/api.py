import json
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import EmailStr, ValidationError, BaseModel
from app.db.database import get_db, SessionLocal
from app.schemas import sequence as sequence_schema
from app.schemas.sequence import SequenceCreate, SequenceResponse, EmailContent
from app.services import openai_service, email_service, sequence_service
from datetime import datetime, timedelta, timezone
from app.services.email_service import send_email
from app.core.config import settings
from loguru import logger
from app.core.exceptions import AppException

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    logger.info("Webhook endpoint hit")
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
        
        # Parse the JSON data
        topic = data.get("topic")
        recipient_email = data.get("recipient_email")
        inputs = data.get("inputs", {})
        
        logger.info(f"Parsed JSON data: {data}")
        logger.info(f"Extracted fields - topic: {topic}, recipient_email: {recipient_email}, inputs: {inputs}")
        
        # Validate required fields
        if not all([topic, recipient_email, inputs]):
            raise ValueError("Missing required fields in webhook data")
        
        # Create a SequenceCreate object
        sequence_create = SequenceCreate(topic=topic, recipient_email=recipient_email, inputs=inputs)
        
        # Create the sequence in the database
        db = SessionLocal()
        try:
            db_sequence = Sequence(topic=topic, recipient_email=recipient_email, inputs=inputs)
            db.add(db_sequence)
            db.commit()
            db.refresh(db_sequence)
            sequence_id = db_sequence.id
        finally:
            db.close()
        
        # Start the email sequence generation process in the background
        background_tasks.add_task(generate_and_store_email_sequence, sequence_id, sequence_create, background_tasks)
        
        logger.info("Webhook processed successfully")
        return {"message": "Webhook processed successfully", "sequence_id": sequence_id}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate, background_tasks: BackgroundTasks):
    logger.info(f"Starting email sequence generation for sequence_id: {sequence_id}")
    db = SessionLocal()
    try:
        emails = []
        for batch in range(0, settings.SEQUENCE_LENGTH, settings.BATCH_SIZE):
            logger.info(f"Generating batch {batch // settings.BATCH_SIZE + 1} of {(settings.SEQUENCE_LENGTH + settings.BATCH_SIZE - 1) // settings.BATCH_SIZE} for sequence_id: {sequence_id}")
            try:
                batch_emails = await asyncio.wait_for(
                    openai_service.generate_email_sequence(
                        sequence.topic,
                        sequence.inputs,
                        batch,
                        min(settings.BATCH_SIZE, settings.SEQUENCE_LENGTH - batch)
                    ),
                    timeout=150  # 2.5 minutes timeout
                )
                emails.extend(batch_emails)
            except TimeoutError:
                logger.error(f"Timeout occurred while generating batch {batch // settings.BATCH_SIZE + 1} for sequence_id: {sequence_id}")
                # Handle the timeout (e.g., skip this batch or use a fallback)
                continue

        logger.info(f"Email generation complete for sequence_id: {sequence_id}. Finalizing sequence.")
        sequence_service.finalize_sequence(db, sequence_id, emails)
        logger.info(f"Sequence finalized for sequence_id: {sequence_id}")
        
        db.commit()
    except AppException as e:
        logger.error(f"Error generating email sequence for sequence_id: {sequence_id}: {str(e)}")
        sequence_service.mark_sequence_failed(db, sequence_id, str(e))
        db.commit()
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
