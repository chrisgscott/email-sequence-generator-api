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
def send_email(to_email: str, email_content: EmailContent, inputs: dict):
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
        return api_response
    except ApiException as e:
        logger.error(f"Exception when calling SMTPApi->send_transac_email: {e}")
        raise

def check_and_send_scheduled_emails():
    db = SessionLocal()
    try:
        current_date = date.today()
        logger.info(f"Checking for emails scheduled for {current_date}")
        
        emails_to_send = db.query(Email).filter(
            func.date(Email.scheduled_for) == current_date,
            Email.sent_to_brevo == False
        ).all()
        
        logger.info(f"Found {len(emails_to_send)} emails to send")
        
        for email in emails_to_send:
            try:
                if email.sent_to_brevo:
                    logger.warning(f"Email {email.id} is marked as sent to Brevo but was returned in the query")
                    continue
                
                api_response = send_email(email.sequence.recipient_email, email, email.sequence.inputs)
                
                email.sent_to_brevo = True
                email.sent_to_brevo_at = datetime.now(timezone.utc)
                email.brevo_message_id = api_response.message_id
                db.commit()
                logger.info(f"Scheduled email {email.id} sent successfully")
            except Exception as e:
                logger.error(f"Error sending email {email.id}: {str(e)}")
                db.rollback()
    except Exception as e:
        logger.error(f"Error in check_and_send_scheduled_emails: {str(e)}")
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