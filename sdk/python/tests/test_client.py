"""Tests for HitlClient."""

from unittest.mock import AsyncMock, patch

import pytest

from hitl import HitlClient, HitlDenied, HitlExtensionUnavailable, HitlVerificationError
from hitl.models import SignedResponse


def _make_signed_response() -> SignedResponse:
    return SignedResponse(
        signature="a" * 86,
        access_token="header.eyJzdWIiOiJ1c2VyMSJ9.sig",
        user_id="user1",
        nonce="a" * 64,
        timestamp=1700000000,
    )


@pytest.mark.asyncio
async def test_extension_unavailable_raises() -> None:
    with patch("hitl._client.check_extension_availability", new_callable=AsyncMock, return_value=False):
        client = HitlClient.from_env()
        with pytest.raises(HitlExtensionUnavailable):
            await client.request_approval("delete /tmp/x")


@pytest.mark.asyncio
async def test_denied_response_raises_hitl_denied() -> None:
    with (
        patch("hitl._client.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl._client.generate_challenge") as mock_gen,
        patch(
            "hitl._client.request_signature",
            new_callable=AsyncMock,
            return_value={"denied": True, "nonce": "a" * 64, "timestamp": 0},
        ),
    ):
        import time
        from hitl.models import ChallengeRequest
        mock_gen.return_value = ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action="delete /tmp/x",
            tool_name="test",
            version="1",
        )
        client = HitlClient.from_env()
        with pytest.raises(HitlDenied):
            await client.request_approval("delete /tmp/x")


@pytest.mark.asyncio
async def test_approved_returns_signed_response() -> None:
    mock_response = _make_signed_response()
    with (
        patch("hitl._client.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl._client.generate_challenge") as mock_gen,
        patch("hitl._client.request_signature", new_callable=AsyncMock, return_value=mock_response),
        patch("hitl._client.verify_signed_response", new_callable=AsyncMock, return_value=True),
    ):
        import time
        from hitl.models import ChallengeRequest
        mock_gen.return_value = ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action="run cmd",
            tool_name="test",
            version="1",
        )
        client = HitlClient.from_env()
        result = await client.request_approval("run cmd")

    assert result.user_id == "user1"
    assert result.signature is not None


@pytest.mark.asyncio
async def test_bad_signature_raises_verification_error() -> None:
    mock_response = _make_signed_response()
    with (
        patch("hitl._client.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl._client.generate_challenge") as mock_gen,
        patch("hitl._client.request_signature", new_callable=AsyncMock, return_value=mock_response),
        patch("hitl._client.verify_signed_response", new_callable=AsyncMock, return_value=False),
    ):
        import time
        from hitl.models import ChallengeRequest
        mock_gen.return_value = ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action="run cmd",
            tool_name="test",
            version="1",
        )
        client = HitlClient.from_env()
        with pytest.raises(HitlVerificationError):
            await client.request_approval("run cmd")
