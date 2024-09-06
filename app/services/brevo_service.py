from loguru import logger
from app.core.config import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import aiohttp

async def subscribe_to_brevo_list(email: str, list_id: int):
    url = f"{settings.BREVO_API_URL}/contacts/lists/{list_id}/contacts/add"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.BREVO_API_KEY
    }
    payload = {"emails": [email]}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 201:
                    logger.info(f"Contact {email} successfully subscribed to Brevo list {list_id}")
                    return await response.json()
                elif response.status == 204:
                    logger.info(f"Contact {email} already exists in Brevo list {list_id}")
                    return None
                else:
                    error_message = await response.text()
                    logger.error(f"Failed to subscribe email to Brevo: {error_message}")
                    raise Exception(f"Failed to subscribe email: {error_message}")
        except aiohttp.ClientError as e:
            logger.error(f"Error subscribing email to Brevo: {str(e)}")
            raise

# Keep the existing SDK-based function for other parts of the application that might use it
def subscribe_to_brevo_list_sdk(email: str, list_id: int):
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