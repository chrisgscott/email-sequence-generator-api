from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.schemas.sequence import SequenceCreate, SequenceResponse, EmailSection
from app.services import sequence_service, openai_service, brevo_service
from app.core.exceptions import AppException
from app.models.sequence import Sequence
from loguru import logger
import json
from typing import List
from app.services import sequence_generation

router = APIRouter()

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    logger.info("Webhook endpoint hit")
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
        
        # Parse the JSON data
        form_id = data.get("form_id")
        topic = data.get("topic")
        recipient_email = data.get("recipient_email")
        brevo_list_id = data.get("brevo_list_id")
        sequence_settings = data.get("sequence_settings", {})
        email_structure = data.get("email_structure", [])
        inputs = data.get("inputs", {})
        
        logger.info(f"Parsed JSON data: {data}")
        
        # Validate required fields
        required_fields = ["form_id", "topic", "recipient_email", "brevo_list_id", "sequence_settings", "email_structure", "inputs"]
        if not all(field in data for field in required_fields):
            raise AppException("Missing required fields in webhook data", status_code=400)
        
        # Validate sequence_settings
        if "total_emails" not in sequence_settings or "days_between_emails" not in sequence_settings:
            raise AppException("Missing required fields in sequence_settings", status_code=400)
        
        # Validate email_structure
        if not isinstance(email_structure, list) or not all(isinstance(section, dict) and "name" in section and "word_count" in section for section in email_structure):
            raise AppException("Invalid email_structure format", status_code=400)
        
        # Create SequenceCreate object
        sequence_create = SequenceCreate(
            form_id=form_id,
            topic=topic,
            recipient_email=recipient_email,
            brevo_list_id=brevo_list_id,
            total_emails=sequence_settings['total_emails'],
            days_between_emails=sequence_settings['days_between_emails'],
            email_structure=[EmailSection(**section) for section in email_structure],
            inputs=inputs
        )
        
        # Check for existing sequence
        db = SessionLocal()
        try:
            existing_sequence = sequence_service.get_existing_sequence(db, form_id, recipient_email, inputs)
            if existing_sequence:
                logger.info(f"Existing sequence found with id: {existing_sequence.id}")
                return {"message": "Sequence already exists", "sequence_id": existing_sequence.id}
            
            # Create a new sequence
            db_sequence = sequence_service.create_sequence(db, sequence_create)
            sequence_id = db_sequence.id
            logger.info(f"New sequence created with id: {sequence_id}")
        except Exception as e:
            logger.error(f"Error checking for existing sequence or creating new sequence: {str(e)}")
            raise AppException(f"Error processing sequence: {str(e)}", status_code=500)
        finally:
            db.close()
        
        # Queue the sequence generation
        background_tasks.add_task(sequence_generation.generate_and_store_email_sequence, sequence_id, sequence_create)
        
        # Subscribe to Brevo list
        background_tasks.add_task(brevo_service.subscribe_to_brevo_list, recipient_email, brevo_list_id)
        
        logger.info("Webhook processed successfully")
        return {"message": "Sequence creation queued successfully", "sequence_id": sequence_id}
    except AppException as e:
        logger.error(f"AppException in webhook: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}", exc_info=True)
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)

# Add other routes here if needed