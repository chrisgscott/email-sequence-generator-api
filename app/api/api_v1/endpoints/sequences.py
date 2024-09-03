from typing import Dict, Any, List
from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException, Header
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.schemas.sequence import SequenceCreate, SequenceResponse, EmailSection
from app.services import sequence_service, brevo_service, api_key_service
from app.core.exceptions import AppException
from app.models.sequence import Sequence
from loguru import logger
import json
from app.services import sequence_generation
from datetime import datetime
from app.core.auth import get_current_active_user
from app.schemas.user import User

router = APIRouter()

@router.post("/webhook")
async def webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    api_key: str = Header(..., alias="X-API-Key")
):
    try:
        with get_db() as db:
            # Use the db session directly for API key validation
            if not api_key_service.validate_api_key(db, api_key):
                raise HTTPException(status_code=401, detail="Invalid API key")
        
            data = await request.json()
            logger.info(f"Received webhook data: {data}")
        
            # Extract and validate required fields
            form_id = data.get("form_id")
            topic = data.get("topic")
            recipient_email = data.get("recipient_email")
            brevo_list_id = data.get("brevo_list_id")
            sequence_settings = data.get("sequence_settings", {})
            email_structure = data.get("email_structure", [])
            inputs = data.get("inputs", {})
            preferred_time = data.get("preferred_time", "07:30:00")
            timezone = data.get("timezone", "UTC")

            logger.info(f"Parsed JSON data: {data}")
        
            # Validate required fields
            required_fields = ["form_id", "topic", "recipient_email", "brevo_list_id", "sequence_settings", "email_structure", "inputs"]
            if not all(field in data for field in required_fields):
                raise AppException("Missing required fields in webhook data", status_code=400)
        
            if "total_emails" not in sequence_settings or "days_between_emails" not in sequence_settings:
                raise AppException("Missing required fields in sequence_settings", status_code=400)
        
            # Validate email_structure
            if not isinstance(email_structure, list) or not all(isinstance(section, dict) and "name" in section and "word_count" in section for section in email_structure):
                raise AppException("Invalid email_structure format", status_code=400)
        
            # Create EmailSection objects
            email_structure = [
                EmailSection(
                    name=section['name'],
                    word_count=str(section['word_count']),  # Ensure word_count is a string
                    description=section.get('description', f"Content for {section['name']}")
                )
                for section in data['email_structure']
            ]
        
            topic_depth = data.get("topic_depth", 5)
        
            try:
                preferred_time_obj = datetime.strptime(preferred_time, "%H:%M:%S").time()
            except ValueError:
                preferred_time_obj = datetime.strptime(preferred_time, "%H:%M").time()

            sequence_create = SequenceCreate(
                form_id=form_id,
                topic=topic,
                recipient_email=recipient_email,
                brevo_list_id=brevo_list_id,
                total_emails=sequence_settings['total_emails'],
                days_between_emails=sequence_settings['days_between_emails'],
                email_structure=email_structure,
                inputs=inputs,
                topic_depth=topic_depth,
                preferred_time=preferred_time_obj,
                timezone=timezone
            )
        
            db_sequence = sequence_service.create_sequence(db, sequence_create)
        
            # Schedule email generation
            background_tasks.add_task(
                generate_and_store_email_sequence,
                db_sequence.id,
                sequence_create
            )

            return {"message": "Sequence creation initiated", "sequence_id": db_sequence.id}
    
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise AppException("An unexpected error occurred", status_code=500)