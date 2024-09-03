import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from loguru import logger
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.database import SessionLocal
from app.schemas.sequence import SequenceCreate
from app.services import sequence_service, openai_service

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate):
    logger.info(f"Starting email sequence generation for sequence_id: {sequence_id}")
    db = SessionLocal()
    previous_topics = {}
    try:
        db_sequence = sequence_service.get_sequence(db, sequence_id)
        if not db_sequence:
            raise AppException(f"Sequence {sequence_id} not found", status_code=404)

        total_batches = (sequence.total_emails + settings.BATCH_SIZE - 1) // settings.BATCH_SIZE
        start_batch = db_sequence.progress * total_batches // 100

        # Calculate the start date based on preferred time and timezone
        subscriber_timezone = ZoneInfo(sequence.timezone)
        start_date = datetime.now(subscriber_timezone).replace(
            hour=sequence.preferred_time.hour,
            minute=sequence.preferred_time.minute,
            second=0,
            microsecond=0
        )
        if start_date <= datetime.now(subscriber_timezone):
            start_date += timedelta(days=1)

        logger.info(f"Sequence start date: {start_date}")

        for batch in range(start_batch * settings.BATCH_SIZE, sequence.total_emails, settings.BATCH_SIZE):
            batch_number = batch // settings.BATCH_SIZE + 1
            logger.info(f"Generating batch {batch_number} of {total_batches} for sequence_id: {sequence_id}")
            try:
                emails = await openai_service.generate_email_sequence(
                    sequence.topic,
                    sequence.inputs,
                    sequence.email_structure,
                    batch,
                    min(settings.BATCH_SIZE, sequence.total_emails - batch),
                    sequence.days_between_emails,
                    previous_topics=previous_topics,
                    topic_depth=sequence.topic_depth,
                    start_date=start_date
                )
                
                # Update topics from generated emails
                for email in emails:
                    previous_topics[email.subject] = previous_topics.get(email.subject, 0) + 1

                sequence_service.add_emails_to_sequence(db, sequence_id, emails)
                logger.info(f"Saved batch {batch_number} to database for sequence_id: {sequence_id}")
                
                progress = min(100, int((batch_number / total_batches) * 100))
                sequence_service.update_sequence_progress(db, sequence_id, progress)
                
                db.commit()

                # Update start_date for the next batch
                start_date += timedelta(days=len(emails) * sequence.days_between_emails)

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