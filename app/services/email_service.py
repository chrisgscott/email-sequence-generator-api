from app.models.sequence import Sequence
from app.core.config import settings
import sib_api_v3_sdk
from app.schemas.sequence import EmailContent

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY

def schedule_emails(sequence: Sequence):
    # This function now just ensures the emails are in the database
    # The actual sending will be handled by the Celery task
    pass

def send_email(to_email: str, email_content: EmailContent, params: dict):
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    params_to_send = {
        "subject": email_content.subject,
        **email_content.content,
        **params
    }
    print("Params being sent to Brevo:", params_to_send)

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        template_id=settings.BREVO_EMAIL_TEMPLATE_ID,
        params=params_to_send,
        sender={"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM}
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"Email sent successfully. Message ID: {api_response.message_id}")
        return api_response
    except sib_api_v3_sdk.ApiException as e:
        print(f"Exception when calling SMTPApi->send_transac_email: {e}")
        raise