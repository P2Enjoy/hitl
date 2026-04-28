import asyncio
import os
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .challenge import check_extension_availability, generate_challenge, request_signature
from .keycloak_client import KeycloakClient
from .models import SignedResponse
from .verifier import verify_signed_response

load_dotenv()
console = Console()


@click.group()
def cli() -> None:
    """HITL — cryptographically signed human-in-the-loop permission system."""


@cli.command()
@click.option("--action", required=True, help="Description of the action requiring approval")
@click.option("--tool", "tool_name", default="hitl-cli", help="Requesting tool name")
@click.option("--skip-verify", is_flag=True, default=False, help="Skip Keycloak signature verification (dev only)")
def request(action: str, tool_name: str, skip_verify: bool) -> None:
    """Request cryptographically verified human approval for an action."""
    asyncio.run(_request(action, tool_name, skip_verify))


async def _request(action: str, tool_name: str, skip_verify: bool) -> None:
    # Pre-flight: check extension is running
    available = await check_extension_availability()
    if not available:
        console.print(
            "[red]Error:[/red] HITL signing host not reachable at "
            f"http://127.0.0.1:{os.getenv('EXTENSION_SIGNING_PORT', '7331')}/health\n"
            "Make sure the browser extension is loaded and the native messaging host is running.\n"
            "See extension/README.md for setup instructions."
        )
        sys.exit(2)

    challenge = generate_challenge(action, tool_name)

    console.print(
        Panel.fit(
            f"[bold yellow]{action}[/bold yellow]",
            title="[bold]Approval Requested[/bold]",
            subtitle=f"Tool: {tool_name} | Nonce: {challenge.nonce[:12]}…",
        )
    )
    console.print("[dim]Waiting for response in browser extension popup…[/dim]")

    with console.status(""):
        response = await request_signature(challenge)

    if isinstance(response, dict) and response.get("denied"):
        console.print("\n[red bold]DENIED[/red bold] — user denied the request")
        sys.exit(1)

    if not isinstance(response, SignedResponse):
        console.print(f"\n[red]Unexpected response:[/red] {response}")
        sys.exit(1)

    if skip_verify:
        console.print("\n[yellow]SKIPPED VERIFICATION[/yellow] (--skip-verify flag set)")
        sys.exit(0)

    keycloak = KeycloakClient.from_env()
    try:
        approved = await verify_signed_response(challenge, response, keycloak)
    except ValueError as exc:
        console.print(f"\n[red bold]VERIFICATION FAILED[/red bold] — {exc}")
        sys.exit(1)

    if approved:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[green]Status[/green]", "[green bold]APPROVED[/green bold]")
        table.add_row("[dim]User ID[/dim]", response.user_id)
        table.add_row("[dim]Signature[/dim]", response.signature[:32] + "…")
        console.print("\n", table)
        sys.exit(0)
    else:
        console.print("\n[red bold]INVALID SIGNATURE[/red bold] — verification failed")
        sys.exit(1)


@cli.command()
def health() -> None:
    """Check whether the HITL signing extension is reachable."""
    async def _check() -> None:
        available = await check_extension_availability()
        if available:
            console.print("[green]OK[/green] — signing host is reachable")
        else:
            console.print("[red]UNREACHABLE[/red] — signing host is not running")
            sys.exit(1)

    asyncio.run(_check())
