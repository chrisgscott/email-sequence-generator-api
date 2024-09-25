from app.core.config import settings, TIMEZONE
import sib_api_v3_sdk
from app.schemas.sequence import EmailContent
from fastapi import BackgroundTasks
from app.db.database import SessionLocal, get_db
from app.models.email import Email
from datetime import datetime, timedelta, date
import logging
from sib_api_v3_sdk.rest import ApiException
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import func
from zoneinfo import ZoneInfo
import pytz
from app.models.sequence import Sequence
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from typing import Dict
from filelock import FileLock, Timeout
import sentry_sdk
import time
import psutil
import markdown

logger = logging.getLogger(__name__)

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY

def send_email(recipient_email: str, email: Email, sequence: Sequence):
    try:
        logger.info(f"Preparing to send email to {recipient_email}")
        logger.info(f"Email content: {email.content}")
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        subscriber_timezone = ZoneInfo(sequence.timezone)
        
        local_scheduled_time = email.scheduled_for.replace(tzinfo=ZoneInfo('UTC')).astimezone(subscriber_timezone)
        
        current_time = datetime.now(subscriber_timezone)
        if local_scheduled_time <= current_time:
            local_scheduled_time = current_time + timedelta(minutes=5)
        
        utc_offset = local_scheduled_time.strftime('%z')
        scheduled_at = local_scheduled_time.strftime(f'%Y-%m-%dT%H:%M:%S{utc_offset[:3]}:{utc_offset[3:]}')

        subject = email.subject if email.subject else "No Subject"
        logger.info(f"Retrieved subject: {subject}")

        # Convert Markdown to HTML
        html_content = {key: markdown.markdown(value) for key, value in email.content.items()}

        params = {
            "subject": subject,
            "image_url": email.image_url,
            "photographer": email.photographer,
            "pexels_url": email.pexels_url,
            **html_content,  # Use the HTML content instead of Markdown
            **{f"input_{key}": value for key, value in sequence.inputs.items()}
        }
        logger.info(f"Params being sent to Brevo: {params}")

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient_email}],
            template_id=sequence.brevo_template_id,
            params=params,
            headers={
                "X-Mailin-custom": "custom_header_1:custom_value_1|custom_header_2:custom_value_2"
            },
            scheduled_at=scheduled_at
        )
        
        logger.info(f"Sending email with subject: {subject}")
        logger.info(f"Making API call to Brevo with the following details:")
        logger.info(f"To: {send_smtp_email.to}")
        logger.info(f"Template ID: {sequence.brevo_template_id}")
        logger.info(f"Params: {send_smtp_email.params}")
        
        api_response = api_instance.send_transac_email(send_smtp_email)
        
        logger.info(f"Email sent successfully. Message ID: {api_response.message_id}")
        return api_response

    except ApiException as e:
        logger.error(f"Exception when calling Brevo API: {e}")
        raise AppException(f"Brevo API error: {str(e)}", status_code=500)
    except TypeError as e:
        logger.error(f"TypeError when preparing or sending email: {e}")
        logger.error(f"Email content: {email.content}")
        logger.error(f"Inputs: {sequence.inputs}")
        raise AppException(f"Error preparing email data: {str(e)}", status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error when sending email: {e}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)

def log_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

