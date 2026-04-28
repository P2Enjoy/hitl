# hooks/ — Pattern 4: HITL-enabled Agent Hook

**Use case**: you want human approval enforced at the Claude Code session level, regardless of which tools the agent calls and without modifying any tool code.

This is one of four HITL integration patterns — see the [root README](../README.md) for the full picture. Unlike the tool decorator, skill, and MCP patterns (which are triggered from inside the agent's decision loop), hooks fire at the harness level before the agent ever sees a tool result.

## How it works

Claude Code fires `PreToolUse` hooks before executing any tool. The hook:
1. Receives the tool name and input as JSON on stdin
2. Classifies whether the call needs approval (fast path for safe commands)
3. If yes: sends a challenge to the browser extension, blocks until the user approves or denies
4. Outputs `{"decision": "approve"}` or `{"decision": "block", "reason": "..."}` on stdout
5. Exits `0` (approve) or `1` (block)

The agent never executes the blocked tool. It sees the denial reason and must abort or ask the user directly.

## Installation

### 1. Install the package

```bash
uv pip install -e hooks/
```

### 2. Run the installer

```bash
# Project-level (recommended — commit .claude/settings.json to share with your team)
hitl-install

# User-level (applies to all your Claude Code sessions)
hitl-install --global

# Preview without writing
hitl-install --show
hitl-install --dry-run
```

The installer writes into `.claude/settings.json` (or `~/.claude/settings.json`), merging with any existing configuration.

### 3. Verify

```bash
# Should block (dangerous command):
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' | hitl-hook
# → {"decision":"block","reason":"HITL: human denied — Run: rm -rf /tmp/test"}
# exit code 1

# Should approve immediately (safe command):
echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' | hitl-hook
# → {"decision":"approve"}
# exit code 0
```

### 4. Ensure the HITL stack is running

```bash
docker compose up -d
# Load the browser extension (see extension/README.md)
node extension/src/signing-host/install.js
```

## What gets intercepted

| Tool | Condition | Example |
|------|-----------|---------|
| `Bash` | Matches a dangerous pattern | `rm -rf`, `sudo`, `git push`, `terraform apply` |
| `Bash` | Safe pattern match | `ls`, `git status`, `pytest` → bypass (no popup) |
| `Write` | File in sensitive path | `/etc/`, `~/.ssh/` |
| `Edit` | File in sensitive path | `/etc/`, `~/.ssh/` |
| `MultiEdit` | File in sensitive path | `/etc/`, `~/.ssh/` |
| `Read` | Any | Always bypassed (read-only) |

## Configuration

### Environment variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `HITL_POLICY` | `enforce`, `audit`, `disabled` | `enforce` | Main policy |
| `HITL_UNAVAILABLE_POLICY` | `block`, `allow` | `block` | When extension is unreachable |

### Config file

Copy `install/hitl-hooks-example.json` to `.claude/hitl-hooks.json` to customise patterns:

```bash
cp hooks/install/hitl-hooks-example.json .claude/hitl-hooks.json
```

Key settings:

```json
{
  "policy": "enforce",
  "unavailable_policy": "block",
  "bash": {
    "require_patterns": ["..."],
    "bypass_patterns": ["..."],
    "default": "allow"
  },
  "write": {
    "require_paths": ["/etc/", "~/.ssh/"],
    "default": "allow"
  }
}
```

### Development mode

When the extension isn't running (e.g. during CI), set `HITL_UNAVAILABLE_POLICY=allow` to fail open:

```bash
HITL_UNAVAILABLE_POLICY=allow claude "run the tests"
```

Or set `HITL_POLICY=disabled` to turn off hooks entirely:

```bash
HITL_POLICY=disabled claude "fix the typo in README"
```

## Uninstall

```bash
hitl-install --uninstall          # project-level
hitl-install --uninstall --global # user-level
```

## Tests

```bash
cd hooks && uv run pytest
```
