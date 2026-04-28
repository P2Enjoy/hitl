# mcp/ — HITL MCP Server

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
        "KEYCLOAK_HOST": "http://localhost:8080",
        "KEYCLOAK_REALM": "hitl",
        "KEYCLOAK_CLI_CLIENT_ID": "hitl-cli",
        "KEYCLOAK_CLI_CLIENT_SECRET": "your-secret"
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
