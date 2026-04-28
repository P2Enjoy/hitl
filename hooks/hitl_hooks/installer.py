"""
hitl-install — writes the Claude Code hook configuration into settings.json.

Usage:
    hitl-install                    # project-level (.claude/settings.json in cwd)
    hitl-install --global           # user-level    (~/.claude/settings.json)
    hitl-install --show             # print the snippet without writing
    hitl-install --uninstall        # remove HITL hooks from settings.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click


# ── Hook snippet ──────────────────────────────────────────────────────────────

# Tools we intercept with HITL. Bash handles shell commands;
# Edit/Write/MultiEdit handle file mutations.
_HOOK_ENTRY: dict[str, Any] = {
    "type": "command",
    "command": "hitl-hook",
}

_HOOK_MATCHERS: list[dict[str, Any]] = [
    {"matcher": "Bash",                  "hooks": [_HOOK_ENTRY]},
    {"matcher": "Edit|Write|MultiEdit",  "hooks": [_HOOK_ENTRY]},
]


def _settings_path(global_: bool) -> Path:
    if global_:
        return Path.home() / ".claude" / "settings.json"
    return Path.cwd() / ".claude" / "settings.json"


def _load(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            with path.open() as f:
                loaded: dict[str, Any] = json.load(f)
                return loaded
        except (json.JSONDecodeError, OSError) as exc:
            click.echo(f"Warning: could not read {path}: {exc}", err=True)
    return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _is_hitl_hook(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and entry.get("type") == "command"
        and entry.get("command") == "hitl-hook"
    )


def _install(cfg: dict[str, Any]) -> dict[str, Any]:
    hooks: dict[str, Any] = cfg.setdefault("hooks", {})
    pre: list[dict[str, Any]] = hooks.setdefault("PreToolUse", [])

    # Build a map of existing matchers for easy lookup
    existing: dict[str, dict[str, Any]] = {
        entry["matcher"]: entry for entry in pre if "matcher" in entry
    }

    for block in _HOOK_MATCHERS:
        matcher = block["matcher"]
        if matcher in existing:
            # Add our hook to the existing matcher block if not already there
            hook_list: list[Any] = existing[matcher].setdefault("hooks", [])
            if not any(_is_hitl_hook(h) for h in hook_list):
                hook_list.append(_HOOK_ENTRY)
        else:
            pre.append({"matcher": matcher, "hooks": [_HOOK_ENTRY]})

    return cfg


def _uninstall(cfg: dict[str, Any]) -> dict[str, Any]:
    pre: list[Any] = cfg.get("hooks", {}).get("PreToolUse", [])
    for block in pre:
        if isinstance(block, dict) and "hooks" in block:
            block["hooks"] = [h for h in block["hooks"] if not _is_hitl_hook(h)]
    # Remove empty matcher blocks
    cfg.get("hooks", {})["PreToolUse"] = [
        b for b in pre if isinstance(b, dict) and b.get("hooks")
    ]
    return cfg


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--global", "global_", is_flag=True, default=False,
              help="Install into ~/.claude/settings.json (user-level) instead of project-level")
@click.option("--show", is_flag=True, default=False,
              help="Print the hook configuration snippet without writing anything")
@click.option("--uninstall", is_flag=True, default=False,
              help="Remove HITL hooks from the settings file")
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would be written without modifying any file")
def main(global_: bool, show: bool, uninstall: bool, dry_run: bool) -> None:
    """Install HITL PreToolUse hooks into Claude Code settings."""

    if show:
        snippet: dict[str, Any] = {"hooks": {"PreToolUse": _HOOK_MATCHERS}}
        click.echo(json.dumps(snippet, indent=2))
        return

    path = _settings_path(global_)
    cfg = _load(path)

    if uninstall:
        cfg = _uninstall(cfg)
        action = "Uninstalled"
    else:
        cfg = _install(cfg)
        action = "Installed"

    if dry_run:
        click.echo(f"Would write to {path}:")
        click.echo(json.dumps(cfg, indent=2))
        return

    _save(path, cfg)
    scope = "global (~/.claude/)" if global_ else "project (.claude/)"
    click.echo(f"{action} HITL hooks in {scope}settings.json → {path}")

    if not uninstall:
        _print_next_steps(path, global_)


def _print_next_steps(path: Path, global_: bool) -> None:
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Ensure the HITL stack is running:")
    click.echo("       docker compose up -d")
    click.echo("  2. Build and load the browser extension (see extension/README.md)")
    click.echo("  3. Install the native messaging host:")
    click.echo("       node extension/src/signing-host/install.js")
    click.echo("  4. Set environment variables (or add to .env):")
    click.echo("       KEYCLOAK_HOST=http://localhost:8080")
    click.echo("       KEYCLOAK_CLI_CLIENT_ID=hitl-cli")
    click.echo("       KEYCLOAK_CLI_CLIENT_SECRET=<your-secret>")
    click.echo("  5. Test the hook:")
    click.echo("       echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rm /tmp/x\"}}' | hitl-hook")
    if not global_:
        click.echo(f"\n  Settings written to: {path}")
        click.echo("  Commit this file to share the hook config with your team.")
