"""
hitl-sdk — Cryptographically signed human-in-the-loop permissions.

Quick start:

    from hitl import HitlClient

    client = HitlClient.from_env()
    await client.request_approval("delete /tmp/x")   # raises HitlDenied if denied

Decorator:

    from hitl import require_human_approval

    @require_human_approval("Delete {path}")
    async def delete_file(path: str) -> bool: ...

Low-level building blocks (for custom integrations):

    from hitl.challenge import generate_challenge, challenge_bytes, request_signature
    from hitl.verify import verify_signed_response
    from hitl.keycloak import KeycloakClient
    from hitl.models import ChallengeRequest, SignedResponse
"""

from ._client import HitlClient
from ._decorators import require_human_approval
from .exceptions import (
    HitlDenied,
    HitlError,
    HitlExtensionUnavailable,
    HitlTimeout,
    HitlVerificationError,
)

__all__ = [
    "HitlClient",
    "require_human_approval",
    "HitlError",
    "HitlDenied",
    "HitlTimeout",
    "HitlVerificationError",
    "HitlExtensionUnavailable",
]

__version__ = "0.1.0"
