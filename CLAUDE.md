# HITL Monorepo — Agent Instructions

## Project Purpose

Cryptographically signed human-in-the-loop (HITL) permission system. When an AI tool requests approval for a sensitive action, the response is Ed25519-signed by the user's browser extension and verified against a public key stored in Keycloak. The agent can never forge a valid signature.

## Package Map

| Package | Language | Description |
|---------|----------|-------------|
| `oauth/` | Bash/JSON | Keycloak 24 realm config + init scripts |
| `extension/` | TypeScript/MV3 | Browser extension — keypair holder and signer |
| `cli/` | Python 3.11 | Demo CLI: `hitl request --action "..."` |
| `tool/` | Python 3.11 | `@require_human_approval` decorator demo |
| `skill/` | Python 3.11 | Claude Code slash command `/hitl-approve` |
| `mcp/` | Python 3.11 | FastMCP server with `request_approval` tool |
| `hooks/` | Python 3.11 | **Claude Code PreToolUse hooks — enforced gating** |

## Integration Modes (read this first)

There are three ways to integrate HITL with Claude Code, with different enforcement levels:

| Mode | Package | Enforcement | How |
|------|---------|-------------|-----|
| **Hooks** (recommended) | `hooks/` | **Hard** — agent cannot bypass | `PreToolUse` hooks run at harness level outside agent control |
| **MCP** | `mcp/` | Soft — agent must cooperate | Agent calls `hitl.request_approval()` when instructed |
| **Skill** | `skill/` | Soft — agent must cooperate | Agent invokes `/hitl-approve` slash command |

**Use hooks for production.** The MCP and skill are useful for agent-initiated checks (e.g. "before I do X, let me verify") but do not prevent a rogue agent from skipping them.

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

# 3. Install Python packages
cd /path/to/hitl && uv pip install -e cli/ tool/ skill/ mcp/ hooks/

# 4. Register native messaging host (one-time setup)
node extension/src/signing-host/install.js

# 5. Install Claude Code hooks (enforced gating)
hitl-install              # project-level (recommended)
# or: hitl-install --global   # user-level

# 6. Test the golden path
hitl request --action "delete /tmp/testfile"
# → Browser popup appears → click Approve → terminal prints: APPROVED

# 7. Test hook enforcement directly
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' | hitl-hook
# → popup appears → approve/deny → {"decision":"approve"} or {"decision":"block",...}
```

## Hooks Configuration

The hooks package (`hooks/`) intercepts Claude Code tool calls at the harness level.

**Disable hooks temporarily** (e.g. for safe exploratory work):
```bash
HITL_POLICY=disabled claude "what files are in src/?"
```

**Fail open when extension is unavailable** (e.g. during CI):
```bash
HITL_UNAVAILABLE_POLICY=allow claude "run the tests"
```

**Customise which commands require approval** — copy the example config:
```bash
cp hooks/install/hitl-hooks-example.json .claude/hitl-hooks.json
# Edit .claude/hitl-hooks.json to add/remove patterns
```

See `hooks/README.md` for the full config reference.

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
