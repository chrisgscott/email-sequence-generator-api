from sqlalchemy.orm import Session
from app.models.webhook_submission import WebhookSubmission

def create_webhook_submission(db: Session, payload: dict) -> WebhookSubmission:
    db_submission = WebhookSubmission(
        form_id=payload.get("form_id"),
        topic=payload.get("topic"),
        recipient_email=payload.get("recipient_email"),
        brevo_list_id=payload.get("brevo_list_id"),
        brevo_template_id=payload.get("brevo_template_id"),
        sequence_settings=payload.get("sequence_settings"),
        email_structure=payload.get("email_structure"),
        inputs=payload.get("inputs"),
        topic_depth=payload.get("topic_depth"),
        preferred_time=payload.get("preferred_time"),
        timezone=payload.get("timezone"),
        raw_payload=payload
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission