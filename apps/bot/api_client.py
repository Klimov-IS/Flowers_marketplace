"""Async HTTP client for internal FastAPI endpoints."""
import logging
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class BotAPIClient:
    """Client for bot-to-API communication."""

    def __init__(self, base_url: str, bot_token: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Bot-Token": bot_token},
            timeout=60.0,
        )

    async def close(self) -> None:
        await self.client.aclose()

    # --- Link management ---

    async def get_link(self, telegram_user_id: int) -> dict | None:
        """Get existing link for a Telegram user. Returns None if not linked."""
        try:
            resp = await self.client.get(f"/internal/telegram/link/{telegram_user_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("get_link failed: %s", e)
            return None

    async def create_link(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        role: str,
        entity_id: UUID,
        username: str | None = None,
        first_name: str | None = None,
    ) -> dict:
        """Create a new Telegram link."""
        resp = await self.client.post(
            "/internal/telegram/link",
            json={
                "telegram_user_id": telegram_user_id,
                "telegram_chat_id": telegram_chat_id,
                "role": role,
                "entity_id": str(entity_id),
                "username": username,
                "first_name": first_name,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_link(self, telegram_user_id: int) -> bool:
        """Delete a Telegram link."""
        resp = await self.client.delete(f"/internal/telegram/link/{telegram_user_id}")
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    # --- Supplier lookup ---

    async def find_supplier_by_phone(self, phone: str) -> dict | None:
        """Find supplier by phone number."""
        resp = await self.client.post(
            "/internal/telegram/find-by-phone",
            json={"phone": phone},
        )
        resp.raise_for_status()
        data = resp.json()
        return data if data.get("found") else None

    async def register_supplier(
        self,
        name: str,
        phone: str,
        city_name: str | None = None,
    ) -> dict:
        """Register a new supplier."""
        resp = await self.client.post(
            "/internal/telegram/register-supplier",
            json={"name": name, "phone": phone, "city_name": city_name},
        )
        resp.raise_for_status()
        return resp.json()

    # --- Price management ---

    async def upload_price(
        self,
        supplier_id: UUID,
        filename: str,
        content: bytes,
    ) -> dict:
        """Upload a price list file."""
        resp = await self.client.post(
            f"/internal/telegram/upload-price/{supplier_id}",
            files={"file": (filename, content)},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_last_import(self, supplier_id: UUID) -> dict | None:
        """Get the last import for a supplier."""
        resp = await self.client.get(
            f"/internal/telegram/last-import/{supplier_id}",
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
