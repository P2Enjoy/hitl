"""
Claude Code skill entry point.

Outputs HITL_APPROVED or HITL_DENIED on stdout.
Exits 0 on approval, 1 on denial or error.
"""

import asyncio
import sys

import click
from dotenv import load_dotenv

from hitl_cli.challenge import check_extension_availability, generate_challenge, request_signature
from hitl_cli.keycloak_client import KeycloakClient
from hitl_cli.models import SignedResponse
from hitl_cli.verifier import verify_signed_response

load_dotenv()


@click.command()
@click.option("--action", required=True, help="Action requiring approval")
@click.option("--tool-name", default="claude-code-skill", help="Name of the requesting tool/skill")
@click.option(
    "--skip-verify",
    is_flag=True,
    default=False,
    help="Skip Keycloak verification (dev/test only)",
    hidden=True,
)
def main(action: str, tool_name: str, skip_verify: bool) -> None:
    """Request cryptographically verified human approval."""
    approved = asyncio.run(_run(action, tool_name, skip_verify))
    if approved:
        click.echo("HITL_APPROVED")
        sys.exit(0)
    else:
        click.echo("HITL_DENIED")
        sys.exit(1)


async def _run(action: str, tool_name: str, skip_verify: bool) -> bool:
    if not await check_extension_availability():
        click.echo(
            "HITL_ERROR: signing host not reachable — "
            "ensure the browser extension and native messaging host are running",
            err=True,
        )
        return False

    challenge = generate_challenge(action, tool_name)

    try:
        response = await request_signature(challenge)
    except Exception as exc:
        click.echo(f"HITL_ERROR: failed to get signature — {exc}", err=True)
        return False

    if isinstance(response, dict) and response.get("denied"):
        return False

    if not isinstance(response, SignedResponse):
        click.echo(f"HITL_ERROR: unexpected response — {response!r}", err=True)
        return False

    if skip_verify:
        return True

    keycloak = KeycloakClient.from_env()
    try:
        return await verify_signed_response(challenge, response, keycloak)
    except ValueError as exc:
        click.echo(f"HITL_ERROR: verification failed — {exc}", err=True)
        return False


if __name__ == "__main__":
    main()
