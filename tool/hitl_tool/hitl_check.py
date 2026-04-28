from hitl_cli.challenge import check_extension_availability, generate_challenge, request_signature
from hitl_cli.keycloak_client import KeycloakClient
from hitl_cli.models import SignedResponse
from hitl_cli.verifier import verify_signed_response

from .exceptions import (
    HitlDenied,
    HitlExtensionUnavailable,
    HitlTimeout,
    HitlVerificationError,
)


async def perform_hitl_check(action: str, tool_name: str) -> SignedResponse:
    if not await check_extension_availability():
        raise HitlExtensionUnavailable(
            "HITL signing host is not reachable. "
            "Ensure the browser extension is loaded and the native messaging host is installed."
        )

    challenge = generate_challenge(action, tool_name)

    try:
        response = await request_signature(challenge)
    except Exception as exc:
        if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
            raise HitlTimeout(f"User did not respond in time: {exc}") from exc
        raise

    if isinstance(response, dict) and response.get("denied"):
        raise HitlDenied(f"User denied the action: {action!r}")

    if not isinstance(response, SignedResponse):
        raise HitlVerificationError(f"Unexpected response format: {response!r}")

    keycloak = KeycloakClient.from_env()
    try:
        approved = await verify_signed_response(challenge, response, keycloak)
    except ValueError as exc:
        raise HitlVerificationError(str(exc)) from exc

    if not approved:
        raise HitlVerificationError("Ed25519 signature verification failed")

    return response
