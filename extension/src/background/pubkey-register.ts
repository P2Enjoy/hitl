const OAUTH_SERVER_URL = "http://localhost:8080";
const REALM = "hitl";

export async function registerPublicKey(
  accessToken: string,
  userId: string,
  publicKeyBase64url: string,
): Promise<void> {
  // Uses the OAuth server Account REST API (user manages own account).
  // The hitl-extension client must have "manage-account" scope.
  const accountUrl = `${OAUTH_SERVER_URL}/realms/${REALM}/account`;

  const resp = await fetch(accountUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      attributes: { ed25519_public_key: publicKeyBase64url },
    }),
  });

  if (!resp.ok) {
    // Fall back to admin endpoint if account API rejects (requires admin token)
    await registerPublicKeyViaAdmin(accessToken, userId, publicKeyBase64url);
  }
}

async function registerPublicKeyViaAdmin(
  accessToken: string,
  userId: string,
  publicKeyBase64url: string,
): Promise<void> {
  const adminUrl = `${OAUTH_SERVER_URL}/admin/realms/${REALM}/users/${userId}`;

  const resp = await fetch(adminUrl, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      attributes: { ed25519_public_key: [publicKeyBase64url] },
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Failed to register public key: ${err}`);
  }
}
