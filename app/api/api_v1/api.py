import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import EmailStr, ValidationError, BaseModel

from app.db.database import get_db
from app.schemas import sequence as sequence_schema
from app.services import openai_service, email_service, sequence_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    logger.info("Webhook endpoint hit")
    try:
        # Log the raw incoming data
        raw_data = await request.body()
        logger.info(f"Received webhook data: {raw_data.decode()}")

        # Parse the incoming JSON data
        data = await request.json()
        logger.info(f"Parsed JSON data: {data}")

        # Extract the required fields, with fallbacks
        topic = data.get("topic") or data.get("form_fields", {}).get("topic") or data.get("topic_field")
        inputs = data.get("inputs") or data.get("form_fields") or {}
        recipient_email = data.get("recipient_email") or data.get("form_fields", {}).get("email") or data.get("email_field")

        if not topic or not recipient_email:
            raise ValueError("Missing required fields: topic and recipient_email")

        # Validate email
        class EmailValidator(BaseModel):
            email: EmailStr

        try:
            EmailValidator(email=recipient_email)
        except ValidationError:
            raise ValueError(f"Invalid email address: {recipient_email}")

        # Create SequenceCreate object
        sequence = sequence_schema.SequenceCreate(
            topic=topic,
            inputs=inputs,
            recipient_email=recipient_email
        )

        # Generate email sequence using OpenAI
        emails = openai_service.generate_email_sequence(sequence.topic, sequence.inputs)

        # Create new sequence in database
        db_sequence = sequence_service.create_sequence(db, sequence, emails)

        # Schedule emails using background tasks
        for email in db_sequence.emails:
            email_service.send_email_background(background_tasks, sequence.recipient_email, email, sequence.inputs)

        logger.info("Webhook processed successfully")
        return {"message": "Webhook received and processed successfully", "sequence_id": db_sequence.id}
    except ValueError as ve:
        logger.error(f"Validation error in webhook: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/sequences", response_model=SequenceResponse)
def create_sequence(sequence: SequenceCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        emails = openai_service.generate_email_sequence(sequence.topic, sequence.inputs)
        db_sequence = sequence_service.create_sequence(db, sequence, emails)
        
        for email in db_sequence.emails:
            email_service.send_email_background(background_tasks, sequence.recipient_email, email, sequence.inputs)
        
        return db_sequence
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))