import base64
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hitl_cli.challenge import challenge_bytes
from hitl_cli.models import ChallengeRequest, SignedResponse
from hitl_mcp.tools import ApprovalResult, check_hitl_availability, request_approval


def _make_jwt(sub: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": sub, "exp": int(time.time()) + 300}).encode()
    ).decode().rstrip("=")
    return f"header.{payload}.sig"


def _sign(private_key: Ed25519PrivateKey, challenge: ChallengeRequest) -> str:
    sig = private_key.sign(challenge_bytes(challenge))
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _pubkey(private_key: Ed25519PrivateKey) -> str:
    return base64.urlsafe_b64encode(private_key.public_key().public_bytes_raw()).decode().rstrip("=")


@pytest.fixture
def keypair():
    return Ed25519PrivateKey.generate()


@pytest.mark.asyncio
async def test_request_approval_approved(keypair) -> None:
    user_id = "user-test-1"
    access_token = _make_jwt(user_id)

    def fake_generate(action: str, tool_name: str) -> ChallengeRequest:
        return ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action=action,
            tool_name=tool_name,
            version="1",
        )

    challenge = fake_generate("test action", "mcp-tool")
    signature = _sign(keypair, challenge)

    mock_response = SignedResponse(
        signature=signature,
        access_token=access_token,
        user_id=user_id,
        nonce=challenge.nonce,
        timestamp=challenge.timestamp,
    )

    with (
        patch("hitl_mcp.tools.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl_mcp.tools.generate_challenge", side_effect=fake_generate),
        patch("hitl_mcp.tools.request_signature", new_callable=AsyncMock, return_value=mock_response),
        patch("hitl_mcp.tools.verify_signed_response", new_callable=AsyncMock, return_value=True),
    ):
        result = await request_approval(action="test action")

    assert isinstance(result, ApprovalResult)
    assert result.approved is True
    assert result.user_id == user_id
    assert result.signature is not None


@pytest.mark.asyncio
async def test_request_approval_extension_unavailable() -> None:
    with patch("hitl_mcp.tools.check_extension_availability", new_callable=AsyncMock, return_value=False):
        result = await request_approval(action="test action")

    assert result.approved is False
    assert result.reason is not None
    assert "not reachable" in result.reason


@pytest.mark.asyncio
async def test_request_approval_denied() -> None:
    def fake_generate(action: str, tool_name: str) -> ChallengeRequest:
        return ChallengeRequest(
            nonce="b" * 64,
            timestamp=int(time.time()),
            action=action,
            tool_name=tool_name,
            version="1",
        )

    with (
        patch("hitl_mcp.tools.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl_mcp.tools.generate_challenge", side_effect=fake_generate),
        patch(
            "hitl_mcp.tools.request_signature",
            new_callable=AsyncMock,
            return_value={"denied": True, "nonce": "b" * 64, "timestamp": 0},
        ),
    ):
        result = await request_approval(action="test action")

    assert result.approved is False
    assert "denied" in (result.reason or "").lower()


@pytest.mark.asyncio
async def test_check_hitl_availability_true() -> None:
    with patch("hitl_mcp.tools.check_extension_availability", new_callable=AsyncMock, return_value=True):
        status = await check_hitl_availability()
    assert status.available is True


@pytest.mark.asyncio
async def test_check_hitl_availability_false() -> None:
    with patch("hitl_mcp.tools.check_extension_availability", new_callable=AsyncMock, return_value=False):
        status = await check_hitl_availability()
    assert status.available is False
