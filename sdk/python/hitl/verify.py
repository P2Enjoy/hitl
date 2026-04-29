from __future__ import annotations

import base64
import os
import time
from typing import Any

import httpx
import jwt as pyjwt
import redis.asyncio as aioredis
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .challenge import challenge_bytes
from .exceptions import HitlVerificationError
from .models import ChallengeRequest, SignedResponse

# JWKS cache: {jwks_uri: (fetched_at, raw_jwks_dict)}
_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL = 3600.0  # refresh keys at most every hour


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(padded)


async def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    """Fetch and cache JWKS from the OAuth server."""
    now = time.time()
    if jwks_uri in _JWKS_CACHE:
        fetched_at, data = _JWKS_CACHE[jwks_uri]
        if now - fetched_at < _JWKS_TTL:
            return data

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        data = resp.json()

    _JWKS_CACHE[jwks_uri] = (now, data)
    return data


async def _verify_jwt_and_get_sub(token: str, issuer: str) -> str:
    """
    Verify a JWT's RS256/ES256 signature against the OAuth server's JWKS
    and return the 'sub' claim.

    Raises HitlVerificationError if the signature is invalid, the issuer
    doesn't match, or the token is expired.
    """
    jwks_uri = f"{issuer}/protocol/openid-connect/certs"
    jwks_data = await _fetch_jwks(jwks_uri)

    try:
        header = pyjwt.get_unverified_header(token)
    except pyjwt.DecodeError as exc:
        raise HitlVerificationError(f"Malformed JWT header: {exc}") from exc

    kid = header.get("kid")
    jwks = pyjwt.PyJWKSet.from_dict(jwks_data)

    signing_key = None
    for jwk in jwks.keys:
        if kid is None or jwk.key_id == kid:
            signing_key = jwk.key
            break

    if signing_key is None:
        # Key not found — cache may be stale, force refresh once
        _JWKS_CACHE.pop(jwks_uri, None)
        jwks_data = await _fetch_jwks(jwks_uri)
        jwks = pyjwt.PyJWKSet.from_dict(jwks_data)
        for jwk in jwks.keys:
            if kid is None or jwk.key_id == kid:
                signing_key = jwk.key
                break
        if signing_key is None:
            raise HitlVerificationError(f"No matching key in JWKS for kid={kid!r}")

    try:
        payload: dict[str, Any] = pyjwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            options={"verify_aud": False},
            issuer=issuer,
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise HitlVerificationError(f"JWT expired: {exc}") from exc
    except pyjwt.InvalidIssuerError as exc:
        raise HitlVerificationError(f"JWT issuer mismatch: {exc}") from exc
    except pyjwt.InvalidTokenError as exc:
        raise HitlVerificationError(f"JWT verification failed: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise HitlVerificationError("JWT missing sub claim")
    return str(sub)


async def _check_nonce(nonce: str) -> None:
    redis_url = os.getenv("NONCE_STORE_REDIS_URL", "redis://localhost:6379/0")
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))
    key = f"hitl:nonce:{nonce}"
    client: Any = aioredis.from_url(redis_url)
    try:
        was_set: bool = await client.set(key, "1", nx=True, ex=ttl * 2)
        if not was_set:
            raise HitlVerificationError(f"Nonce already used: {nonce!r}")
    finally:
        await client.aclose()


async def verify_signed_response(
    challenge: ChallengeRequest,
    response: SignedResponse,
    oauth_client: Any,  # OAuthClient — typed as Any to avoid circular import
) -> bool:
    """
    Verify a SignedResponse against a ChallengeRequest.

    Raises HitlVerificationError on any check failure.
    Returns True if the Ed25519 signature is valid.
    """
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))
    age = abs(time.time() - challenge.timestamp)
    if age > ttl:
        raise HitlVerificationError(f"Challenge expired (age={age:.0f}s, ttl={ttl}s)")

    if response.nonce != challenge.nonce:
        raise HitlVerificationError("Response nonce does not match challenge nonce")

    await _check_nonce(challenge.nonce)

    # Verify JWT signature cryptographically — prevents crafted/fake JWTs
    issuer = f"{oauth_client.oauth_server_url}/realms/{oauth_client.realm}"
    try:
        user_id = await _verify_jwt_and_get_sub(response.access_token, issuer)
    except HitlVerificationError:
        raise
    except Exception as exc:
        raise HitlVerificationError(f"JWT validation error: {exc}") from exc

    if user_id != response.user_id:
        raise HitlVerificationError("user_id in response does not match access_token sub")

    pubkey_b64url: str = await oauth_client.get_user_pubkey(user_id)
    pubkey_bytes = _b64url_decode(pubkey_b64url)
    public_key = Ed25519PublicKey.from_public_bytes(pubkey_bytes)

    payload = challenge_bytes(challenge)
    sig_bytes = _b64url_decode(response.signature)
    try:
        public_key.verify(sig_bytes, payload)
    except InvalidSignature:
        return False

    return True
