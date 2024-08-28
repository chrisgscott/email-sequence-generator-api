from app.core.config import settings
import sib_api_v3_sdk
from app.schemas.sequence import EmailContent
from fastapi import BackgroundTasks
from app.db.database import SessionLocal
from app.models.email import Email
from datetime import datetime, timezone
import logging
from sib_api_v3_sdk.rest import ApiException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_email(to_email: str, email_content: EmailContent, params: dict):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    params_to_send = {
        "subject": email_content.subject,
        **email_content.content,
        **params
    }
    logger.info(f"Params being sent to Brevo: {params_to_send}")

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        template_id=settings.BREVO_EMAIL_TEMPLATE_ID,
        params=params_to_send,
        sender={"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM}
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully to {to_email}. Message ID: {api_response.message_id}")
        return api_response
    except ApiException as e:
        logger.error(f"Exception when calling SMTPApi->send_transac_email: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when sending email: {e}")
        raise

def check_and_send_scheduled_emails():
    db = SessionLocal()
    try:
        current_time = datetime.now(timezone.utc)
        emails_to_send = db.query(Email).filter(
            Email.scheduled_for <= current_time,
            Email.sent == False
        ).all()
        
        for email in emails_to_send:
            try:
                send_email(email.sequence.recipient_email, email, email.sequence.inputs)
                email.sent = True
                email.sent_at = current_time
                db.commit()
                logger.info(f"Scheduled email {email.id} sent successfully")
            except Exception as e:
                logger.error(f"Error sending email {email.id}: {str(e)}")
                db.rollback()
    finally:
        db.close()

def send_email_background(background_tasks: BackgroundTasks, to_email: str, email_content: EmailContent, params: dict):
    background_tasks.add_task(send_email, to_email, email_content, params)