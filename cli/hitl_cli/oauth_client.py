from __future__ import annotations

import os
import time
from typing import Any

import httpx


class OAuthClient:
    """Client for the OAuth/OIDC server (Keycloak by default)."""

    def __init__(
        self,
        oauth_server_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._oauth_server_url = oauth_server_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def oauth_server_url(self) -> str:
        return self._oauth_server_url

    @property
    def realm(self) -> str:
        return self._realm

    @classmethod
    def from_env(cls) -> "OAuthClient":
        url = (
            os.environ.get("OAUTH_SERVER_URL")
            or os.environ.get("KEYCLOAK_HOST")
        )
        if not url:
            raise OSError("OAUTH_SERVER_URL (or KEYCLOAK_HOST) is required")

        realm = (
            os.environ.get("OAUTH_REALM")
            or os.environ.get("KEYCLOAK_REALM")
            or "hitl"
        )
        client_id = (
            os.environ.get("OAUTH_CLI_CLIENT_ID")
            or os.environ.get("KEYCLOAK_CLI_CLIENT_ID")
        )
        if not client_id:
            raise OSError("OAUTH_CLI_CLIENT_ID (or KEYCLOAK_CLI_CLIENT_ID) is required")

        client_secret = (
            os.environ.get("OAUTH_CLI_CLIENT_SECRET")
            or os.environ.get("KEYCLOAK_CLI_CLIENT_SECRET")
        )
        if not client_secret:
            raise OSError("OAUTH_CLI_CLIENT_SECRET (or KEYCLOAK_CLI_CLIENT_SECRET) is required")

        return cls(
            oauth_server_url=url,
            realm=realm,
            client_id=client_id,
            client_secret=client_secret,
        )

    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._token_expires_at - 10:
            return
        token_url = (
            f"{self._oauth_server_url}/realms/{self._realm}/protocol/openid-connect/token"
        )
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
        url = f"{self._oauth_server_url}/admin/realms/{self._realm}/users/{user_id}"
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
        url = f"{self._oauth_server_url}/admin/realms/{self._realm}/users/{user_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result


# Backward-compatible alias
KeycloakClient = OAuthClient
