from asyncio import Queue
from pydantic import BaseModel
from app.db.database import SessionLocal
from app.models.sequence import Sequence
from app.schemas.sequence import SequenceCreate
from app.services import sequence_service
from app.services.sequence_generation import generate_and_store_email_sequence
from loguru import logger

class SubmissionQueue(BaseModel):
    topic: str
    recipient_email: str
    inputs: dict

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
        db_sequence = Sequence(topic=submission.topic, recipient_email=submission.recipient_email, inputs=submission.inputs)
        db.add(db_sequence)
        db.commit()
        db.refresh(db_sequence)
        sequence_id = db_sequence.id

        sequence_create = SequenceCreate(topic=submission.topic, recipient_email=submission.recipient_email, inputs=submission.inputs)
        await generate_and_store_email_sequence(sequence_id, sequence_create)
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        raise
    finally:
        db.close()