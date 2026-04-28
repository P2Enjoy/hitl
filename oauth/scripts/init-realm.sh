#!/usr/bin/env bash
# Bootstrap Keycloak realm configuration via kcadm.sh.
# Run this inside the Keycloak container or with kcadm.sh on PATH.
# The realm-export.json import handles most config; this script
# sets the hitl-cli client secret from the environment.
set -euo pipefail

KC_URL="${KEYCLOAK_HOST:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-hitl}"
ADMIN="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-changeme}"
CLI_SECRET="${KEYCLOAK_CLI_CLIENT_SECRET:-}"

echo "Waiting for Keycloak at $KC_URL ..."
until curl -sf "$KC_URL/realms/master/.well-known/openid-configuration" > /dev/null; do
  sleep 3
done
echo "Keycloak is up."

kcadm.sh config credentials \
  --server "$KC_URL" \
  --realm master \
  --user "$ADMIN" \
  --password "$ADMIN_PASS"

# Update hitl-cli client secret if provided
if [[ -n "$CLI_SECRET" ]]; then
  CLIENT_ID=$(kcadm.sh get clients -r "$REALM" --fields id,clientId \
    | python3 -c "import sys,json; clients=json.load(sys.stdin); \
      print(next(c['id'] for c in clients if c['clientId']=='hitl-cli'))")
  kcadm.sh update "clients/$CLIENT_ID" -r "$REALM" -s "secret=$CLI_SECRET"
  echo "Updated hitl-cli client secret."
fi

# Grant hitl-cli service account the view-users role so it can read user attributes
SERVICE_ACCT=$(kcadm.sh get "clients/$CLIENT_ID/service-account-user" -r "$REALM" --fields id -o --format csv --noquotes 2>/dev/null || echo "")
if [[ -n "$SERVICE_ACCT" ]]; then
  REALM_MGMT_ID=$(kcadm.sh get clients -r "$REALM" --fields id,clientId \
    | python3 -c "import sys,json; clients=json.load(sys.stdin); \
      print(next(c['id'] for c in clients if c['clientId']=='realm-management'))")
  VIEW_USERS_ROLE=$(kcadm.sh get "clients/$REALM_MGMT_ID/roles/view-users" -r "$REALM" --fields id,name)
  kcadm.sh add-roles -r "$REALM" \
    --uusername "service-account-hitl-cli" \
    --cclientid realm-management \
    --rolename view-users 2>/dev/null || true
  echo "Granted view-users to hitl-cli service account."
fi

echo "Realm '$REALM' configuration complete."
