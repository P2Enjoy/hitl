"""
hitl-setup — one-stop setup CLI for the HITL infrastructure.

Commands:
    hitl-setup infra          Start OAuth server + Redis via Docker Compose
    hitl-setup infra stop     Stop the stack
    hitl-setup infra status   Show container status
    hitl-setup hooks          Install Claude Code PreToolUse hooks
    hitl-setup hooks --show   Print hook snippet without writing
    hitl-setup host           Install the native messaging host
    hitl-setup all            Run infra + hooks + host in sequence
    hitl-setup status         Check what's running and configured
"""

from __future__ import annotations

import asyncio
import json
import sys

import click

from . import _docker, _hooks, _host
from ..challenge import check_extension_availability


# ── infra ─────────────────────────────────────────────────────────────────────

@click.group("infra")
def infra_group() -> None:
    """Manage OAuth server + Redis infrastructure via Docker Compose."""


@infra_group.command("start")
@click.option("--foreground", is_flag=True, help="Run in foreground (no -d)")
def infra_start(foreground: bool) -> None:
    """Start OAuth server and Redis."""
    rc = _docker.start(detach=not foreground)
    sys.exit(rc)


@infra_group.command("stop")
def infra_stop() -> None:
    """Stop the HITL infrastructure containers."""
    sys.exit(_docker.stop())


@infra_group.command("status")
def infra_status() -> None:
    """Show container status."""
    sys.exit(_docker.status())


@infra_group.command("logs")
@click.argument("service", required=False)
def infra_logs(service: str | None) -> None:
    """Tail logs from the stack (or a specific service)."""
    sys.exit(_docker.logs(service))


# ── hooks ─────────────────────────────────────────────────────────────────────

@click.command("hooks")
@click.option("--global", "global_", is_flag=True, help="Write to ~/.claude/settings.json")
@click.option("--show", is_flag=True, help="Print snippet without writing")
@click.option("--uninstall", is_flag=True, help="Remove HITL hooks")
@click.option("--dry-run", is_flag=True, help="Show what would be written")
def hooks_cmd(global_: bool, show: bool, uninstall: bool, dry_run: bool) -> None:
    """Install Claude Code PreToolUse hooks."""
    if show:
        click.echo(json.dumps(_hooks.snippet(), indent=2))
        return

    path = _hooks.settings_path(global_)
    cfg = _hooks.load(path)

    if uninstall:
        cfg = _hooks.uninstall(cfg)
        action = "Uninstalled"
    else:
        cfg = _hooks.install(cfg)
        action = "Installed"

    if dry_run:
        click.echo(f"Would write to {path}:")
        click.echo(json.dumps(cfg, indent=2))
        return

    _hooks.save(path, cfg)
    scope = "global (~/.claude/)" if global_ else "project (.claude/)"
    click.echo(f"{action} HITL hooks in {scope}settings.json → {path}")


# ── host ──────────────────────────────────────────────────────────────────────

@click.command("host")
@click.option("--browser", default="chrome", type=click.Choice(["chrome", "firefox"]),
              help="Target browser for native messaging host manifest")
@click.option("--host-script", default=None, type=click.Path(exists=True),
              help="Path to signing-host/index.js (auto-detected if omitted)")
def host_cmd(browser: str, host_script: str | None) -> None:
    """Install the native messaging host for the browser extension."""
    from pathlib import Path

    script = Path(host_script) if host_script else None
    rc = _host.install(browser=browser, host_script=script)
    if rc == 0:
        click.echo(f"Native messaging host installed for {browser}.")
        click.echo("If you haven't yet, load the extension and click Login.")
    sys.exit(rc)


# ── status ────────────────────────────────────────────────────────────────────

@click.command("status")
def status_cmd() -> None:
    """Check HITL infrastructure and extension availability."""
    import os

    click.echo("HITL status\n" + "─" * 40)

    # Docker
    import subprocess
    import shutil

    if shutil.which("docker"):
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            click.echo("  Infrastructure: running")
        else:
            click.echo("  Infrastructure: not running  (run: hitl-setup infra)")
    else:
        click.echo("  Infrastructure: docker not found")

    # Extension
    available = asyncio.run(check_extension_availability())
    if available:
        click.echo("  Extension:      reachable on port 7331")
    else:
        click.echo("  Extension:      not reachable  (load extension + install host)")

    # Hooks
    project_hooks = _hooks.settings_path(global_=False)
    global_hooks = _hooks.settings_path(global_=True)

    def _has_hooks(path: "Path") -> bool:  # type: ignore[name-defined]
        from pathlib import Path as P
        cfg = _hooks.load(P(str(path)))
        pre = cfg.get("hooks", {}).get("PreToolUse", [])
        return any(
            h.get("command") == "hitl-hook"
            for block in pre if isinstance(block, dict)
            for h in block.get("hooks", [])
            if isinstance(h, dict)
        )

    if _has_hooks(project_hooks):
        click.echo(f"  Hooks:          project-level installed ({project_hooks})")
    elif _has_hooks(global_hooks):
        click.echo(f"  Hooks:          global installed ({global_hooks})")
    else:
        click.echo("  Hooks:          not installed  (run: hitl-setup hooks)")

    # Env vars — accept either OAUTH_* (new) or KEYCLOAK_* (legacy)
    pairs = [
        ("OAUTH_SERVER_URL", "KEYCLOAK_HOST"),
        ("OAUTH_CLI_CLIENT_ID", "KEYCLOAK_CLI_CLIENT_ID"),
        ("OAUTH_CLI_CLIENT_SECRET", "KEYCLOAK_CLI_CLIENT_SECRET"),
    ]
    missing = [new for new, old in pairs if not os.environ.get(new) and not os.environ.get(old)]
    if missing:
        click.echo(f"  Env vars:       missing: {', '.join(missing)}")
    else:
        click.echo("  Env vars:       all required vars set")


# ── all ───────────────────────────────────────────────────────────────────────

@click.command("all")
@click.option("--global", "global_", is_flag=True, help="Install hooks globally")
@click.option("--browser", default="chrome", type=click.Choice(["chrome", "firefox"]))
def all_cmd(global_: bool, browser: str) -> None:
    """Run infra start + hooks install + host install in sequence."""
    click.echo("==> Starting infrastructure...")
    rc = _docker.start(detach=True)
    if rc != 0:
        click.echo("Warning: docker compose start failed; continuing.", err=True)

    click.echo("\n==> Installing Claude Code hooks...")
    path = _hooks.settings_path(global_)
    cfg = _hooks.load(path)
    cfg = _hooks.install(cfg)
    _hooks.save(path, cfg)
    scope = "global" if global_ else "project"
    click.echo(f"  Hooks installed ({scope}): {path}")

    click.echo("\n==> Installing native messaging host...")
    rc = _host.install(browser=browser)
    if rc != 0:
        click.echo("  Warning: host install failed (build extension first).", err=True)

    click.echo("\nDone. Next:")
    click.echo("  1. Load extension/dist-chrome/ in Chrome (developer mode)")
    click.echo("  2. Click the extension icon → Login")
    click.echo("  3. Set OAUTH_SERVER_URL, OAUTH_CLI_CLIENT_ID, OAUTH_CLI_CLIENT_SECRET in .env")


# ── root group ────────────────────────────────────────────────────────────────

@click.group()
def main() -> None:
    """HITL setup — configure signing infrastructure, hooks, and native host."""


main.add_command(infra_group, name="infra")
main.add_command(hooks_cmd, name="hooks")
main.add_command(host_cmd, name="host")
main.add_command(status_cmd, name="status")
main.add_command(all_cmd, name="all")
