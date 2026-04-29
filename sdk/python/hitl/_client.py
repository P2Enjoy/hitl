from __future__ import annotations

from .challenge import check_extension_availability, generate_challenge, request_signature
from .exceptions import (
    HitlDenied,
    HitlExtensionUnavailable,
    HitlTimeout,
    HitlVerificationError,
)
from .oauth import OAuthClient
from .models import SignedResponse
from .verify import verify_signed_response


class HitlClient:
    """
    High-level client for the HITL signing flow.

    Usage:
        client = HitlClient.from_env()
        await client.request_approval("delete /tmp/x")  # raises HitlDenied if denied
    """

    def __init__(self, oauth_client: OAuthClient) -> None:
        self._oauth_client = oauth_client

    @classmethod
    def from_env(cls) -> "HitlClient":
        """Construct a client from environment variables."""
        return cls(oauth_client=OAuthClient.from_env())

    async def request_approval(
        self,
        action: str,
        tool_name: str = "hitl-sdk",
    ) -> SignedResponse:
        """
        Run the full challenge → sign → verify pipeline.

        Returns the verified SignedResponse on approval.

        Raises:
            HitlExtensionUnavailable — signing host not reachable
            HitlDenied               — user clicked Deny
            HitlTimeout              — user did not respond in time
            HitlVerificationError    — signature invalid or replay detected
        """
        if not await check_extension_availability():
            raise HitlExtensionUnavailable(
                "HITL signing host is not reachable. "
                "Ensure the browser extension is loaded and the native messaging host is installed. "
                "Run `hitl-setup host` to install the host."
            )

        challenge = generate_challenge(action, tool_name)

        try:
            response = await request_signature(challenge)
        except Exception as exc:
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg:
                raise HitlTimeout(f"User did not respond in time: {exc}") from exc
            raise

        if isinstance(response, dict) and response.get("denied"):
            raise HitlDenied(f"User denied the action: {action!r}")

        if not isinstance(response, SignedResponse):
            raise HitlVerificationError(f"Unexpected response format: {response!r}")

        try:
            approved = await verify_signed_response(challenge, response, self._oauth_client)
        except HitlVerificationError:
            raise
        except Exception as exc:
            raise HitlVerificationError(str(exc)) from exc

        if not approved:
            raise HitlVerificationError("Ed25519 signature verification failed")

        return response
