#!/usr/bin/env bash
# Example: register an Ed25519 public key for a test user via kcadm.sh.
# Usage: ./register-pubkey.sh <username> <base64url-public-key>
set -euo pipefail

KC_URL="${KEYCLOAK_HOST:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-hitl}"
ADMIN="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme}"

USERNAME="${1:?Usage: $0 <username> <base64url-pubkey>}"
PUBKEY="${2:?Usage: $0 <username> <base64url-pubkey>}"

kcadm.sh config credentials \
  --server "$KC_URL" \
  --realm master \
  --user "$ADMIN" \
  --password "$ADMIN_PASS"

USER_ID=$(kcadm.sh get users -r "$REALM" -q "username=$USERNAME" --fields id \
  | python3 -c "import sys,json; users=json.load(sys.stdin); print(users[0]['id'])")

kcadm.sh update "users/$USER_ID" -r "$REALM" \
  -s "attributes.ed25519_public_key=[\"$PUBKEY\"]"

echo "Registered public key for user '$USERNAME' (id: $USER_ID)."
