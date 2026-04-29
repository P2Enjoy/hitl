from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from hitl_skill.skill import main
from hitl import HitlDenied, HitlExtensionUnavailable


def test_approved_exits_0() -> None:
    runner = CliRunner()
    with patch("hitl_skill.skill.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(return_value=None)
        result = runner.invoke(main, ["--action", "test"])

    assert result.exit_code == 0
    assert "HITL_APPROVED" in result.output


def test_denied_exits_1() -> None:
    runner = CliRunner()
    with patch("hitl_skill.skill.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(side_effect=HitlDenied("denied"))
        result = runner.invoke(main, ["--action", "test"])

    assert result.exit_code == 1
    assert "HITL_DENIED" in result.output


def test_extension_unavailable_exits_1() -> None:
    runner = CliRunner()
    with patch("hitl_skill.skill.HitlClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.from_env.return_value = mock_client
        mock_client.request_approval = AsyncMock(
            side_effect=HitlExtensionUnavailable("not reachable")
        )
        result = runner.invoke(main, ["--action", "test"])

    assert result.exit_code == 1
    assert "HITL_DENIED" in result.output
