# cli/ — Shared Signing Library + Demo CLI

The `hitl_cli` package is the **shared foundation** for all four HITL integration patterns. It provides challenge generation, signature verification, and the Keycloak client. The `tool/`, `skill/`, `mcp/`, and `hooks/` packages all depend on it.

The `hitl` CLI is a demo that exercises the full sign→verify flow end-to-end, useful for testing and scripting. It is not itself an integration pattern — see the [root README](../README.md) for the four patterns.

## Installation

```bash
uv pip install -e cli/
cp .env.example .env  # fill in KEYCLOAK_CLI_CLIENT_SECRET
```

## Usage

```bash
# Request approval for an action
hitl request --action "delete /tmp/important-file"

# Specify the requesting tool name
hitl request --action "push to production" --tool "deploy-script"

# Check the signing host is reachable
hitl health
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Approved — signature verified |
| `1` | Denied by user, invalid signature, or verification error |
| `2` | Extension / signing host not reachable |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_HOST` | — | Keycloak base URL |
| `KEYCLOAK_REALM` | `hitl` | Keycloak realm name |
| `KEYCLOAK_CLI_CLIENT_ID` | — | Service account client ID |
| `KEYCLOAK_CLI_CLIENT_SECRET` | — | Service account client secret |
| `EXTENSION_SIGNING_PORT` | `7331` | Native messaging host HTTP port |
| `CHALLENGE_TTL_SECONDS` | `300` | Max age of a challenge |
| `NONCE_STORE_REDIS_URL` | `redis://localhost:6379/0` | Redis URL for nonce tracking |

## API (for use by tool/, skill/, mcp/)

```python
from hitl_cli.challenge import generate_challenge, challenge_bytes, request_signature
from hitl_cli.verifier import verify_signed_response
from hitl_cli.keycloak_client import KeycloakClient
from hitl_cli.models import ChallengeRequest, SignedResponse

# Generate a challenge
challenge = generate_challenge("delete /tmp/x", tool_name="my-tool")

# Send to extension and wait for user response
response = await request_signature(challenge)

# Verify
keycloak = KeycloakClient.from_env()
approved = await verify_signed_response(challenge, response, keycloak)
```

## Tests

```bash
cd cli && uv run pytest
```
