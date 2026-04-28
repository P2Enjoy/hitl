from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from hitl_skill.skill import main


def _make_signed_response():
    from hitl_cli.models import SignedResponse
    return SignedResponse(
        signature="a" * 86,  # ~64 bytes base64url
        access_token="header.eyJzdWIiOiJ1c2VyMSJ9.sig",
        user_id="user1",
        nonce="a" * 64,
        timestamp=1700000000,
    )


def test_approved_exits_0() -> None:
    runner = CliRunner()
    with (
        patch("hitl_skill.skill.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl_skill.skill.generate_challenge") as mock_gen,
        patch("hitl_skill.skill.request_signature", new_callable=AsyncMock, return_value=_make_signed_response()),
        patch("hitl_skill.skill.verify_signed_response", new_callable=AsyncMock, return_value=True),
    ):
        from hitl_cli.models import ChallengeRequest
        import time
        mock_gen.return_value = ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action="test",
            tool_name="skill",
            version="1",
        )
        result = runner.invoke(main, ["--action", "test", "--skip-verify"])

    assert result.exit_code == 0
    assert "HITL_APPROVED" in result.output


def test_denied_exits_1() -> None:
    runner = CliRunner()
    with (
        patch("hitl_skill.skill.check_extension_availability", new_callable=AsyncMock, return_value=True),
        patch("hitl_skill.skill.generate_challenge") as mock_gen,
        patch(
            "hitl_skill.skill.request_signature",
            new_callable=AsyncMock,
            return_value={"denied": True, "nonce": "a" * 64, "timestamp": 0},
        ),
    ):
        from hitl_cli.models import ChallengeRequest
        import time
        mock_gen.return_value = ChallengeRequest(
            nonce="a" * 64,
            timestamp=int(time.time()),
            action="test",
            tool_name="skill",
            version="1",
        )
        result = runner.invoke(main, ["--action", "test"])

    assert result.exit_code == 1
    assert "HITL_DENIED" in result.output


def test_extension_unavailable_exits_1() -> None:
    runner = CliRunner()
    with patch(
        "hitl_skill.skill.check_extension_availability",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = runner.invoke(main, ["--action", "test"])

    assert result.exit_code == 1
    assert "HITL_DENIED" in result.output
