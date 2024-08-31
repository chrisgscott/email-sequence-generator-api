from loguru import logger
from app.core.config import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def subscribe_to_brevo_list(email: str, list_id: int):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))
    create_contact = sib_api_v3_sdk.CreateContact(email=email, list_ids=[list_id])

    try:
        api_response = api_instance.create_contact(create_contact)
        logger.info(f"Contact {email} successfully subscribed to Brevo list {list_id}")
        return api_response
    except ApiException as e:
        if e.status == 400 and "Contact already exist" in str(e):
            logger.info(f"Contact {email} already exists in Brevo list {list_id}")
            return None
        else:
            logger.error(f"Exception when calling ContactsApi->create_contact: {e}")
            raise