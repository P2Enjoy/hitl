---
description: Request cryptographically verified human approval for a sensitive action. The response is Ed25519-signed by the user's browser extension and verified against Keycloak. Exit code 0 = APPROVED, 1 = DENIED.
argument-hint: "<action description>"
---

# HITL Approval Request

You are requesting human approval for the action: **$ARGUMENTS**

This command:
1. Generates a cryptographic challenge (nonce + timestamp + action description)
2. Sends it to the user's browser extension for signing
3. Verifies the Ed25519 signature against the user's public key stored in Keycloak
4. Outputs `HITL_APPROVED` or `HITL_DENIED` and exits with code 0 or 1

**This command blocks** until the user responds in the browser extension popup (up to `CHALLENGE_TTL_SECONDS` seconds, default 300).

## Invocation

```bash
python -m hitl_skill.skill --action "$ARGUMENTS"
```

## Integration Pattern

When using this as a gate before a sensitive operation:

```
result=$(python -m hitl_skill.skill --action "$ARGUMENTS")
if [ "$result" = "HITL_APPROVED" ]; then
  # proceed with the operation
else
  echo "Operation blocked: HITL approval denied or failed"
  exit 1
fi
```

## Requires

- Browser extension loaded and signed in (see extension/README.md)
- Native messaging host installed (run: node extension/src/signing-host/install.js)
- Python package installed: uv pip install -e skill/
- Environment: KEYCLOAK_HOST, KEYCLOAK_CLI_CLIENT_ID, KEYCLOAK_CLI_CLIENT_SECRET
