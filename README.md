# HITL — Cryptographically Signed Human-in-the-Loop Permissions

Ensures that when an AI agent requests permission for a sensitive action, the approval is **cryptographically proven** to come from a verified human — not from the agent itself, an automation script, or a replay attack.

The same signing infrastructure works across every AI integration pattern: Python tools with decorators, Claude Code skills, MCP servers, and system-level agent hooks. You pick the pattern that fits your architecture; the cryptographic proof is identical in all cases.

## The Signing Infrastructure

All four integration patterns share the same underlying flow:

```
Any integration point
(tool / skill / MCP / hook)
         │
         │  POST /sign  {nonce, timestamp, action, tool_name}
         ▼
Native Messaging Host (localhost:7331)
         │  stdio NativeMessaging protocol
         ▼
Browser Extension (service worker)
         │  shows popup to user
         ▼
   User: Approve / Deny
         │
         │  Ed25519 sign(challenge)
         │  ← private key in SubtleCrypto, extractable:false
         ▼
{signature, access_token} returned to integration point
         │
         │  fetch ed25519_public_key from OAuth server Admin API
         ▼
Ed25519 verify(signature, challenge_bytes, public_key)
         │
         ▼
  APPROVED or DENIED — cryptographic proof
```

The agent **cannot forge** a valid signature. The private key lives only in the browser extension (never exportable, cleared when the browser closes). The OAuth server ensures only verified humans have registered keys.

## Four Integration Patterns

This repository demonstrates HITL across every major AI integration scenario. Each is independent — pick the one that matches how you build.

---

### Pattern 1 — HITL-enabled Tool (`tool/`)

**Scenario**: You own the tool code and want it to self-gate before executing dangerous operations.

```python
from hitl_tool.decorator import require_human_approval

@require_human_approval("Delete file: {kwargs[path]}")
async def delete_file(path: str) -> bool:
    os.remove(path)
    return True
```

The tool refuses to run without a valid human signature. Works in any Python codebase, any agent framework, any runtime — the check is inside the function, not outside it.

→ [`tool/README.md`](tool/README.md)

---

### Pattern 2 — HITL-enabled Skill (`skill/`)

**Scenario**: You're building Claude Code workflows and want the agent to be able to explicitly request approval as part of its reasoning.

```
/hitl-approve push the release branch to production
```

The skill blocks until the human approves or denies in the browser extension, then returns `HITL_APPROVED` / `HITL_DENIED` with exit code 0/1. The agent decides when to invoke it; the signing infrastructure ensures the response is genuine.

→ [`skill/README.md`](skill/README.md)

---

### Pattern 3 — HITL-enabled MCP Server (`mcp/`)

**Scenario**: You're building with MCP-compatible agents and want approval as a standard, discoverable tool in the agent's tool list.

```
Tool: request_approval
Input: {"action": "run database migration on prod"}
→ blocks until human signs → returns {approved: true, signature: "...", user_id: "..."}
```

Any MCP-compatible agent (Claude, others) can call `request_approval()` and `check_hitl_availability()` without any special SDK. Works in multi-agent systems where individual agents need to escalate decisions.

→ [`mcp/README.md`](mcp/README.md)

---

### Pattern 4 — HITL-enabled Agent Hook (`hooks/`)

**Scenario**: You want approval enforced at the session level — intercepting tool calls before they execute, regardless of which tools or agents are involved.

```
Claude Code session
    │  agent calls Bash("rm -rf /tmp/x")
    ▼
PreToolUse hook fires  ←  outside agent control
    │  classifies command as dangerous
    ▼
HITL signing flow → human approves/denies
    │
    ├─ exit 0  {"decision":"approve"}  →  tool executes
    └─ exit 1  {"decision":"block",...} →  tool is cancelled
```

The hook intercepts at the Claude Code harness level. Safe commands (`ls`, `git status`, `pytest`) bypass immediately with no popup. Only flagged commands (`rm -rf`, `sudo`, `git push`, `terraform apply`, …) require a signature.

→ [`hooks/README.md`](hooks/README.md)

---

## Combining Patterns

The patterns are orthogonal and compose naturally:

| Combination | Effect |
|-------------|--------|
| Tool decorator only | Tool self-gates; agent can still use other tools freely |
| MCP only | Agent can request approval; unchecked tools remain unchecked |
| Hook only | System-level policy on all Bash/Edit/Write without touching tool code |
| Tool + Hook | Two independent approval points — tool checks intent, hook checks execution |
| MCP + Hook | Agent-initiated approval for decisions, hook for unchecked side effects |
| All four | Maximum coverage across every layer of the AI stack |

