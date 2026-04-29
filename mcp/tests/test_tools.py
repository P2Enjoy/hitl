from unittest.mock import AsyncMock, patch

import pytest

from hitl import HitlDenied, HitlExtensionUnavailable
from hitl.models import SignedResponse
from hitl_mcp.tools import ApprovalResult, check_hitl_availability, request_approval


def _make_signed_response() -> SignedResponse:
    return SignedResponse(
        signature="a" * 86,
        access_token="header.eyJzdWIiOiJ1c2VyMSJ9.sig",
        user_id="user1",
        nonce="a" * 64,
        timestamp=1700000000,
    )


@pytest.mark.asyncio
async def test_request_approval_approved() -> None:
    mock_response = _make_signed_response()

    with patch("hitl_mcp.tools.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(return_value=mock_response)
        result = await request_approval(action="test action")

    assert isinstance(result, ApprovalResult)
    assert result.approved is True
    assert result.user_id == "user1"
    assert result.signature is not None


@pytest.mark.asyncio
async def test_request_approval_extension_unavailable() -> None:
    with patch("hitl_mcp.tools.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(
            side_effect=HitlExtensionUnavailable("not reachable")
        )
        result = await request_approval(action="test action")

    assert result.approved is False
    assert result.reason is not None
    assert "not reachable" in result.reason


@pytest.mark.asyncio
async def test_request_approval_denied() -> None:
    with patch("hitl_mcp.tools.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(
            side_effect=HitlDenied("User denied")
        )
        result = await request_approval(action="test action")

    assert result.approved is False
    assert result.reason is not None


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
