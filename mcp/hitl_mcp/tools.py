from typing import Annotated

from hitl_cli.challenge import check_extension_availability, generate_challenge, request_signature
from hitl_cli.keycloak_client import KeycloakClient
from hitl_cli.models import SignedResponse
from hitl_cli.verifier import verify_signed_response
from pydantic import BaseModel, Field


class ApprovalResult(BaseModel):
    approved: bool
    challenge_id: str      # nonce (used for correlation / audit)
    user_id: str | None    # Keycloak sub if approved
    signature: str | None  # base64url signature if approved
    timestamp: int
    reason: str | None = None  # error/denial reason if not approved


class AvailabilityStatus(BaseModel):
    available: bool
    message: str


async def request_approval(
    action: Annotated[str, Field(description="Human-readable description of the action requiring approval", min_length=1, max_length=4096)],
    tool_name: Annotated[str, Field(description="Name of the tool or agent requesting approval", default="mcp-tool")] = "mcp-tool",
) -> ApprovalResult:
    """
    Request cryptographically verified human approval for a sensitive action.

    Sends a challenge to the user's browser extension and blocks until the user
    approves or denies. The response is Ed25519-signed and verified against the
    user's public key registered in Keycloak.

    Returns an ApprovalResult. If approved=False, the tool should abort.
    """
    if not await check_extension_availability():
        return ApprovalResult(
            approved=False,
            challenge_id="",
            user_id=None,
            signature=None,
            timestamp=0,
            reason="HITL signing host not reachable — browser extension may not be running",
        )

    challenge = generate_challenge(action, tool_name)

    try:
        response = await request_signature(challenge)
    except Exception as exc:
        return ApprovalResult(
            approved=False,
            challenge_id=challenge.nonce,
            user_id=None,
            signature=None,
            timestamp=challenge.timestamp,
            reason=f"Failed to get signature: {exc}",
        )

    if isinstance(response, dict) and response.get("denied"):
        return ApprovalResult(
            approved=False,
            challenge_id=challenge.nonce,
            user_id=None,
            signature=None,
            timestamp=challenge.timestamp,
            reason="User denied the request",
        )

    if not isinstance(response, SignedResponse):
        return ApprovalResult(
            approved=False,
            challenge_id=challenge.nonce,
            user_id=None,
            signature=None,
            timestamp=challenge.timestamp,
            reason=f"Unexpected response format: {response!r}",
        )

    keycloak = KeycloakClient.from_env()
    try:
        approved = await verify_signed_response(challenge, response, keycloak)
    except ValueError as exc:
        return ApprovalResult(
            approved=False,
            challenge_id=challenge.nonce,
            user_id=response.user_id,
            signature=None,
            timestamp=challenge.timestamp,
            reason=f"Verification failed: {exc}",
        )

    return ApprovalResult(
        approved=approved,
        challenge_id=challenge.nonce,
        user_id=response.user_id,
        signature=response.signature if approved else None,
        timestamp=challenge.timestamp,
        reason=None if approved else "Signature verification failed",
    )


async def check_hitl_availability() -> AvailabilityStatus:
    """
    Check whether the HITL signing extension is reachable.

    Returns {available: true} when the browser extension and native messaging
    host are running and ready to handle approval requests.
    """
    available = await check_extension_availability()
    return AvailabilityStatus(
        available=available,
        message="HITL signing host is ready" if available else "HITL signing host is not reachable",
    )
