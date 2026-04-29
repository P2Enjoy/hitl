"""
Challenge generation and signing-host communication.

The canonical challenge_bytes() serialization MUST remain byte-for-byte
identical to sdk/node/src/challenge.ts:challengeBytes().
"""

from __future__ import annotations

import json
import os
import secrets
import time

import httpx

from .models import ChallengeRequest, SignedResponse


def generate_challenge(action: str, tool_name: str) -> ChallengeRequest:
    return ChallengeRequest(
        nonce=secrets.token_hex(32),  # 256-bit random nonce, 64 hex chars
        timestamp=int(time.time()),
        action=action,
        tool_name=tool_name,
        version="1",
    )


def challenge_bytes(challenge: ChallengeRequest) -> bytes:
    """
    Canonical UTF-8 serialization of a challenge for signing/verifying.

    MUST stay byte-for-byte identical to sdk/node/src/challenge.ts:challengeBytes().
    Keys are sorted, no whitespace.
    """
    payload = {
        "action": challenge.action,
        "nonce": challenge.nonce,
        "timestamp": challenge.timestamp,
        "tool_name": challenge.tool_name,
        "version": challenge.version,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def request_signature(
    challenge: ChallengeRequest,
) -> SignedResponse | dict[str, object]:
    port = int(os.getenv("EXTENSION_SIGNING_PORT", "7331"))
    ttl = int(os.getenv("CHALLENGE_TTL_SECONDS", "300"))

    async with httpx.AsyncClient(timeout=float(ttl + 10)) as client:
        resp = await client.post(
            f"http://127.0.0.1:{port}/sign",
            json=challenge.model_dump(),
        )
        resp.raise_for_status()
        data: dict[str, object] = resp.json()

    if data.get("denied"):
        return data
    return SignedResponse.model_validate(data)


async def check_extension_availability() -> bool:
    port = int(os.getenv("EXTENSION_SIGNING_PORT", "7331"))
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/health")
            return resp.status_code == 200
    except Exception:
        return False
