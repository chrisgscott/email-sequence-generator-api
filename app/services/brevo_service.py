import aiohttp
from app.core.config import settings
from loguru import logger

async def subscribe_to_brevo_list(email: str, list_id: int):
    logger.info(f"Starting Brevo subscription process for email: {email} to list: {list_id}")
    url = "https://api.brevo.com/v3/contacts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": settings.BREVO_API_KEY
    }
    payload = {
        "email": email,
        "listIds": [list_id]
    }

    try:
        logger.info(f"Sending request to Brevo API for email: {email}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                logger.info(f"Received response from Brevo API. Status: {response.status}")
                if response.status == 201:
                    logger.info(f"Contact {email} successfully subscribed to Brevo list {list_id}")
                elif response.status == 204:
                    logger.info(f"Contact {email} was already in Brevo list {list_id}")
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to subscribe {email} to Brevo list {list_id}. Status: {response.status}, Response: {response_text}")
                    raise Exception(f"Failed to subscribe email to Brevo list. Status: {response.status}, Response: {response_text}")
    except Exception as e:
        logger.error(f"Exception occurred while subscribing to Brevo: {str(e)}")
        raise

    logger.info(f"Completed Brevo subscription process for email: {email}")