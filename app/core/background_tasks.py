from asyncio import Queue
from pydantic import BaseModel
from app.db.database import SessionLocal
from app.models.sequence import Sequence
from app.schemas.sequence import SequenceCreate, EmailSection
from app.services import sequence_service
from app.services.sequence_generation import generate_and_store_email_sequence
from loguru import logger
from typing import List

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
            topic_depth=submission.topic_depth
        )
        db_sequence = sequence_service.create_sequence(db, sequence_create)
        sequence_id = db_sequence.id

        await generate_and_store_email_sequence(sequence_id, sequence_create)
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        raise
    finally:
        db.close()