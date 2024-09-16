from sqlalchemy.orm import Session
from app.models.sequence import Sequence
from app.models.email import Email
from app.schemas.sequence import SequenceCreate, EmailContent, EmailBase, EmailSection
from typing import List, Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import AppException
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
import json
from sqlalchemy import String

def create_sequence(db: Session, sequence: SequenceCreate) -> Sequence:
    email_structure_json = [
        {
            "name": section.name,
            "word_count": section.word_count,
            "description": section.description
        }
        for section in sequence.email_structure
    ]
    db_sequence = Sequence(
        form_id=sequence.form_id,
        topic=sequence.topic,
        recipient_email=sequence.recipient_email,
        brevo_list_id=sequence.brevo_list_id,
        brevo_template_id=sequence.brevo_template_id,  # Add this line
        total_emails=sequence.total_emails,
        days_between_emails=sequence.days_between_emails,
        email_structure=email_structure_json,
        inputs=sequence.inputs,
        preferred_time=sequence.preferred_time,
        timezone=sequence.timezone
    )
    db.add(db_sequence)
    db.commit()
    db.refresh(db_sequence)
    return db_sequence

def create_empty_sequence(db: Session, sequence: SequenceCreate):
    return create_sequence(db, sequence)

def update_sequence_progress(db: Session, sequence_id: int, progress: int):
    db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
    if db_sequence:
        db_sequence.progress = progress
        db.commit()
    else:
        logger.error(f"Sequence {sequence_id} not found while updating progress")

def finalize_sequence(db: Session, sequence_id: int):
    try:
        db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
        if db_sequence:
            db_sequence.status = "completed"
            db_sequence.progress = 100
            db_sequence.next_email_date = db.query(func.min(Email.scheduled_for)).filter(Email.sequence_id == sequence_id).scalar()
            db.commit()
            logger.info(f"Sequence {sequence_id} finalized successfully")
        else:
            logger.error(f"Sequence {sequence_id} not found")
            raise AppException(f"Sequence {sequence_id} not found", status_code=404)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while finalizing sequence {sequence_id}: {str(e)}")
        raise AppException(f"Database error: {str(e)}", status_code=500)

def mark_sequence_failed(db: Session, sequence_id: int, error_message: str):
    db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
    if db_sequence:
        db_sequence.status = "failed"
        db_sequence.error_message = error_message
        db.commit()

def add_emails_to_sequence(db: Session, sequence_id: int, emails: List[EmailBase]):
    sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
    if not sequence:
        raise AppException(f"Sequence with id {sequence_id} not found", status_code=404)
    
    email_data = [
        {
            "sequence_id": sequence_id,
            "subject": email.subject,
            "content": email.content,
            "scheduled_for": email.scheduled_for
        }
        for email in emails
    ]
    
    logger.info(f"Attempting to insert {len(email_data)} emails for sequence {sequence_id}")
    
    stmt = insert(Email).values(email_data)
    stmt = stmt.on_conflict_do_nothing()  # In case of unique constraint violations
    result = db.execute(stmt)
    db.flush()
    
    logger.info(f"Inserted {result.rowcount} emails for sequence {sequence_id}")

    # Verify the insertion
    inserted_emails = db.query(Email).filter(Email.sequence_id == sequence_id).all()
    logger.info(f"Total emails in database for sequence {sequence_id}: {len(inserted_emails)}")

def get_sequence(db: Session, sequence_id: int) -> Sequence:
    return db.query(Sequence).filter(Sequence.id == sequence_id).first()

def get_existing_sequence(db: Session, form_id: str, recipient_email: str, inputs: Dict[str, Any]):
    return db.query(Sequence).filter(
        Sequence.form_id == form_id,
        Sequence.recipient_email == recipient_email,
        Sequence.inputs.cast(String) == json.dumps(inputs)
    ).first()

def get_email_count(db: Session, sequence_id: int) -> int:
    return db.query(func.count(Email.id)).filter(Email.sequence_id == sequence_id).scalar()