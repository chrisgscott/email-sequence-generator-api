from app.models.sequence import Sequence
from app.core.config import settings
import sib_api_v3_sdk
from app.schemas.sequence import EmailContent

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY

def schedule_emails(sequence: Sequence):
    # In a real-world scenario, you would use a task queue like Celery to schedule emails
    # For this example, we'll just print out the scheduled emails
    for email in sequence.emails:
        print(f"Scheduled email: {email.subject} for {email.scheduled_for}")

def send_email(to_email: str, email_content: EmailContent, params: dict):
    # Create an instance of the API class
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # Create a SendSmtpEmail model
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        template_id=settings.BREVO_EMAIL_TEMPLATE_ID,
        params={
            "subject": email_content.subject,
            **email_content.content,
            **params  # Include all other parameters for placeholders
        },
        sender={"name": "Your Name", "email": settings.EMAIL_FROM},
        schedule_at=email_content.scheduled_for.isoformat()
    )

def send_sequence_emails(sequence: Sequence):
    for email in sequence.emails:
        params = {
            **sequence.inputs,
            "topic": sequence.topic,
        }
        send_email(
            to_email=sequence.recipient_email,
            email_content=email,
            params=params
        )