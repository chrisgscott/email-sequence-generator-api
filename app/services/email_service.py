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
from sqlalchemy import func
from datetime import date
import pytz

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
        current_date = date.today()
        logger.info(f"Checking for emails scheduled for {current_date}")
        
        emails_to_send = db.query(Email).filter(
            func.date(Email.scheduled_for) == current_date,
            Email.sent == False
        ).all()
        
        logger.info(f"Found {len(emails_to_send)} emails to send")
        
        for email in emails_to_send:
            try:
                # Check if the email has already been sent
                if email.sent:
                    logger.warning(f"Email {email.id} is marked as sent but was returned in the query")
                    continue
                
                send_email(email.sequence.recipient_email, email, email.sequence.inputs)
                
                # Update the email status immediately
                email.sent = True
                email.sent_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Scheduled email {email.id} sent successfully")
            except Exception as e:
                logger.error(f"Error sending email {email.id}: {str(e)}")
                db.rollback()
    finally:
        db.close()

def send_email_background(background_tasks: BackgroundTasks, to_email: str, email_content: EmailContent, params: dict):
    background_tasks.add_task(send_email, to_email, email_content, params)

def send_email_to_brevo(to_email: str, email_content: EmailContent, inputs: dict):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    subject = email_content.subject
    sender = {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM}
    to = [{"email": to_email}]
    params = {
        "subject": subject,
        **email_content.content,
        **inputs
    }
    
    scheduled_at = int(email_content.scheduled_for.replace(tzinfo=pytz.UTC).timestamp())
    
    try:
        api_response = api_instance.send_transac_email({
            "templateId": settings.BREVO_EMAIL_TEMPLATE_ID,
            "to": to,
            "params": params,
            "scheduledAt": scheduled_at
        })
        logger.info(f"Email scheduled with Brevo for {email_content.scheduled_for}. Message ID: {api_response.message_id}")
        return api_response.message_id
    except ApiException as e:
        logger.error(f"Exception when calling SMTPApi->send_transac_email: {e}")
        raise