import os
import time
from typing import Any

import httpx


class KeycloakClient:
    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @classmethod
    def from_env(cls) -> "KeycloakClient":
        return cls(
            base_url=os.environ["KEYCLOAK_HOST"],
            realm=os.environ.get("KEYCLOAK_REALM", "hitl"),
            client_id=os.environ["KEYCLOAK_CLI_CLIENT_ID"],
            client_secret=os.environ["KEYCLOAK_CLI_CLIENT_SECRET"],
        )

    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._token_expires_at - 10:
            return
        token_url = f"{self._base_url}/realms/{self._realm}/protocol/openid-connect/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + int(data.get("expires_in", 300))

    async def get_user_pubkey(self, user_id: str) -> str:
        await self._ensure_token()
        url = f"{self._base_url}/admin/realms/{self._realm}/users/{user_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()

        attrs: dict[str, list[str]] = data.get("attributes", {})
        keys = attrs.get("ed25519_public_key", [])
        if not keys:
            raise ValueError(f"No ed25519_public_key registered for user {user_id!r}")
        return keys[0]

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        await self._ensure_token()
        url = f"{self._base_url}/admin/realms/{self._realm}/users/{user_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result
