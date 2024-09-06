from asyncio import Queue
from pydantic import BaseModel
from app.db.database import SessionLocal
from app.models.sequence import Sequence
from app.schemas.sequence import SequenceCreate, EmailSection
from app.services import sequence_service
from app.services.sequence_generation import generate_and_store_email_sequence
from app.services.brevo_service import subscribe_to_brevo_list
from loguru import logger
from typing import List
from datetime import time
import sentry_sdk

class SubmissionQueue(BaseModel):
    form_id: str
    topic: str
    recipient_email: str
    brevo_list_id: int
    total_emails: int
    days_between_emails: int
    email_structure: List[EmailSection]
    inputs: dict
    topic_depth: int
    preferred_time: time
    timezone: str

async def process_submission_queue(queue: Queue):
    while True:
        submission = await queue.get()
        try:
            await process_submission(submission)
        except Exception as e:
            logger.error(f"Error processing submission: {str(e)}")
        finally:
            queue.task_done()

async def process_submission(submission: SubmissionQueue):
    db = SessionLocal()
    try:
        sequence_create = SequenceCreate(
            form_id=submission.form_id,
            topic=submission.topic,
            recipient_email=submission.recipient_email,
            brevo_list_id=submission.brevo_list_id,
            total_emails=submission.total_emails,
            days_between_emails=submission.days_between_emails,
            email_structure=submission.email_structure,
            inputs=submission.inputs,
            topic_depth=submission.topic_depth,
            preferred_time=submission.preferred_time,
            timezone=submission.timezone
        )
        db_sequence = sequence_service.create_sequence(db, sequence_create)
        sequence_id = db_sequence.id

        # Subscribe the email to Brevo list
        try:
            subscribe_to_brevo_list(submission.recipient_email, submission.brevo_list_id)
            logger.info(f"Email {submission.recipient_email} subscribed to Brevo list {submission.brevo_list_id}")
        except Exception as brevo_error:
            logger.error(f"Failed to subscribe email to Brevo: {str(brevo_error)}")
            sentry_sdk.capture_exception(brevo_error)
            # Continue with the process even if Brevo subscription fails

        await generate_and_store_email_sequence(sequence_id, sequence_create)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error processing submission: {str(e)}")
        raise
    finally:
        db.close()