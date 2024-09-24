from typing import Dict, Any, List
from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException, Header
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.schemas.sequence import SequenceCreate, SequenceResponse, EmailSection
from app.services.sequence_generation import generate_and_store_email_sequence
from app.services import sequence_service, brevo_service, api_key_service, webhook_service
from app.core.exceptions import AppException
from app.models.sequence import Sequence
from loguru import logger
import json
from app.services import sequence_generation
from datetime import datetime
from app.core.auth import get_current_active_user
from app.schemas.user import User
from app.core.background_tasks import SubmissionQueue, process_submission
from app.services import sequence_service, blog_post_service
from app.services import webhook_service
from app.schemas.blog_post import BlogPostCreate, BlogPostResponse
from app.core.api_key import get_api_key
from app.models.api_key import APIKey

router = APIRouter()

@router.post("/webhook")
async def webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {data}")

        # Store the raw submission
        webhook_service.create_webhook_submission(db, data)
        logger.info("Webhook submission stored successfully")

        # Define required fields
        required_fields = [
            "form_id", "topic", "recipient_email", "brevo_list_id",
            "sequence_settings", "email_structure", "inputs",
            "preferred_time", "timezone"
        ]

        # Check for required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise AppException(f"Missing required fields: {', '.join(missing_fields)}", status_code=400)

        # Extract and validate sequence settings
        sequence_settings = data["sequence_settings"]
        if "total_emails" not in sequence_settings or "days_between_emails" not in sequence_settings:
            raise AppException("Missing required fields in sequence_settings", status_code=400)

        # Validate email_structure
        email_structure = data["email_structure"]
        if not isinstance(email_structure, list) or not all(isinstance(section, dict) and "name" in section and "word_count" in section for section in email_structure):
            raise AppException("Invalid email_structure format", status_code=400)

        # Create EmailSection objects
        email_sections = [
            EmailSection(
                name=section['name'],
                word_count=str(section['word_count']),
                description=section.get('description', f"Content for {section['name']}")
            )
            for section in email_structure
        ]

        # Parse preferred time
        try:
            preferred_time_obj = datetime.strptime(data["preferred_time"], "%H:%M").time()
        except ValueError:
            raise AppException("Invalid preferred_time format. Use HH:MM", status_code=400)

        # Create the SubmissionQueue object
        submission = SubmissionQueue(
            form_id=data["form_id"],
            topic=data["topic"],
            recipient_email=data["recipient_email"],
            brevo_list_id=data["brevo_list_id"],
            brevo_template_id=data.get("brevo_template_id"),
            total_emails=sequence_settings["total_emails"],
            days_between_emails=sequence_settings["days_between_emails"],
            email_structure=email_sections,
            inputs=data["inputs"],
            topic_depth=data.get("topic_depth", 5),
            preferred_time=preferred_time_obj,
            timezone=data["timezone"],
            api_key=api_key,
            custom_post_type=data.get("custom_post_type", "email_blog_post")
        )

        background_tasks.add_task(process_submission, submission)

        return {"message": "Sequence creation and email generation started"}

    except AppException as e:
        logger.error(f"AppException in webhook: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise AppException("An unexpected error occurred", status_code=500)

@router.post("/create-blog-post", response_model=BlogPostResponse)
async def create_blog_post(
    post: BlogPostCreate,
    db: Session = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    try:
        result = blog_post_service.create_blog_post(post.content, post.metadata, api_key)
        return BlogPostResponse(message=result)
    except Exception as e:
        logger.error(f"Error creating blog post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))