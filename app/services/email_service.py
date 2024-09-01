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
from typing import Dict

logger = logging.getLogger(__name__)

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_email(recipient_email: str, email_content: EmailContent, inputs: Dict[str, str]):
    try:
        logger.info(f"Preparing to send email to {recipient_email}")
        
        # Create an instance of the API class
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        # Prepare the email data
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient_email}],
            template_id=settings.BREVO_EMAIL_TEMPLATE_ID,
            params={
                "subject": email_content.subject,
                **email_content.content,
                **inputs
            },
            headers={
                "X-Mailin-custom": "custom_header_1:custom_value_1|custom_header_2:custom_value_2"
            }
        )
        
        logger.info(f"Sending email with subject: {email_content.subject}")
        
        # Make the API call
        api_response = api_instance.send_transac_email(send_smtp_email)
        
        logger.info(f"Email sent successfully. Message ID: {api_response.message_id}")
        return api_response

    except ApiException as e:
        logger.error(f"Exception when calling Brevo API: {e}")
        raise AppException(f"Brevo API error: {str(e)}", status_code=500)
    except TypeError as e:
        logger.error(f"TypeError when preparing or sending email: {e}")
        logger.error(f"Email content: {email_content}")
        logger.error(f"Inputs: {inputs}")
        raise AppException(f"Error preparing email data: {str(e)}", status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error when sending email: {e}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)

def check_and_send_scheduled_emails():
    db = SessionLocal()
    try:
        current_date = datetime.now(TIMEZONE)
        logger.info(f"Checking for emails scheduled up to {current_date}")
        
        emails_to_send = db.query(Email).filter(
            Email.scheduled_for <= current_date,
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
                email.sent_to_brevo_at = current_date
                email.brevo_message_id = api_response.message_id
                db.commit()
                logger.info(f"Email {email.id} sent successfully (originally scheduled for {email.scheduled_for})")
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
            emails_to_schedule = [
                email for email in sequence.emails 
                if not email.sent_to_brevo and email.scheduled_for.replace(tzinfo=TIMEZONE) <= next_3_days
            ]
            
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
                except AppException as e:
                    logger.error(f"AppException scheduling email {email.id} for sequence {sequence.id}: {str(e)}")
                    db.rollback()
                except Exception as e:
                    logger.error(f"Unexpected error scheduling email {email.id} for sequence {sequence.id}: {str(e)}")
                    db.rollback()
            
            sequence.next_email_date = min(
                (email.scheduled_for.replace(tzinfo=TIMEZONE) for email in sequence.emails if not email.sent_to_brevo),
                default=None
            )
            db.commit()
        
        logger.info("Finished checking and scheduling emails")
    except Exception as e:
        logger.error(f"Error in check_and_schedule_emails: {str(e)}")
    finally:
        db.close()