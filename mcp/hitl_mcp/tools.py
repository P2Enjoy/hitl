from typing import Annotated

from hitl import HitlClient, HitlDenied, HitlExtensionUnavailable, HitlVerificationError
from hitl.challenge import check_extension_availability
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
    client = HitlClient.from_env()
    try:
        response = await client.request_approval(action, tool_name=tool_name)
        return ApprovalResult(
            approved=True,
            challenge_id=response.nonce,
            user_id=response.user_id,
            signature=response.signature,
            timestamp=response.timestamp,
        )
    except HitlExtensionUnavailable as exc:
        return ApprovalResult(
            approved=False, challenge_id="", user_id=None, signature=None,
            timestamp=0, reason=str(exc),
        )
    except HitlDenied as exc:
        return ApprovalResult(
            approved=False, challenge_id="", user_id=None, signature=None,
            timestamp=0, reason=str(exc),
        )
    except HitlVerificationError as exc:
        return ApprovalResult(
            approved=False, challenge_id="", user_id=None, signature=None,
            timestamp=0, reason=f"Verification failed: {exc}",
        )
    except Exception as exc:
        return ApprovalResult(
            approved=False, challenge_id="", user_id=None, signature=None,
            timestamp=0, reason=f"Unexpected error: {exc}",
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