A practical example: a team shipping an AI coding assistant deploys Pattern 3 (MCP) so the agent can ask "should I push this PR?" and Pattern 4 (hooks) so no `git push` ever runs without approval — even if the agent forgets to ask.

---

## Security Properties

| Property | How it's enforced |
|----------|-------------------|
| Only verified humans can approve | OAuth server realm — no bot/service accounts |
| Agent cannot self-approve | Private key never leaves the browser extension (`extractable:false`) |
| Key cleared on browser close | `chrome.storage.session` — in-memory only |
| Replay attacks prevented | Per-challenge nonce stored in Redis + timestamp TTL |
| Key bound to authenticated identity | Public key registered in OAuth server at login |
| Approval is action-specific | Challenge includes action description, nonce, timestamp |

### Known Limitations

- If the browser host OS is fully compromised (OS-level keylogger), the private key can be read at signing time
- If the OAuth server is compromised, public keys can be swapped
- The 5-minute TTL (configurable) requires the human to be present; long-running jobs need to re-request

---

## Repository Structure

```
hitl/
├── CLAUDE.md              # Agent/developer instructions
├── README.md              # This file
├── .env.example           # Environment variable template
├── docker-compose.yml     # OAuth server (Keycloak) + Redis
├── oauth/                 # OAuth server realm config + init scripts
├── extension/             # Browser extension (TypeScript, MV3, Chrome+Firefox)
├── cli/                   # Core signing library + demo CLI
├── tool/                  # Pattern 1: @require_human_approval decorator
├── skill/                 # Pattern 2: Claude Code /hitl-approve slash command
├── mcp/                   # Pattern 3: FastMCP server with request_approval tool
└── hooks/                 # Pattern 4: Claude Code PreToolUse hook enforcement
```

The `cli/` package is the shared foundation. `tool/`, `skill/`, `mcp/`, and `hooks/` all depend on it for challenge generation and signature verification.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) Python package manager
- Chrome 113+ or Firefox 115+

### 1. Start Infrastructure

```bash
cp .env.example .env
# Edit .env — at minimum set OAUTH_CLI_CLIENT_SECRET
docker compose up -d
```

The OAuth server starts at `http://localhost:8080`. The `hitl` realm is imported automatically.

### 2. Build & Load the Extension

```bash
cd extension && npm install && npm run build
```

**Chrome**: `chrome://extensions` → "Load unpacked" → select `extension/dist-chrome/`

**Firefox**: `about:debugging` → "Load Temporary Add-on" → select `extension/dist-firefox/manifest.json`

### 3. Install the Native Messaging Host

```bash
node extension/src/signing-host/install.js
```

This bridges HTTP requests from tools to the extension via the NativeMessaging stdio protocol.

### 4. Install Python Packages

```bash
uv pip install -e cli/ tool/ skill/ mcp/ hooks/
```

### 5. Log In via the Extension

Click the extension icon → "Login". Your Ed25519 keypair is generated in-browser and your public key is registered with the OAuth server.

### 6. Try Each Pattern

```bash
# Pattern 1 — tool self-gate
python -m hitl_tool.demo_tool

# Pattern 2 — skill (from a Claude Code session)
# /hitl-approve delete the old logs

# Pattern 3 — MCP (add to .claude/mcp_config.json, then start a session)
# Agent calls: request_approval(action="push release branch")

# Pattern 4 — hook enforcement
hitl-install                    # writes .claude/settings.json
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' | hitl-hook
```

### Bypassing hooks when needed

```bash
HITL_POLICY=disabled claude "explain this function"          # read-only session
HITL_UNAVAILABLE_POLICY=allow claude "run the tests"         # extension not running
hitl-install --uninstall                                     # remove hooks
```

---

## Package Documentation

| Package | Pattern | README |
|---------|---------|--------|
| `oauth/` | Infrastructure | [`oauth/README.md`](oauth/README.md) |
| `extension/` | Infrastructure | [`extension/README.md`](extension/README.md) |
| `cli/` | Shared library | [`cli/README.md`](cli/README.md) |
| `tool/` | Pattern 1 | [`tool/README.md`](tool/README.md) |
| `skill/` | Pattern 2 | [`skill/README.md`](skill/README.md) |
| `mcp/` | Pattern 3 | [`mcp/README.md`](mcp/README.md) |
| `hooks/` | Pattern 4 | [`hooks/README.md`](hooks/README.md) |

## Development

```bash
cd extension && npm test
cd cli && uv run pytest
cd tool && uv run pytest
cd mcp && uv run pytest
cd hooks && uv run pytest

cd extension && npm run lint
cd cli && uv run ruff check . && uv run mypy hitl_cli/
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
