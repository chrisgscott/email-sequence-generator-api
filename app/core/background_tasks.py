from asyncio import Queue
from pydantic import BaseModel
from app.db.database import SessionLocal
from app.models.sequence import Sequence
from app.schemas.sequence import SequenceCreate, EmailSection
from app.services import sequence_service, api_key_service, blog_post_service
from app.services.sequence_generation import generate_and_store_email_sequence, format_email_for_blog_post
from app.services.brevo_service import subscribe_to_brevo_list
from loguru import logger
from typing import List
from datetime import time
import sentry_sdk

from app.services import sequence_generation

class SubmissionQueue(BaseModel):
    form_id: str
    topic: str
    recipient_email: str
    brevo_list_id: int
    brevo_template_id: int  # Add this line
    total_emails: int
    days_between_emails: int
    email_structure: List[EmailSection]
    inputs: dict
    topic_depth: int
    preferred_time: time
    timezone: str
    api_key: str  # Add this line
    custom_post_type: str

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
    logger.info(f"Starting process_submission for email: {submission.recipient_email}")
    db = SessionLocal()
    try:
        sequence_create = SequenceCreate(
            form_id=submission.form_id,
            topic=submission.topic,
            recipient_email=submission.recipient_email,
            brevo_list_id=submission.brevo_list_id,
            brevo_template_id=submission.brevo_template_id,
            total_emails=submission.total_emails,
            days_between_emails=submission.days_between_emails,
            email_structure=submission.email_structure,
            inputs=submission.inputs,
            topic_depth=submission.topic_depth,
            preferred_time=submission.preferred_time,
            timezone=submission.timezone,
            custom_post_type=submission.custom_post_type
        )
        logger.info(f"Creating sequence for email: {submission.recipient_email}")
        db_sequence = sequence_service.create_sequence(db, sequence_create)
        sequence_id = db_sequence.id
        logger.info(f"Sequence created with ID: {sequence_id}")

        # Subscribe the email to the Brevo list
        logger.info(f"Attempting to subscribe {submission.recipient_email} to Brevo list {submission.brevo_list_id}")
        try:
            await subscribe_to_brevo_list(submission.recipient_email, submission.brevo_list_id)
            logger.info(f"Successfully subscribed {submission.recipient_email} to Brevo list {submission.brevo_list_id}")
        except Exception as e:
            logger.error(f"Failed to subscribe {submission.recipient_email} to Brevo list {submission.brevo_list_id}: {str(e)}")
            # Continue with email generation even if Brevo subscription fails

        logger.info(f"Starting email generation for sequence ID: {sequence_id}")
        await generate_and_store_email_sequence(sequence_id, sequence_create)
        logger.info(f"Completed email generation for sequence ID: {sequence_id}")

        # Get the API key object once
        api_key_obj = api_key_service.get_api_key(db, submission.api_key)
        if not api_key_obj:
            raise ValueError(f"Invalid API key: {submission.api_key}")

        # Set up custom post type and fields
        try:
            blog_post_service.setup_custom_post_type_and_fields(api_key_obj, submission.custom_post_type, submission.email_structure)
            logger.info(f"Custom post type '{submission.custom_post_type}' is ready for use")
        except AppException as e:
            logger.error(f"Failed to set up custom post type: {str(e)}")
            # Here you might want to send a notification to the user or admin
            # For now, we'll continue processing but skip blog post creation
            return

        # Generate and post blog posts for each email in the sequence
        emails = sequence_service.get_emails_for_sequence(db, db_sequence.id)
        for email in emails:
            blog_post_content = sequence_generation.format_email_for_blog_post(email)
            blog_post_metadata = {
                "title": f"{email.subject}",
                "category": email.category,
                "tags": email.tags,
                "custom_post_type": submission.custom_post_type
            }
            try:
                blog_post_result = blog_post_service.create_blog_post(blog_post_content, blog_post_metadata, api_key_obj)
                logger.info(f"Blog post created for email {email.id}: {blog_post_result}")
            except Exception as e:
                logger.error(f"Failed to create blog post for email {email.id}: {str(e)}")
                # Consider adding a retry mechanism or alternative action here

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error processing submission for email {submission.recipient_email}: {str(e)}")
        raise
    finally:
        logger.info(f"Closing database connection for email: {submission.recipient_email}")
        db.close()