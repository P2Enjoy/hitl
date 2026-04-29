from hitl import HitlClient
from hitl import (
    HitlDenied,
    HitlExtensionUnavailable,
    HitlTimeout,
    HitlVerificationError,
)
from hitl.models import SignedResponse


async def perform_hitl_check(action: str, tool_name: str) -> SignedResponse:
    client = HitlClient.from_env()
    return await client.request_approval(action, tool_name=tool_name)
