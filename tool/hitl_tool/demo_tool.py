"""
Demo tool: three representative dangerous operations guarded by HITL.
Run via:  python -m hitl_tool.demo_tool
"""

import asyncio
import os
import subprocess
import sys

from rich.console import Console

from .decorator import require_human_approval
from .exceptions import HitlDenied, HitlExtensionUnavailable, HitlTimeout, HitlVerificationError

console = Console()


@require_human_approval("Delete file: {kwargs[path]}")
async def delete_file(path: str) -> bool:
    """Permanently delete a file after HITL approval."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    os.remove(path)
    return True


@require_human_approval("Execute shell command: {kwargs[command]}")
async def execute_shell(command: str, cwd: str | None = None) -> tuple[int, str, str]:
    """Run a shell command after HITL approval. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


@require_human_approval("Send email to {kwargs[to]}: {kwargs[subject]}")
async def send_email(to: str, subject: str, body: str) -> bool:
    """Simulate sending an email after HITL approval (prints instead of sending)."""
    console.print(f"[dim]→ Simulated email to {to!r}: {subject!r}[/dim]")
    return True


async def _demo() -> None:
    console.print("[bold]HITL Demo Tool[/bold]")
    console.print("Each operation below requires your approval in the browser extension.\n")

    # Demo 1: file deletion
    demo_path = "/tmp/hitl-demo-file.txt"
    with open(demo_path, "w") as f:
        f.write("demo content\n")

    try:
        console.print(f"[1] Requesting approval to delete: {demo_path}")
        await delete_file(path=demo_path)
        console.print("[green]File deleted successfully.[/green]\n")
    except HitlDenied:
        console.print("[yellow]Denied — file not deleted.[/yellow]\n")
    except (HitlTimeout, HitlVerificationError, HitlExtensionUnavailable) as exc:
        console.print(f"[red]Error: {exc}[/red]\n")
        sys.exit(1)

    # Demo 2: shell command
    try:
        console.print("[2] Requesting approval to run: echo 'hello from HITL'")
        rc, out, err = await execute_shell(command="echo 'hello from HITL'")
        console.print(f"[green]Command output:[/green] {out.strip()}\n")
    except HitlDenied:
        console.print("[yellow]Denied — command not executed.[/yellow]\n")
    except (HitlTimeout, HitlVerificationError, HitlExtensionUnavailable) as exc:
        console.print(f"[red]Error: {exc}[/red]\n")

    # Demo 3: send email
    try:
        console.print("[3] Requesting approval to send email")
        await send_email(to="ops@example.com", subject="Deploy complete", body="Deploy finished.")
        console.print("[green]Email sent (simulated).[/green]\n")
    except HitlDenied:
        console.print("[yellow]Denied — email not sent.[/yellow]\n")
    except (HitlTimeout, HitlVerificationError, HitlExtensionUnavailable) as exc:
        console.print(f"[red]Error: {exc}[/red]\n")


if __name__ == "__main__":
    asyncio.run(_demo())
