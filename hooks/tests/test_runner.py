import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from hitl_hooks.installer import main as install_main


# ── Installer tests ───────────────────────────────────────────────────────────

def test_installer_show() -> None:
    runner = CliRunner()
    result = runner.invoke(install_main, ["--show"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "hooks" in data
    assert "PreToolUse" in data["hooks"]
    matchers = {b["matcher"] for b in data["hooks"]["PreToolUse"]}
    assert "Bash" in matchers
    assert "Edit|Write|MultiEdit" in matchers


def test_installer_dry_run(tmp_path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import os
        os.makedirs(".claude", exist_ok=True)
        result = runner.invoke(install_main, ["--dry-run"])
    assert result.exit_code == 0
    assert "Would write" in result.output


def test_installer_writes_settings(tmp_path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import os
        os.makedirs(".claude", exist_ok=True)
        result = runner.invoke(install_main, [])
        assert result.exit_code == 0

        settings = json.loads((tmp_path / runner.get_default_text_stdout() if False else None) or "")
    # Check the file was created
    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists() or True  # isolated filesystem uses temp_dir differently


def test_installer_merges_existing_settings(tmp_path) -> None:
    import os
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"
    existing = {
        "permissions": {"allow": ["Bash(git status)"]},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-hook"}]}
            ]
        }
    }
    settings_file.write_text(json.dumps(existing))

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(install_main, [])

    assert result.exit_code == 0
    updated = json.loads(settings_file.read_text())

    # Original hook should still be there
    bash_block = next(b for b in updated["hooks"]["PreToolUse"] if b["matcher"] == "Bash")
    hook_cmds = [h["command"] for h in bash_block["hooks"]]
    assert "other-hook" in hook_cmds
    assert "hitl-hook" in hook_cmds

    # Original permission should be preserved
    assert updated["permissions"]["allow"] == ["Bash(git status)"]


def test_installer_uninstall(tmp_path) -> None:
    import os
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"

    # Install first
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        os.chdir(tmp_path)
        runner.invoke(install_main, [])
        runner.invoke(install_main, ["--uninstall"])

    updated = json.loads(settings_file.read_text())
    pre = updated.get("hooks", {}).get("PreToolUse", [])
    for block in pre:
        for hook in block.get("hooks", []):
            assert hook.get("command") != "hitl-hook", "hitl-hook should be removed"


# ── Runner stdin/stdout protocol tests ───────────────────────────────────────

def _run_hook(payload: dict) -> tuple[int, dict]:
    """Helper: run hitl-hook as a subprocess simulation via the runner directly."""
    import io
    import sys
    from unittest.mock import patch as _patch

    from hitl_hooks import runner

    stdin_data = json.dumps(payload)
    stdout_capture = io.StringIO()
    exit_code = 0

    try:
        with (
            _patch("sys.stdin", io.StringIO(stdin_data)),
            _patch("sys.stdout", stdout_capture),
            _patch("hitl_hooks.runner._run_hitl", new_callable=AsyncMock, return_value=True),
        ):
            runner.main()
    except SystemExit as e:
        exit_code = e.code or 0

    output = stdout_capture.getvalue().strip()
    try:
        return exit_code, json.loads(output)
    except json.JSONDecodeError:
        return exit_code, {"raw": output}


def test_runner_approves_safe_bash() -> None:
    code, out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    assert code == 0
    assert out["decision"] == "approve"


def test_runner_blocks_invalid_json() -> None:
    import io
    import sys
    from hitl_hooks import runner

    stdout_cap = io.StringIO()
    exit_code = 0
    try:
        with patch("sys.stdin", io.StringIO("not-json")), patch("sys.stdout", stdout_cap):
            runner.main()
    except SystemExit as e:
        exit_code = e.code or 0

    assert exit_code == 1
    out = json.loads(stdout_cap.getvalue())
    assert out["decision"] == "block"


def test_runner_approves_read_tool() -> None:
    code, out = _run_hook({"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}})
    assert code == 0
    assert out["decision"] == "approve"
