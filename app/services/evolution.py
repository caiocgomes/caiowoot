import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_http_client = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30)
    return _http_client


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

    client = get_http_client()
    response = await client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


async def send_media_message(phone_number: str, base64_data: str, mime_type: str, caption: str = "") -> dict:
    url = f"{settings.evolution_api_url}/message/sendMedia/{settings.evolution_instance}"

    payload = {
        "number": phone_number,
        "mediatype": "image" if mime_type.startswith("image/") else "document",
        "media": base64_data,
        "caption": caption,
        "mimetype": mime_type,
    }

    headers = {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }

    client = get_http_client()
    response = await client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


async def send_document_message(phone_number: str, base64_data: str, filename: str, caption: str = "") -> dict:
    url = f"{settings.evolution_api_url}/message/sendMedia/{settings.evolution_instance}"

    payload = {
        "number": phone_number,
        "mediatype": "document",
        "media": base64_data,
        "caption": caption,
        "fileName": filename,
    }

    headers = {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }

    client = get_http_client()
    response = await client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
