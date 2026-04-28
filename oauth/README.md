# oauth/ — Keycloak Configuration

Reproducible Keycloak 24 setup for the HITL realm. The realm config is committed as `realm-export.json` and auto-imported on first container start.

## What Gets Configured

- **Realm `hitl`** — isolated from the `master` realm
- **Custom user attribute `ed25519_public_key`** — stores the user's base64url-encoded Ed25519 public key (32 bytes raw)
- **Protocol mapper** — exposes `ed25519_public_key` in `id_token` and `userinfo` responses
- **Client `hitl-extension`** — public PKCE client for the browser extension
- **Client `hitl-cli`** — confidential service-account client for CLI/tool/MCP Admin API calls
- **Role `hitl-user`** — assigned to all registered users; no bot/service accounts get this role

## Quick Start

```bash
# From the repo root:
docker compose up -d

# Verify the realm is up:
./oauth/scripts/verify-setup.sh
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/init-realm.sh` | Update `hitl-cli` secret + grant service account roles (run after first start if needed) |
| `scripts/register-pubkey.sh <user> <key>` | Manually register a public key for a test user |
| `scripts/verify-setup.sh` | Smoke test OIDC discovery, realm status, JWKS |

## Modifying the Realm

Make changes in the Keycloak admin console (`http://localhost:8080`), then export:

```bash
docker compose exec keycloak \
  /opt/keycloak/bin/kc.sh export \
  --realm hitl \
  --file /tmp/hitl-export.json

docker compose cp keycloak:/tmp/hitl-export.json oauth/realm-export.json
```

Commit the updated `realm-export.json`.

## Client Credentials

| Client | Type | Grant | Used by |
|--------|------|-------|---------|
| `hitl-extension` | Public | PKCE authorization_code | Browser extension |
| `hitl-cli` | Confidential | client_credentials | cli, tool, mcp packages |

The `hitl-cli` client secret is set via `KEYCLOAK_CLI_CLIENT_SECRET` in `.env`. The default value in `realm-export.json` is `hitl-cli-secret-change-me` — change it for any non-local deployment.
