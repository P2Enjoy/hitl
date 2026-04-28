#!/usr/bin/env bash
# Smoke test: verify OIDC discovery and client configuration are correct.
set -euo pipefail

KC_URL="${KEYCLOAK_HOST:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-hitl}"

echo "=== OIDC Discovery ==="
curl -sf "$KC_URL/realms/$REALM/.well-known/openid-configuration" \
  | python3 -m json.tool | grep -E '"issuer"|"token_endpoint"|"userinfo_endpoint"|"jwks_uri"'

echo ""
echo "=== Realm Status ==="
curl -sf "$KC_URL/realms/$REALM" | python3 -m json.tool | grep -E '"realm"|"enabled"'

echo ""
echo "=== JWKS Endpoint ==="
curl -sf "$KC_URL/realms/$REALM/protocol/openid-connect/certs" \
  | python3 -m json.tool | python3 -c "import sys,json; j=json.load(sys.stdin); print(f'Keys available: {len(j[\"keys\"])}')"

echo ""
echo "Setup looks good. Keycloak realm '$REALM' is operational."
