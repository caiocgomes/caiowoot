import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_text_message(phone_number: str, text: str) -> dict:
    url = f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}"

    payload = {
        "number": phone_number,
        "text": text,
    }

    headers = {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
