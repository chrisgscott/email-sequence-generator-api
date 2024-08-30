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
from app.models.sequence import Sequence
import asyncio
from asyncio import Queue
from app.core.background_tasks import process_submission_queue, SubmissionQueue

router = APIRouter()
logger = logging.getLogger(__name__)

submission_queue = Queue()
queue_processor_running = False

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
            raise AppException("Missing required fields in webhook data", status_code=400)
        
        # Create a SubmissionQueue object
        submission = SubmissionQueue(topic=topic, recipient_email=recipient_email, inputs=inputs)
        
        # Add submission to the queue
        await submission_queue.put(submission)
        
        # Start the queue processor if it's not already running
        global queue_processor_running
        if not queue_processor_running:
            background_tasks.add_task(process_submission_queue, submission_queue)
            queue_processor_running = True
        
        logger.info("Webhook processed successfully")
        return {"message": "Submission queued successfully"}
    except AppException as e:
        logger.error(f"AppException in webhook: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate):
    logger.info(f"Starting email sequence generation for sequence_id: {sequence_id}")
    db = SessionLocal()
    try:
        db_sequence = sequence_service.get_sequence(db, sequence_id)
        if not db_sequence:
            raise AppException(f"Sequence {sequence_id} not found", status_code=404)

        total_batches = (settings.SEQUENCE_LENGTH + settings.BATCH_SIZE - 1) // settings.BATCH_SIZE
        start_batch = db_sequence.progress * total_batches // 100

        for batch in range(start_batch * settings.BATCH_SIZE, settings.SEQUENCE_LENGTH, settings.BATCH_SIZE):
            batch_number = batch // settings.BATCH_SIZE + 1
            logger.info(f"Generating batch {batch_number} of {total_batches} for sequence_id: {sequence_id}")
            try:
                batch_emails = await asyncio.wait_for(
                    openai_service.generate_email_sequence(
                        sequence.topic,
                        sequence.inputs,
                        batch,
                        min(settings.BATCH_SIZE, settings.SEQUENCE_LENGTH - batch),
                        buffer_time=timedelta(hours=1)
                    ),
                    timeout=180  # 3 minutes timeout
                )
                sequence_service.add_emails_to_sequence(db, sequence_id, batch_emails)
                logger.info(f"Saved batch {batch_number} to database for sequence_id: {sequence_id}")
                
                progress = min(100, int((batch_number / total_batches) * 100))
                sequence_service.update_sequence_progress(db, sequence_id, progress)
                
                db.commit()
            except asyncio.TimeoutError:
                logger.error(f"Timeout occurred while generating batch {batch_number} for sequence_id: {sequence_id}")
                sequence_service.update_sequence_progress(db, sequence_id, progress)
                db.commit()
                raise AppException("Timeout occurred while generating email sequence", status_code=504)
            except AppException as e:
                logger.error(f"AppException generating batch {batch_number} for sequence_id: {sequence_id}: {str(e)}")
                sequence_service.mark_sequence_failed(db, sequence_id, str(e))
                db.commit()
                raise
            except Exception as e:
                logger.error(f"Unexpected error generating batch {batch_number} for sequence_id: {sequence_id}: {str(e)}")
                sequence_service.mark_sequence_failed(db, sequence_id, str(e))
                db.commit()
                raise AppException(f"Unexpected error: {str(e)}", status_code=500)

        logger.info(f"Email generation complete for sequence_id: {sequence_id}. Finalizing sequence.")
        sequence_service.finalize_sequence(db, sequence_id)
        logger.info(f"Sequence finalized for sequence_id: {sequence_id}")
        db.commit()
    except AppException:
        # Re-raise AppExceptions as they are already handled
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating email sequence for sequence_id: {sequence_id}: {str(e)}")
        sequence_service.mark_sequence_failed(db, sequence_id, str(e))
        db.commit()
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)
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
            except AppException as e:
                logger.error(f"Failed to schedule email {email.id} with Brevo: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error scheduling email {email.id} with Brevo: {str(e)}")
        
        db.commit()
        return db_sequence
    except AppException as e:
        db.rollback()
        logger.error(f"AppException creating sequence: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating sequence: {str(e)}")
        raise AppException(f"Error creating sequence: {str(e)}", status_code=500)

def schedule_next_batch_of_emails(sequence, days=30):
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() + timedelta(days=days)
        emails_to_schedule = [email for email in sequence.emails if email.scheduled_for <= cutoff_date and not email.sent_to_brevo]
        
        for email in emails_to_schedule:
            try:
                api_response = email_service.send_email(sequence.recipient_email, email, sequence.inputs)
                email.sent_to_brevo = True
                email.sent_to_brevo_at = datetime.now(timezone.utc)
                email.brevo_message_id = api_response.message_id
            except AppException as e:
                logger.error(f"Failed to schedule email {email.id} with Brevo: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error scheduling email {email.id} with Brevo: {str(e)}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in schedule_next_batch_of_emails: {str(e)}")
        raise AppException(f"Error scheduling emails: {str(e)}", status_code=500)
    finally:
        db.close()

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
    except AppException as e:
        logger.error(f"AppException in test_email_scheduling: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in test_email_scheduling: {str(e)}")
        raise AppException(f"Error in test email scheduling: {str(e)}", status_code=500)

@router.post("/sequences/{sequence_id}/retry", response_model=SequenceResponse)
async def retry_sequence_generation(sequence_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        sequence = sequence_service.get_sequence(db, sequence_id)
        if not sequence:
            raise AppException("Sequence not found", status_code=404)
        
        if sequence.status not in ["failed", "pending"]:
            raise AppException("Sequence is not in a retryable state", status_code=400)
        
        sequence_create = SequenceCreate(topic=sequence.topic, recipient_email=sequence.recipient_email, inputs=sequence.inputs)
        background_tasks.add_task(generate_and_store_email_sequence, sequence_id, sequence_create)
        
        return SequenceResponse(id=sequence.id, status="retrying")
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in retry_sequence_generation: {str(e)}")
        raise AppException(f"Error retrying sequence generation: {str(e)}", status_code=500)
