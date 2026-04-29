"""
Claude Code skill entry point.

Outputs HITL_APPROVED or HITL_DENIED on stdout.
Exits 0 on approval, 1 on denial or error.
"""

import asyncio
import sys

import click
from dotenv import load_dotenv

from hitl import HitlClient, HitlDenied, HitlExtensionUnavailable, HitlVerificationError

load_dotenv()


@click.command()
@click.option("--action", required=True, help="Action requiring approval")
@click.option("--tool-name", default="claude-code-skill", help="Name of the requesting tool/skill")
def main(action: str, tool_name: str) -> None:
    """Request cryptographically verified human approval."""
    approved = asyncio.run(_run(action, tool_name))
    if approved:
        click.echo("HITL_APPROVED")
        sys.exit(0)
    else:
        click.echo("HITL_DENIED")
        sys.exit(1)


async def _run(action: str, tool_name: str) -> bool:
    client = HitlClient.from_env()
    try:
        await client.request_approval(action, tool_name=tool_name)
        return True
    except HitlExtensionUnavailable as exc:
        click.echo(f"HITL_ERROR: {exc}", err=True)
        return False
    except HitlDenied:
        return False
    except HitlVerificationError as exc:
        click.echo(f"HITL_ERROR: verification failed — {exc}", err=True)
        return False
    except Exception as exc:
        click.echo(f"HITL_ERROR: {exc}", err=True)
        return False


if __name__ == "__main__":
    main()
