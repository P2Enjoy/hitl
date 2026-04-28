# HITL — Cryptographically Signed Human-in-the-Loop Permissions

Ensures that when an AI agent requests permission for a sensitive action, the approval is **cryptographically proven** to come from a verified human — not from the agent itself, an automation script, or a replay attack.

## The Problem

AI agents operating autonomously can self-approve their own tool actions. Even "human-in-the-loop" systems that prompt for approval can be bypassed if the approval check happens within the agent's own process. There's no cryptographic proof that a human actually responded.

## The Solution

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Trust Chain                                  │
│                                                                     │
│  Keycloak OAuth ──► verified human accounts only                    │
│        │                                                            │
│        ▼                                                            │
│  Browser Extension ──► holds Ed25519 keypair in memory             │
│  (chrome.storage.session, extractable:false)                        │
│        │                                                            │
│        ▼                                                            │
│  User clicks Approve ──► extension signs the challenge              │
│        │                                                            │
│        ▼                                                            │
│  Tool verifies signature against Keycloak-registered public key     │
│        │                                                            │
│        ▼                                                            │
│  APPROVED — cryptographic proof that a registered human responded   │
└─────────────────────────────────────────────────────────────────────┘
```

The agent **cannot forge** a valid signature. Only the browser extension, which holds the private key (never extractable, cleared on browser close), can sign challenges.

## Architecture

```
Tool/CLI/MCP/Skill
      │
      │  POST /sign {challenge}
      ▼
Native Messaging Host (localhost:7331)
      │
      │  NativeMessaging stdio protocol
      ▼
Extension Background Service Worker
      │
      │  Show popup to user
      ▼
User: Approve / Deny
      │
      │  Ed25519 sign(challenge)  ← private key stays in SubtleCrypto
      ▼
Extension → NativeHost → Tool
                              │
                              │  GET /admin/realms/hitl/users/{id}
                              ▼
                         Keycloak Admin API
                              │
                              │  returns ed25519_public_key attribute
                              ▼
                         Tool verifies signature
                              │
                              ▼
                         APPROVED or DENIED
```

## Security Properties

| Property | How it's enforced |
|----------|-------------------|
| Only verified humans can approve | Keycloak realm — no bot/service accounts allowed |
| Agent cannot self-approve | Private key never leaves the browser extension (`extractable:false`) |
| Key cleared when browser closes | `chrome.storage.session` — in-memory only |
| Replay attacks prevented | Per-challenge nonce tracked in Redis + timestamp TTL |
| Key bound to authenticated user | Public key registered in Keycloak at OAuth login |
| Approval is action-specific | Challenge includes the action description, nonce, timestamp |

### Known Limitations

- If the browser host OS is fully compromised (OS-level keylogger), the private key can be captured at signing time
- If Keycloak is compromised, public keys can be swapped
- The 5-minute TTL (configurable) means the human must be present; long-running agents need to re-request

## Repository Structure

```
hitl/
├── CLAUDE.md              # Agent/developer instructions
├── README.md              # This file
├── .env.example           # Environment variable template
├── docker-compose.yml     # Keycloak + Redis
├── oauth/                 # Keycloak realm config + init scripts
├── extension/             # Browser extension (TypeScript, MV3, Chrome+Firefox)
├── cli/                   # Demo CLI: hitl request --action "..."
├── tool/                  # @require_human_approval decorator demo
├── skill/                 # Claude Code /hitl-approve slash command
└── mcp/                   # FastMCP server with request_approval tool
```

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
# Edit .env if needed (defaults work for local dev)
docker compose up -d
```

Keycloak will be available at `http://localhost:8080`. The realm `hitl` is imported automatically on first start.

### 2. Build & Load the Extension

```bash
cd extension
npm install
npm run build
```

**Chrome**: Go to `chrome://extensions` → Enable "Developer mode" → "Load unpacked" → select `extension/dist-chrome/`

**Firefox**: Go to `about:debugging` → "This Firefox" → "Load Temporary Add-on" → select `extension/dist-firefox/manifest.json`

### 3. Register Native Messaging Host

```bash
cd extension
node signing-host/install.js
```

This installs the native messaging host manifest so the extension can communicate with the local HTTP relay.

### 4. Install Python Packages

```bash
cd /path/to/hitl
uv pip install -e cli/ tool/ skill/ mcp/
```

### 5. Log In via the Extension

Click the extension icon in the browser toolbar → "Login with Keycloak" → register with a Keycloak account. Your Ed25519 keypair is generated and your public key is stored in Keycloak.

### 6. Test the Golden Path

```bash
hitl request --action "delete /tmp/testfile"
```

A popup appears in the browser. Click **Approve**. The terminal prints:

```
APPROVED — signature verified
User: alice@example.com
Challenge: a3f1b2... (nonce truncated)
```

## Package Documentation

- [`oauth/README.md`](oauth/README.md) — Keycloak setup and configuration
- [`extension/README.md`](extension/README.md) — Browser extension development
- [`cli/README.md`](cli/README.md) — CLI usage and integration API
- [`tool/README.md`](tool/README.md) — `@require_human_approval` decorator
- [`skill/README.md`](skill/README.md) — Claude Code skill usage
- [`mcp/README.md`](mcp/README.md) — MCP server configuration

## Development

```bash
# Run all tests
cd extension && npm test
cd cli && uv run pytest
cd tool && uv run pytest
cd mcp && uv run pytest

# Lint
cd extension && npm run lint
cd cli && uv run ruff check . && uv run mypy hitl_cli/
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
