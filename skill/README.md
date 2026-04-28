# skill/ — Pattern 2: HITL-enabled Skill

**Use this pattern when**: you're building Claude Code workflows and want the agent to be able to explicitly request approval as part of its own reasoning — "before I do X, let me check with the human."

The agent decides when to invoke `/hitl-approve`. This is intentional: the skill is for scenarios where the agent has enough context to know it needs a human decision, and you want that check to be first-class in the agent's reasoning trace rather than invisible infrastructure.

For other HITL integration patterns see the [root README](../README.md).

---

A Claude Code skill (`/hitl-approve`) that an AI agent can invoke to request cryptographically verified human approval before proceeding with a sensitive action.

## Installation

```bash
uv pip install -e skill/
```

Copy `.claude/commands/hitl-approve.md` into your project's `.claude/commands/` directory, or use it from here by adding this repo to Claude Code's project context.

## Usage

In Claude Code, invoke the skill with:

```
/hitl-approve delete all logs older than 30 days
```

The skill blocks until the user approves or denies in the browser extension popup, then outputs:
- `HITL_APPROVED` (exit code 0) — safe to proceed
- `HITL_DENIED` (exit code 1) — abort the operation

## CLI

```bash
hitl-approve --action "push to production"
echo $?  # 0 = approved, 1 = denied
```

## Agent Integration Pattern

```python
# In an agent tool that needs HITL gating:
import subprocess

result = subprocess.run(
    ["hitl-approve", "--action", f"run: {command}"],
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    raise PermissionError("Action not approved by human")
# proceed...
```

## Environment Variables

Inherits from `hitl-cli` — see `cli/README.md`.
