from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import sequence as sequence_schema
from app.services import openai_service, email_service, sequence_service

router = APIRouter()

@router.post("/", response_model=sequence_schema.Sequence)
def create_sequence(
    sequence: sequence_schema.SequenceCreate,
    db: Session = Depends(get_db)
):
    try:
        # Generate email sequence using OpenAI
        emails = openai_service.generate_email_sequence(sequence.topic, sequence.inputs)
        
        # Create new sequence in database
        db_sequence = sequence_service.create_sequence(db, sequence, emails)
        
        # Schedule emails
        email_service.schedule_emails(db_sequence)
        
        return db_sequence
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))