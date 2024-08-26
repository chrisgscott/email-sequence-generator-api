from sqlalchemy.orm import Session
from app.models.sequence import Sequence
from app.models.email import Email
from app.schemas.sequence import SequenceCreate, EmailContent

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