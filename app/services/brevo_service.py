import aiohttp
from app.core.config import settings
from loguru import logger

async def subscribe_to_brevo_list(email: str, list_id: int):
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

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 201:
                logger.info(f"Contact {email} successfully subscribed to Brevo list {list_id}")
            elif response.status == 204:
                logger.info(f"Contact {email} was already in Brevo list {list_id}")
            else:
                response_text = await response.text()
                logger.error(f"Failed to subscribe {email} to Brevo list {list_id}. Status: {response.status}, Response: {response_text}")
                raise Exception(f"Failed to subscribe email to Brevo list. Status: {response.status}, Response: {response_text}")