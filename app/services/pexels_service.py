import httpx
from app.core.config import settings
from app.core.logging import logger
from typing import Dict, Optional

async def get_image_for_tags(tags: list[str]) -> Optional[Dict[str, str]]:
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": settings.PEXELS_API_KEY}
    params = {"query": " ".join(tags), "per_page": 1}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    if data["photos"]:
        photo = data["photos"][0]
        return {
            "image_url": photo["src"]["medium"],
            "photographer": photo["photographer"],
            "pexels_url": photo["url"]
        }
    else:
        logger.warning(f"No image found for tags: {tags}")
        return None