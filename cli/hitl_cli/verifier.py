import base64
import os
import time
from typing import Any

import redis.asyncio as aioredis
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .challenge import challenge_bytes
from .keycloak_client import KeycloakClient
from .models import ChallengeRequest, SignedResponse


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(padded)


def _parse_jwt_sub(token: str) -> str:
    import json

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT: expected 3 parts")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
    sub: str = payload["sub"]
    return sub


async def _check_nonce(nonce: str) -> None:
    redis_url = os.getenv("NONCE_STORE_REDIS_URL", "redis://localhost:6379/0")
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))
    key = f"hitl:nonce:{nonce}"
    client: Any = aioredis.from_url(redis_url)
    try:
        # SET NX EX: only set if not exists, expires after TTL
        was_set: bool = await client.set(key, "1", nx=True, ex=ttl * 2)
        if not was_set:
            raise ValueError(f"Nonce already used: {nonce!r}")
    finally:
        await client.aclose()


async def verify_signed_response(
    challenge: ChallengeRequest,
    response: SignedResponse,
    keycloak: KeycloakClient,
) -> bool:
    # 1. Timestamp freshness
    age = abs(time.time() - challenge.timestamp)
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))
    if age > ttl:
        raise ValueError(f"Challenge expired (age={age:.0f}s, ttl={ttl}s)")

    # 2. Nonce consistency
    if response.nonce != challenge.nonce:
        raise ValueError("Response nonce does not match challenge nonce")

    # 3. Redis nonce dedup (prevents replay)
    await _check_nonce(challenge.nonce)

    # 4. Extract user ID from access token sub claim
    try:
        user_id = _parse_jwt_sub(response.access_token)
    except Exception as exc:
        raise ValueError(f"Cannot parse access_token sub: {exc}") from exc

    if user_id != response.user_id:
        raise ValueError("user_id in response does not match access_token sub")

    # 5. Fetch public key from Keycloak
    pubkey_b64url = await keycloak.get_user_pubkey(user_id)
    pubkey_bytes = _b64url_decode(pubkey_b64url)
    public_key = Ed25519PublicKey.from_public_bytes(pubkey_bytes)

    # 6. Reconstruct canonical challenge bytes
    payload = challenge_bytes(challenge)

    # 7. Decode and verify signature
    sig_bytes = _b64url_decode(response.signature)
    try:
        public_key.verify(sig_bytes, payload)
    except InvalidSignature:
        return False

    return True