def check_and_send_scheduled_emails():
    db = next(get_db())
    try:
        with db.begin():  # Start a transaction
            log_memory_usage()
            current_date = datetime.now(TIMEZONE)
            logger.info(f"Checking for emails scheduled up to {current_date}")
            
            emails_to_send = db.query(Email).filter(
                Email.scheduled_for <= current_date,
                Email.sent_to_brevo == False
            ).with_for_update().limit(100).all()  # Lock the rows for update
            
            logger.info(f"Found {len(emails_to_send)} emails to send")
            
            for email in emails_to_send:
                try:
                    if email.sent_to_brevo:
                        logger.warning(f"Email {email.id} is marked as sent to Brevo but was returned in the query")
                        continue
                    
                    logger.info(f"Attempting to send email {email.id} scheduled for {email.scheduled_for}")
                    api_response = send_email(email.sequence.recipient_email, email, email.sequence)
                    
                    email.sent_to_brevo = True
                    email.sent_to_brevo_at = current_date
                    email.brevo_message_id = api_response.message_id
                    logger.info(f"Email {email.id} sent successfully (originally scheduled for {email.scheduled_for})")
                except Exception as e:
                    logger.error(f"Error sending email {email.id}: {str(e)}")
                    # Don't raise the exception, continue with the next email
            
            db.commit()  # Commit the transaction
            log_memory_usage()
    except Exception as e:
        logger.error(f"Error in check_and_send_scheduled_emails: {str(e)}")
        db.rollback()
    finally:
        db.close()

def send_email_background(db: Session, recipient_email: str, email: EmailContent, inputs: dict):
    try:
        message_id = send_email_to_brevo(db, recipient_email, email, inputs)
        # Here you might want to update the database to mark the email as sent
        # For example:
        # db.query(Email).filter(Email.id == email.id).update({"sent": True, "message_id": message_id})
        # db.commit()
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        # Here you might want to handle the error, maybe retry later or mark as failed in the database

def send_email_to_brevo(db: Session, to_email: str, email_content: EmailContent, inputs: dict, template_id: int):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    subject = email_content.subject
    sender = {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM}
    to = [{"email": to_email}]
    
    # Combine all content sections into a single Markdown string
    markdown_content = "\n\n".join([f"## {section}\n\n{content}" for section, content in email_content.content.items()])
    
    params = {
        "subject": subject,
        "content": markdown_content,
        **inputs
    }
    
    scheduled_at = email_content.scheduled_for.replace(tzinfo=pytz.UTC).isoformat()
    
    # Log the API call details
    logger.info(f"Making API call to Brevo with the following details:")
    logger.info(f"To: {to}")
    logger.info(f"Params: {params}")
    logger.info(f"Scheduled At: {scheduled_at}")
    logger.info(f"Template ID: {template_id}")

    try:
        api_response = api_instance.send_transac_email({
            "templateId": template_id,
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
            if should_send_email(sequence):
                emails_to_schedule = [
                    email for email in sequence.emails 
                    if not email.sent_to_brevo and email.scheduled_for.replace(tzinfo=TIMEZONE) <= next_3_days
                ]
                
                for email in emails_to_schedule:
                    try:
                        if not email.sent_to_brevo:
                            api_response = send_email(sequence.recipient_email, email, sequence)
                            email.sent_to_brevo = True
                            email.sent_to_brevo_at = current_date
                            email.brevo_message_id = api_response.message_id
                            db.commit()
                            logger.info(f"Scheduled email {email.id} for sequence {sequence.id}")
                        else:
                            logger.warning(f"Email {email.id} for sequence {sequence.id} already sent to Brevo")
                    except AppException as e:
                        sentry_sdk.capture_exception(e)
                        logger.error(f"AppException scheduling email {email.id} for sequence {sequence.id}: {str(e)}")
                        db.rollback()
                    except Exception as e:
                        sentry_sdk.capture_exception(e)
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

def should_send_email(sequence: Sequence) -> bool:
    now = datetime.now(ZoneInfo(sequence.timezone))
    preferred_time = datetime.combine(now.date(), sequence.preferred_time)
    preferred_time = preferred_time.replace(tzinfo=ZoneInfo(sequence.timezone))
    
    # Allow a 15-minute window for sending
    return abs((now - preferred_time).total_seconds()) < 900  # 15 minutes in seconds

def get_utc_offset(timezone_str: str) -> str:
    now = datetime.now(ZoneInfo(timezone_str))
    offset = now.strftime('%z')
    return f"{offset[:3]}:{offset[3:]}"  # Format as ±HH:MM