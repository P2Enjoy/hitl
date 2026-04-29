"""
hitl-hook — Claude Code PreToolUse hook entry point.

Claude Code invokes this before every matched tool call, passing a JSON
payload on stdin. We output a JSON decision on stdout and exit 0 (approve)
or 1 (block).

Stdin JSON (from Claude Code):
    {
      "session_id": "...",
      "transcript_path": "...",
      "hook_event_name": "PreToolUse",
      "tool_name": "Bash",
      "tool_input": { "command": "rm -rf /tmp/x" }
    }

Stdout JSON (read by Claude Code):
    {"decision": "approve"}
    {"decision": "block", "reason": "Human denied via HITL"}

Exit code:
    0 — approve (proceed with tool call)
    1 — block   (abort tool call, show reason to agent)
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _out(decision: str, reason: str | None = None) -> None:
    payload: dict[str, str] = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload), flush=True)


def main() -> None:
    raw = sys.stdin.read()

    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        # Can't parse Claude Code's input — fail safe
        _out("block", f"hitl-hook: could not parse tool input JSON: {exc}")
        sys.exit(1)

    tool_name: str = payload.get("tool_name", "")
    tool_input: dict[str, Any] = payload.get("tool_input", {})

    # Lazy imports so the fast-path bypass exits before loading async stack
    from .classifier import classify, format_action
    from .config import load_config

    cfg = load_config()

    if cfg.get("policy") == "disabled":
        _out("approve")
        sys.exit(0)

    verdict = classify(tool_name, tool_input)

    if verdict in ("bypass", "allow"):
        _out("approve")
        sys.exit(0)

    # verdict == "require" — invoke the HITL signing flow
    action = format_action(tool_name, tool_input)
    approved = asyncio.run(_run_hitl(action, tool_name, cfg))

    if approved:
        _out("approve")
        sys.exit(0)
    else:
        _out("block", f"HITL: human denied — {action}")
        sys.exit(1)


async def _run_hitl(action: str, tool_name: str, cfg: dict[str, Any]) -> bool:
    from hitl import HitlClient, HitlDenied, HitlExtensionUnavailable, HitlVerificationError, HitlTimeout

    unavail_policy: str = cfg.get("unavailable_policy", "block")

    try:
        client = HitlClient.from_env()
        await client.request_approval(action, tool_name=f"claude-code:{tool_name}")
        return True
    except HitlExtensionUnavailable:
        if unavail_policy == "allow":
            print(
                "hitl-hook WARNING: signing extension not reachable — "
                "allowing through (unavailable_policy=allow)",
                file=sys.stderr,
            )
            return True
        print(
            "hitl-hook: signing extension not reachable — "
            "blocking tool call (unavailable_policy=block)\n"
            "Start the browser extension and native messaging host, or set "
            "HITL_UNAVAILABLE_POLICY=allow to bypass.",
            file=sys.stderr,
        )
        return False
    except HitlDenied:
        return False
    except HitlTimeout as exc:
        print(f"hitl-hook: timed out waiting for approval — {exc}", file=sys.stderr)
        return False
    except HitlVerificationError as exc:
        print(f"hitl-hook: verification failed — {exc}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"hitl-hook: unexpected error — {exc}", file=sys.stderr)
        return False
