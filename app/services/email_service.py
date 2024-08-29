from app.core.config import settings, TIMEZONE
import sib_api_v3_sdk
from app.schemas.sequence import EmailContent
from fastapi import BackgroundTasks
from app.db.database import SessionLocal
from app.models.email import Email
from datetime import datetime, timedelta
import logging
from sib_api_v3_sdk.rest import ApiException
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import func
from datetime import date
import pytz
from app.models.sequence import Sequence
from sqlalchemy.orm import Session
from app.core.exceptions import AppException

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
    
    current_time = datetime.now(TIMEZONE)
    max_schedule_time = current_time + timedelta(days=3)
    scheduled_at = min(max(email_content.scheduled_for, current_time + timedelta(minutes=5)), max_schedule_time)
    scheduled_at_str = scheduled_at.isoformat()  # It's already in UTC, so we don't need to convert
    
    try:
        api_response = api_instance.send_transac_email({
            "templateId": settings.BREVO_EMAIL_TEMPLATE_ID,
            "to": to,
            "params": params,
            "scheduledAt": scheduled_at_str
        })
        logger.info(f"Email scheduled with Brevo for {scheduled_at_str}. Message ID: {api_response.message_id}")
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
                email.sent_to_brevo_at = datetime.now(TIMEZONE)
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

def send_email_background(db: Session, recipient_email: str, email: EmailContent, inputs: dict):
    try:
        message_id = send_email_to_brevo(recipient_email, email, inputs)
        # Here you might want to update the database to mark the email as sent
        # For example:
        # db.query(Email).filter(Email.id == email.id).update({"sent": True, "message_id": message_id})
        # db.commit()
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        # Here you might want to handle the error, maybe retry later or mark as failed in the database

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

def check_and_schedule_emails():
    db = SessionLocal()
    try:
        current_date = datetime.now(TIMEZONE)
        next_3_days = current_date + timedelta(days=3)
        
        sequences = db.query(Sequence).filter(
            Sequence.is_active == True,
            Sequence.next_email_date <= next_3_days
        ).all()
        
        for sequence in sequences:
            emails_to_schedule = [email for email in sequence.emails if not email.sent_to_brevo and email.scheduled_for <= next_3_days]
            
            for email in emails_to_schedule:
                try:
                    if not email.sent_to_brevo:
                        api_response = send_email(sequence.recipient_email, email, sequence.inputs)
                        email.sent_to_brevo = True
                        email.sent_to_brevo_at = current_date
                        email.brevo_message_id = api_response.message_id
                        db.commit()
                        logger.info(f"Scheduled email {email.id} for sequence {sequence.id}")
                    else:
                        logger.warning(f"Email {email.id} for sequence {sequence.id} already sent to Brevo")
                except Exception as e:
                    logger.error(f"Error scheduling email {email.id} for sequence {sequence.id}: {str(e)}")
                    db.rollback()
            
            sequence.next_email_date = min((email.scheduled_for for email in sequence.emails if not email.sent_to_brevo), default=None)
            db.commit()
        
        logger.info("Finished checking and scheduling emails")
    except Exception as e:
        logger.error(f"Error in check_and_schedule_emails: {str(e)}")
    finally:
        db.close()