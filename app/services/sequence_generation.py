import asyncio
from datetime import timedelta
from loguru import logger
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.database import SessionLocal
from app.schemas.sequence import SequenceCreate
from app.services import sequence_service, openai_service

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate):
    logger.info(f"Starting email sequence generation for sequence_id: {sequence_id}")
    db = SessionLocal()
    previous_topics = []
    try:
        db_sequence = sequence_service.get_sequence(db, sequence_id)
        if not db_sequence:
            raise AppException(f"Sequence {sequence_id} not found", status_code=404)

        total_batches = (sequence.total_emails + settings.BATCH_SIZE - 1) // settings.BATCH_SIZE
        start_batch = db_sequence.progress * total_batches // 100

        for batch in range(start_batch * settings.BATCH_SIZE, sequence.total_emails, settings.BATCH_SIZE):
            batch_number = batch // settings.BATCH_SIZE + 1
            logger.info(f"Generating batch {batch_number} of {total_batches} for sequence_id: {sequence_id}")
            try:
                batch_emails = await asyncio.wait_for(
                    openai_service.generate_email_sequence(
                        sequence.topic,
                        sequence.inputs,
                        sequence.email_structure,
                        batch,
                        min(settings.BATCH_SIZE, sequence.total_emails - batch),
                        sequence.days_between_emails,
                        previous_topics=previous_topics
                    ),
                    timeout=settings.OPENAI_REQUEST_TIMEOUT
                )
                
                # Extract topics from generated emails
                new_topics = [email.subject for email in batch_emails]
                previous_topics.extend(new_topics)

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
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating email sequence for sequence_id: {sequence_id}: {str(e)}")
        sequence_service.mark_sequence_failed(db, sequence_id, str(e))
        db.commit()
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)
    finally:
        db.close()