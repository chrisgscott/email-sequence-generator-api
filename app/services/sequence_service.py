from sqlalchemy.orm import Session
from app.models.sequence import Sequence
from app.models.email import Email
from app.schemas.sequence import SequenceCreate, EmailContent
from typing import List
from sqlalchemy.exc import SQLAlchemyError

def create_sequence(db: Session, sequence: SequenceCreate, emails: list[EmailContent]):
    db_sequence = Sequence(
        topic=sequence.topic,
        inputs=sequence.inputs,
        recipient_email=sequence.recipient_email,
    )
    
    for email_content in emails:
        db_email = Email(
            subject=email_content.subject,
            content=email_content.content,
            scheduled_for=email_content.scheduled_for
        )
        db_sequence.emails.append(db_email)
    
    db.add(db_sequence)
    db.commit()
    db.refresh(db_sequence)
    return db_sequence

def create_empty_sequence(db: Session, sequence: SequenceCreate):
    db_sequence = Sequence(
        topic=sequence.topic,
        inputs=sequence.inputs,
        recipient_email=sequence.recipient_email,
        status="generating",
        progress=0
    )
    db.add(db_sequence)
    db.commit()
    db.refresh(db_sequence)
    return db_sequence

def update_sequence_progress(db: Session, sequence_id: int, progress: int):
    db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
    if db_sequence:
        db_sequence.progress = progress
        db.commit()

def finalize_sequence(db: Session, sequence_id: int, emails: List[EmailContent]):
    try:
        db_sequence = db.query(Sequence).filter(Sequence.id == sequence_id).first()
        if db_sequence:
            for email in emails:
                db_email = Email(
                    subject=email.subject,
                    content=email.content,
                    scheduled_for=email.scheduled_for
                )
                db_sequence.emails.append(db_email)
            db_sequence.status = "completed"
            db_sequence.progress = len(emails)
            db_sequence.next_email_date = min(email.scheduled_for for email in emails)
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