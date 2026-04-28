# HITL Monorepo — Agent Instructions

## Project Purpose

Cryptographically signed human-in-the-loop (HITL) permission system. When an AI tool requests approval for a sensitive action, the response is Ed25519-signed by the user's browser extension and verified against a public key stored in Keycloak. The agent can never forge a valid signature.

## Package Map

| Package | Language | Description |
|---------|----------|-------------|
| `oauth/` | Bash/JSON | Keycloak 24 realm config + init scripts |
| `extension/` | TypeScript/MV3 | Browser extension — keypair holder and signer |
| `cli/` | Python 3.11 | Shared signing library + demo CLI |
| `tool/` | Python 3.11 | **Pattern 1**: `@require_human_approval` decorator |
| `skill/` | Python 3.11 | **Pattern 2**: Claude Code `/hitl-approve` slash command |
| `mcp/` | Python 3.11 | **Pattern 3**: FastMCP server with `request_approval` tool |
| `hooks/` | Python 3.11 | **Pattern 4**: Claude Code `PreToolUse` hook enforcement |

## Four Integration Patterns

HITL works across every AI integration scenario. Each pattern is independent and addresses a different use case. They can be combined.

| Pattern | Package | Use case | Who triggers the check |
|---------|---------|----------|------------------------|
| **1 — Tool** | `tool/` | You own the tool code; gate the function itself | The tool, unconditionally |
| **2 — Skill** | `skill/` | Agent-driven Claude Code workflows | The agent, when it decides to ask |
| **3 — MCP** | `mcp/` | MCP-compatible agents; multi-agent systems | The agent, via standard MCP tool call |
| **4 — Hook** | `hooks/` | Session-level policy; any deployment | The Claude Code harness, regardless of agent |

The underlying signing infrastructure (`oauth/`, `extension/`, `cli/`) is identical for all four. Only the triggering point differs.

## CRITICAL Security Invariants

**Never violate these without an explicit security review:**

1. **`extractable: false`** — The `generateKey` call in `extension/src/background/crypto.ts` MUST keep `extractable` as `false`. The private key must never be exportable from SubtleCrypto.
2. **`chrome.storage.session` only** — Key material lives ONLY in session storage (in-memory, cleared on browser close). NEVER use `chrome.storage.local`, `chrome.storage.sync`, `localStorage`, `sessionStorage`, or IndexedDB for key material.
3. **Canonical serialization must match** — `challenge_bytes()` in `cli/hitl_cli/challenge.py` and `canonicalChallengeBytes()` in `extension/src/background/crypto.ts` MUST produce byte-for-byte identical output. Any divergence silently breaks all signature verification. If you change one, change both.
4. **Nonce uniqueness** — Every challenge nonce MUST be checked against Redis before accepting a signature. Never skip the nonce check even in tests against a live Keycloak.
5. **localhost only** — The native messaging host binds to `127.0.0.1:7331` only. Never change this to `0.0.0.0`.
6. **No key logging** — Never log private key material. Signature bytes may be logged at DEBUG level only.

## Challenge Schema

Version `"1"` canonical bytes (sorted keys, no whitespace):
```
{"action":"...","nonce":"...","timestamp":...,"tool_name":"...","version":"1"}
```
Both TypeScript and Python must produce this exact format. See `extension/src/background/crypto.ts:canonicalChallengeBytes()` and `cli/hitl_cli/challenge.py:challenge_bytes()`.

## Build Commands

```bash
# Extension
cd extension && npm install && npm run build   # production build → dist/
cd extension && npm run dev                    # watch mode
cd extension && npm test                       # Vitest unit tests

# Python packages (run from repo root)
uv pip install -e cli/ tool/ skill/ mcp/ hooks/

# Per-package tests
cd cli && uv run pytest
cd tool && uv run pytest
cd mcp && uv run pytest
cd hooks && uv run pytest

# Infrastructure
docker compose up -d          # Keycloak on :8080, Redis on :6379
docker compose down           # stop
docker compose logs keycloak  # Keycloak logs
```

## Running the Full Stack

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Build and load extension
cd extension && npm run build
# Chrome: chrome://extensions → Load unpacked → select extension/dist-chrome/
# Firefox: about:debugging → Load Temporary Add-on → select extension/dist-firefox/manifest.json

# 3. Install Python packages (all patterns)
uv pip install -e cli/ tool/ skill/ mcp/ hooks/

# 4. Register native messaging host (one-time, required for all patterns)
node extension/src/signing-host/install.js

# 5. Test each pattern
python -m hitl_tool.demo_tool           # Pattern 1: tool decorator
hitl-approve --action "test action"     # Pattern 2: skill
# Pattern 3: add mcp_config.json to Claude config, then use request_approval() in a session
hitl-install && hitl-hook               # Pattern 4: hook enforcement
```

## Hooks Configuration (Pattern 4)

```bash
hitl-install              # install in current project
hitl-install --global     # install for all Claude Code sessions
hitl-install --uninstall  # remove
HITL_POLICY=disabled      # turn off without uninstalling (env var)
HITL_UNAVAILABLE_POLICY=allow  # fail open when extension isn't running

# Customise dangerous/safe command patterns:
cp hooks/install/hitl-hooks-example.json .claude/hitl-hooks.json
```

## Keycloak Admin

- URL: `http://localhost:8080`
- Admin console: `http://localhost:8080/admin`
- Realm: `hitl`
- Admin credentials: see `.env` (copied from `.env.example`)
- CLI client (`hitl-cli`): confidential, `client_credentials` grant
- Extension client (`hitl-extension`): public PKCE, redirect `http://localhost:7331/*`

## Adding a New Tool Integration

1. Add `hitl-cli` as a dependency (path dep: `{path = "../cli"}`)
2. Import `generate_challenge`, `request_signature`, `verify_signed_response`, `KeycloakClient`
3. Use `@require_human_approval("Action description: {kwargs[param]}")` or call the pipeline directly
4. Catch `HitlDenied`, `HitlTimeout`, `HitlVerificationError` from `hitl_tool.exceptions`

## Changing the Challenge Schema

If you must add/remove fields from `ChallengeRequest`:
1. Update `extension/src/types/challenge.ts` — `ChallengeRequest` interface
2. Update `cli/hitl_cli/models.py` — `ChallengeRequest` Pydantic model
3. Update `canonicalChallengeBytes()` in `extension/src/background/crypto.ts`
4. Update `challenge_bytes()` in `cli/hitl_cli/challenge.py`
5. Bump `version` field to `"2"` (or next integer) in both places
6. Update tests in `extension/tests/` and `cli/tests/`
7. Update this section in CLAUDE.md

## Code Style

- **TypeScript**: `strict: true`, ESLint with `@typescript-eslint`, no `any` except where typed via `unknown` first
- **Python**: `ruff` for linting and formatting (`ruff check` + `ruff format`), `mypy` for type checking
- No inline comments except for non-obvious invariants or security-relevant constraints

## Environment Variables

Copy `.env.example` to `.env` before running. All packages read from environment; never hardcode secrets.

Required for Python packages:
- `KEYCLOAK_HOST`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLI_CLIENT_ID`
- `KEYCLOAK_CLI_CLIENT_SECRET`
- `EXTENSION_SIGNING_PORT` (default `7331`)
- `CHALLENGE_TTL_SECONDS` (default `300`)
- `NONCE_STORE_REDIS_URL`

Hooks-specific (optional, override defaults):
- `HITL_POLICY` — `enforce` (default) | `audit` | `disabled`
- `HITL_UNAVAILABLE_POLICY` — `block` (default) | `allow`
