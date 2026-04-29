# mcp/ — Pattern 3: HITL-enabled MCP Server

**Use this pattern when**: you're building with MCP-compatible agents and want human approval available as a standard, discoverable tool — one the agent can call like any other capability without any special SDK or integration code.

This is particularly useful in multi-agent systems where individual agents need to escalate decisions upward, or in any architecture where the agent framework speaks MCP natively and you want HITL to be a first-class tool in its tool list.

For other HITL integration patterns see the [root README](../README.md).

---

FastMCP server that exposes HITL verification as MCP tools, usable by any MCP-compatible agent (Claude, etc.).

## Installation

```bash
uv pip install -e mcp/
```

## Tools

### `request_approval(action, tool_name?)`

Blocks until the user approves or denies the action in the browser extension popup.

```
Input:
  action:    string  — human-readable action description (required)
  tool_name: string  — name of the requesting tool (default: "mcp-tool")

Output: ApprovalResult
  approved:      bool
  challenge_id:  string  — nonce for audit trail
  user_id:       string | null  — Keycloak sub if approved
  signature:     string | null  — base64url Ed25519 signature if approved
  timestamp:     int
  reason:        string | null  — denial/error reason if not approved
```

### `check_hitl_availability()`

Quick check that the signing extension is reachable.

```
Output: AvailabilityStatus
  available: bool
  message:   string
```

## Configuration

### stdio (default, for Claude Code)

Add to your Claude MCP config (`~/.claude/mcp_config.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "hitl": {
      "command": "hitl-mcp",
      "env": {
        "OAUTH_SERVER_URL": "http://localhost:8080",
        "OAUTH_REALM": "hitl",
        "OAUTH_CLI_CLIENT_ID": "hitl-cli",
        "OAUTH_CLI_CLIENT_SECRET": "your-secret"
      }
    }
  }
}
```

See `mcp_config.json` for a full template.

### SSE transport

```bash
MCP_TRANSPORT=sse MCP_SERVER_PORT=8008 hitl-mcp
```

## Tests

```bash
cd mcp && uv run pytest
```
