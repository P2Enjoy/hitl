"""Write Claude Code PreToolUse hook configuration into settings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_HOOK_ENTRY: dict[str, Any] = {
    "type": "command",
    "command": "hitl-hook",
}

_HOOK_MATCHERS: list[dict[str, Any]] = [
    {"matcher": "Bash", "hooks": [_HOOK_ENTRY]},
    {"matcher": "Edit|Write|MultiEdit", "hooks": [_HOOK_ENTRY]},
]


def settings_path(global_: bool) -> Path:
    if global_:
        return Path.home() / ".claude" / "settings.json"
    return Path.cwd() / ".claude" / "settings.json"


def load(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            with path.open() as f:
                data: dict[str, Any] = json.load(f)
                return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save(path: Path, data: dict[str, Any]) -> None:
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


def install(cfg: dict[str, Any]) -> dict[str, Any]:
    hooks: dict[str, Any] = cfg.setdefault("hooks", {})
    pre: list[dict[str, Any]] = hooks.setdefault("PreToolUse", [])

    existing: dict[str, dict[str, Any]] = {
        entry["matcher"]: entry for entry in pre if "matcher" in entry
    }

    for block in _HOOK_MATCHERS:
        matcher = block["matcher"]
        if matcher in existing:
            hook_list: list[Any] = existing[matcher].setdefault("hooks", [])
            if not any(_is_hitl_hook(h) for h in hook_list):
                hook_list.append(_HOOK_ENTRY)
        else:
            pre.append({"matcher": matcher, "hooks": [_HOOK_ENTRY]})

    return cfg


def uninstall(cfg: dict[str, Any]) -> dict[str, Any]:
    pre: list[Any] = cfg.get("hooks", {}).get("PreToolUse", [])
    for block in pre:
        if isinstance(block, dict) and "hooks" in block:
            block["hooks"] = [h for h in block["hooks"] if not _is_hitl_hook(h)]
    cfg.get("hooks", {})["PreToolUse"] = [
        b for b in pre if isinstance(b, dict) and b.get("hooks")
    ]
    return cfg


def snippet() -> dict[str, Any]:
    return {"hooks": {"PreToolUse": _HOOK_MATCHERS}}
