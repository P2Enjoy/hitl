import json
import os
import secrets
import time

import httpx

from .models import ChallengeRequest, SignedResponse


def generate_challenge(action: str, tool_name: str) -> ChallengeRequest:
    return ChallengeRequest(
        nonce=secrets.token_hex(32),  # 256-bit random nonce
        timestamp=int(time.time()),
        action=action,
        tool_name=tool_name,
        version="1",
    )


def challenge_bytes(challenge: ChallengeRequest) -> bytes:
    # SECURITY: This serialization MUST stay byte-for-byte identical to
    # extension/src/background/crypto.ts:canonicalChallengeBytes().
    # Sorted keys, no whitespace, UTF-8 encoded.
    payload = {
        "action": challenge.action,
        "nonce": challenge.nonce,
        "timestamp": challenge.timestamp,
        "tool_name": challenge.tool_name,
        "version": challenge.version,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def request_signature(challenge: ChallengeRequest) -> SignedResponse | dict[str, object]:
    port = int(os.getenv("EXTENSION_SIGNING_PORT", "7331"))
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))
    url = f"http://127.0.0.1:{port}/sign"

    async with httpx.AsyncClient(timeout=float(ttl + 10)) as client:
        resp = await client.post(url, json=challenge.model_dump())
        resp.raise_for_status()
        data: dict[str, object] = resp.json()

    if data.get("denied"):
        return data  # DeniedResponse-compatible dict

    return SignedResponse.model_validate(data)


async def check_extension_availability() -> bool:
    port = int(os.getenv("EXTENSION_SIGNING_PORT", "7331"))
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/health")
            return resp.status_code == 200
    except Exception:
        return False
