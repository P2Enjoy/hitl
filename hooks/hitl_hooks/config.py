"""
Config loading for hitl-hooks.

Resolution order (later overrides earlier):
  1. Built-in defaults
  2. ~/.config/hitl/hooks.json    (user-level)
  3. .claude/hitl-hooks.json      (project-level, relative to cwd)
  4. Environment variables         (HITL_POLICY, HITL_UNAVAILABLE_POLICY)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DEFAULTS: dict[str, Any] = {
    # "enforce"  — block the tool call when extension is unavailable
    # "audit"    — allow through but print a warning (useful while onboarding)
    # "disabled" — disable HITL checks entirely (use only for testing)
    "policy": "enforce",

    # What to do when the signing extension is unreachable:
    # "block" — fail safe (recommended for production)
    # "allow" — fail open (useful during development when extension isn't running)
    "unavailable_policy": "block",

    "bash": {
        # Patterns (Python regex) that require HITL approval.
        # Checked in order; first match wins.
        "require_patterns": [
            r"rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+|--recursive|--force)",  # rm -rf / --recursive
            r"rm\s+/",                       # rm of absolute paths
            r"\bsudo\b",                     # any sudo
            r"\bsu\b\s",                     # su to another user
            r"git\s+push",                   # push to remote
            r"git\s+reset\s+--hard",         # destructive reset
            r"git\s+clean\s+-[a-zA-Z]*f",   # git clean -f
            r"git\s+branch\s+-[Dd]",         # delete branch
            r"curl\s+.*\|\s*(ba)?sh",        # curl | sh (supply-chain risk)
            r"wget\s+.*\|",                  # wget | anything
            r"\bdd\s+",                      # dd (disk operations)
            r"mkfs\.",                       # format filesystem
            r">(>?)\s*/",                    # redirect to absolute path
            r"\bchmod\s+[0-7]*7[0-7]*\b",   # world-writable chmod
            r"\bchown\s+-R\b",               # recursive chown
            r"\bpkill\b|\bkillall\b",        # kill processes by name
            r"\bdropdb\b|\bdropdatabase\b",  # drop database
            r"DROP\s+TABLE|DROP\s+DATABASE", # SQL drops
            r"\btruncate\b",                 # truncate file/table
            r"ssh\s+.*&&",                   # ssh with chained commands
            r"rsync\s+.*--delete",           # rsync --delete
            r"docker\s+(rm|rmi|system\s+prune)", # docker destructive ops
            r"kubectl\s+delete",             # k8s delete
            r"terraform\s+(destroy|apply)",  # infra changes
        ],
        # Patterns that are always safe — skip HITL entirely.
        # Checked before require_patterns; first match bypasses the check.
        "bypass_patterns": [
            r"^ls(\s|$)",
            r"^ll(\s|$)",
            r"^la(\s|$)",
            r"^cat\s+",
            r"^head\s+",
            r"^tail\s+",
            r"^less\s+",
            r"^more\s+",
            r"^echo\b",
            r"^printf\b",
            r"^pwd$",
            r"^whoami$",
            r"^id$",
            r"^date(\s|$)",
            r"^which\s+",
            r"^type\s+",
            r"^env(\s|$)",
            r"^printenv(\s|$)",
            r"^uname(\s|$)",
            r"^hostname(\s|$)",
            r"^git\s+(status|log|diff|show|branch|remote|fetch|stash\s+list|tag|describe)(\s|$)",
            r"^grep\b",
            r"^rg\b",
            r"^find\s+",
            r"^locate\s+",
            r"^wc\s+",
            r"^sort\b",
            r"^uniq\b",
            r"^awk\b",
            r"^sed\s+-n\b",            # sed -n (read-only)
            r"^python3?\s+-c\s+['\"]?print",  # python print
            r"^node\s+-e\s+['\"]?console\.log",
            r"^curl\s+-[a-zA-Z]*[Iss]",       # curl -I/-s (HEAD/silent, no pipe)
            r"^(uv\s+)?pip\s+(list|show|freeze|check)",
            r"^npm\s+(list|ls|info|view|outdated)",
            r"^cargo\s+(check|clippy|test|bench)",
            r"^go\s+(vet|test|build)(\s|$)",
            r"^pytest(\s|$)",
            r"^ruff\s+(check|format\s+--check)(\s|$)",
            r"^mypy\b",
        ],
        # What to do for commands matching neither list:
        # "allow" or "require"
        "default": "allow",
    },

    "write": {
        # File path prefixes that require HITL for Write/Edit/MultiEdit.
        "require_paths": [
            "/etc/",
            "/usr/",
            "/var/",
            "/opt/",
            "/boot/",
            "/sys/",
            "/proc/",
            "~/.ssh/",
            "~/.aws/",
            "~/.gnupg/",
            "~/.config/",
            "~/.bashrc",
            "~/.bash_profile",
            "~/.zshrc",
            "~/.profile",
        ],
        "default": "allow",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = dict(_DEFAULTS)

    for path in [
        Path.home() / ".config" / "hitl" / "hooks.json",
        Path.cwd() / ".claude" / "hitl-hooks.json",
    ]:
        if path.exists():
            try:
                with path.open() as f:
                    cfg = _deep_merge(cfg, json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    # Environment variable overrides
    if policy := os.getenv("HITL_POLICY"):
        cfg["policy"] = policy
    if unavail := os.getenv("HITL_UNAVAILABLE_POLICY"):
        cfg["unavailable_policy"] = unavail

    return cfg
