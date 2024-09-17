import asyncio
from datetime import datetime, timedelta
from app.models.email import EmailBase
from zoneinfo import ZoneInfo
from loguru import logger
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.database import SessionLocal
from app.schemas.sequence import SequenceCreate
from app.services import sequence_service, openai_service
import re
import sentry_sdk
from typing import Dict

async def generate_and_store_email_sequence(sequence_id: int, sequence: SequenceCreate):
    logger.info(f"Starting email sequence generation for sequence_id: {sequence_id}")
    db = SessionLocal()
    previous_topics = {}
    try:
        logger.info(f"Fetching sequence {sequence_id} from database")
        db_sequence = sequence_service.get_sequence(db, sequence_id)
        if not db_sequence:
            logger.error(f"Sequence {sequence_id} not found in database")
            raise AppException(f"Sequence {sequence_id} not found", status_code=404)
        
        logger.info(f"Sequence {sequence_id} found. Calculating batches.")
        total_batches = (sequence.total_emails + settings.BATCH_SIZE - 1) // settings.BATCH_SIZE
        start_batch = db_sequence.progress * total_batches // 100
        
        logger.info(f"Total batches: {total_batches}, Starting from batch: {start_batch}")
        
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
                batch_emails = await asyncio.wait_for(
                    openai_service.generate_email_sequence(
                        sequence.topic,
                        sequence.inputs,
                        sequence.email_structure,
                        batch,
                        min(settings.BATCH_SIZE, sequence.total_emails - batch),
                        sequence.days_between_emails,
                        previous_topics=previous_topics,
                        topic_depth=sequence.topic_depth,
                        start_date=start_date  # Pass the start_date to the generate_email_sequence function
                    ),
                    timeout=settings.OPENAI_REQUEST_TIMEOUT
                )
                
                # Update topics from generated emails
                for email in batch_emails:
                    previous_topics[email.subject] = previous_topics.get(email.subject, 0) + 1

                logger.info(f"Saved batch {batch_number} to database for sequence_id: {sequence_id}")
                sequence_service.add_emails_to_sequence(db, sequence_id, batch_emails)

                progress = min(100, int((batch_number / total_batches) * 100))
                sequence_service.update_sequence_progress(db, sequence_id, progress)

                db.commit()

                # Update start_date for the next batch
                start_date += timedelta(days=len(batch_emails) * sequence.days_between_emails)

            except asyncio.TimeoutError as e:
                sentry_sdk.capture_exception(e)
                logger.error(f"Timeout occurred while generating batch {batch_number} for sequence_id: {sequence_id}")
                sequence_service.update_sequence_progress(db, sequence_id, progress)
                db.commit()
                raise AppException("Timeout occurred while generating email sequence", status_code=504)
            except AppException as e:
                sentry_sdk.capture_exception(e)
                logger.error(f"AppException generating batch {batch_number} for sequence_id: {sequence_id}: {str(e)}")
                sequence_service.mark_sequence_failed(db, sequence_id, str(e))
                db.commit()
                raise
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.error(f"Unexpected error generating batch {batch_number} for sequence_id: {sequence_id}: {str(e)}")
                sequence_service.mark_sequence_failed(db, sequence_id, str(e))
                db.commit()
                raise AppException(f"Unexpected error: {str(e)}", status_code=500)

        # Check if we've generated the correct number of emails
        actual_email_count = sequence_service.get_email_count(db, sequence_id)
        if actual_email_count < sequence.total_emails:
            logger.warning(f"Only {actual_email_count} emails generated for sequence {sequence_id}. Expected {sequence.total_emails}.")
            remaining_emails = sequence.total_emails - actual_email_count
            
            try:
                additional_emails = await asyncio.wait_for(
                    openai_service.generate_email_sequence(
                        sequence.topic,
                        sequence.inputs,
                        sequence.email_structure,
                        actual_email_count,
                        remaining_emails,
                        sequence.days_between_emails,
                        previous_topics=previous_topics,
                        topic_depth=sequence.topic_depth,
                        start_date=start_date
                    ),
                    timeout=settings.OPENAI_REQUEST_TIMEOUT
                )
                
                sequence_service.add_emails_to_sequence(db, sequence_id, additional_emails)
                logger.info(f"Generated and added {len(additional_emails)} additional emails for sequence {sequence_id}")
                
                db.commit()
            except Exception as e:
                logger.error(f"Failed to generate additional emails for sequence {sequence_id}: {str(e)}")
                raise AppException(f"Failed to generate all requested emails: {str(e)}", status_code=500)

        logger.info(f"Email generation complete for sequence_id: {sequence_id}. Finalizing sequence.")
        sequence_service.finalize_sequence(db, sequence_id)
        logger.info(f"Sequence finalized for sequence_id: {sequence_id}")
        db.commit()
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating email sequence for sequence_id: {sequence_id}: {str(e)}")
        logger.exception("Full traceback:")
        sequence_service.mark_sequence_failed(db, sequence_id, str(e))
        db.commit()
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)
    finally:
        logger.info(f"Closing database connection for sequence_id: {sequence_id}")
        db.close()

def format_email_for_blog_post(email: EmailBase) -> Dict[str, str]:
    blog_post_content = {}
    
    for section_name, section_content in email.content.items():
        # Remove any personal information or placeholders
        content = re.sub(r'\[NAME\]', 'Reader', section_content)
        content = re.sub(r'\[EMAIL\]', 'your email', content)
        blog_post_content[section_name] = content.strip()
    
    return blog_post_content