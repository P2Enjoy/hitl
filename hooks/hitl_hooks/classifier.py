"""
Classify whether a Claude Code tool call requires HITL approval.

Returns one of:
    "bypass"  — definitively safe, skip HITL entirely (fast path)
    "require" — must get human approval before proceeding
    "allow"   — default allow (no pattern matched, policy is allow)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import load_config


def classify(tool_name: str, tool_input: dict[str, Any]) -> str:
    cfg = load_config()

    if cfg.get("policy") == "disabled":
        return "bypass"

    match tool_name:
        case "Bash":
            return _classify_bash(tool_input.get("command", ""), cfg)
        case "Write":
            return _classify_write(tool_input.get("file_path", ""), cfg)
        case "Edit" | "MultiEdit":
            return _classify_write(tool_input.get("file_path", ""), cfg)
        case _:
            return "bypass"


def _classify_bash(command: str, cfg: dict[str, Any]) -> str:
    bash_cfg: dict[str, Any] = cfg.get("bash", {})
    command = command.strip()

    # Fast bypass check — read-only / obviously safe commands
    for pattern in bash_cfg.get("bypass_patterns", []):
        if re.search(pattern, command, re.IGNORECASE | re.MULTILINE):
            return "bypass"

    # Require check — dangerous patterns
    for pattern in bash_cfg.get("require_patterns", []):
        if re.search(pattern, command, re.IGNORECASE | re.MULTILINE):
            return "require"

    default: str = bash_cfg.get("default", "allow")
    return default


def _classify_write(file_path: str, cfg: dict[str, Any]) -> str:
    write_cfg: dict[str, Any] = cfg.get("write", {})
    expanded = str(Path(file_path).expanduser())

    for prefix in write_cfg.get("require_paths", []):
        expanded_prefix = str(Path(prefix).expanduser())
        if expanded.startswith(expanded_prefix):
            return "require"

    default: str = write_cfg.get("default", "allow")
    return default


def format_action(tool_name: str, tool_input: dict[str, Any]) -> str:
    match tool_name:
        case "Bash":
            cmd = tool_input.get("command", "").strip()
            # Truncate long commands but keep them readable
            if len(cmd) > 200:
                cmd = cmd[:197] + "…"
            return f"Run: {cmd}"

        case "Write":
            path = tool_input.get("file_path", "?")
            content = tool_input.get("content", "")
            return f"Write {path} ({len(content):,} chars)"

        case "Edit":
            path = tool_input.get("file_path", "?")
            old = (tool_input.get("old_string", "") or "")[:60].replace("\n", "↵")
            return f"Edit {path}: replace '{old}{'…' if len(old) == 60 else ''}'"

        case "MultiEdit":
            path = tool_input.get("file_path", "?")
            edits = tool_input.get("edits", [])
            return f"MultiEdit {path} ({len(edits)} change{'s' if len(edits) != 1 else ''})"

        case _:
            return f"{tool_name}: {str(tool_input)[:120]}"
