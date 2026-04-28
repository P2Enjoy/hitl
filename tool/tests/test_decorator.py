from unittest.mock import AsyncMock, patch

import pytest

from hitl_tool.decorator import require_human_approval
from hitl_tool.exceptions import HitlDenied, HitlVerificationError


@require_human_approval("Test action: {kwargs[value]}")
async def _sample_tool(value: str) -> str:
    return f"result:{value}"


@pytest.mark.asyncio
async def test_decorator_allows_when_approved() -> None:
    mock_response = AsyncMock()
    with patch("hitl_tool.hitl_check.perform_hitl_check", new_callable=AsyncMock, return_value=mock_response):
        result = await _sample_tool(value="hello")
    assert result == "result:hello"


@pytest.mark.asyncio
async def test_decorator_raises_on_denied() -> None:
    with patch(
        "hitl_tool.hitl_check.perform_hitl_check",
        new_callable=AsyncMock,
        side_effect=HitlDenied("denied"),
    ):
        with pytest.raises(HitlDenied):
            await _sample_tool(value="hello")


@pytest.mark.asyncio
async def test_decorator_action_string_formatted() -> None:
    captured: list[str] = []

    async def mock_check(action: str, tool_name: str) -> None:
        captured.append(action)

    with patch("hitl_tool.hitl_check.perform_hitl_check", side_effect=mock_check):
        await _sample_tool(value="my-value")

    assert captured[0] == "Test action: my-value"


@pytest.mark.asyncio
async def test_decorator_fallback_on_template_error() -> None:
    @require_human_approval("Bad template: {kwargs[nonexistent_key]}")
    async def _bad_template(value: str) -> str:
        return value

    captured: list[str] = []

    async def mock_check(action: str, tool_name: str) -> None:
        captured.append(action)

    with patch("hitl_tool.hitl_check.perform_hitl_check", side_effect=mock_check):
        await _bad_template(value="x")

    assert "_bad_template" in captured[0]
