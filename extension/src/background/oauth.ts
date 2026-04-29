import { storeTokens, storeUser, clearAll, type StoredTokens } from "./keystore.js";

const OAUTH_SERVER_URL = "http://localhost:8080";
const REALM = "hitl";
const CLIENT_ID = "hitl-extension";
const TOKEN_ENDPOINT = `${OAUTH_SERVER_URL}/realms/${REALM}/protocol/openid-connect/token`;
const USERINFO_ENDPOINT = `${OAUTH_SERVER_URL}/realms/${REALM}/protocol/openid-connect/userinfo`;
const AUTH_ENDPOINT = `${OAUTH_SERVER_URL}/realms/${REALM}/protocol/openid-connect/auth`;

function generateCodeVerifier(): string {
  const arr = new Uint8Array(32);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

async function sha256Base64url(plain: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

export async function loginWithOAuth(): Promise<StoredTokens> {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await sha256Base64url(codeVerifier);
  const redirectUri = chrome.identity.getRedirectURL("callback");

  const authUrl = new URL(AUTH_ENDPOINT);
  authUrl.searchParams.set("client_id", CLIENT_ID);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("code_challenge", codeChallenge);
  authUrl.searchParams.set("code_challenge_method", "S256");
  authUrl.searchParams.set("scope", "openid profile email");

  const responseUrl = await chrome.identity.launchWebAuthFlow({
    url: authUrl.toString(),
    interactive: true,
  });

  if (!responseUrl) throw new Error("OAuth flow returned no redirect URL");

  const code = new URL(responseUrl).searchParams.get("code");
  if (!code) throw new Error("No authorization code in redirect URL");

  return exchangeCode(code, codeVerifier, redirectUri);
}

// Backward-compatible alias
export const loginWithKeycloak = loginWithOAuth;

async function exchangeCode(
  code: string,
  verifier: string,
  redirectUri: string,
): Promise<StoredTokens> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CLIENT_ID,
    code,
    redirect_uri: redirectUri,
    code_verifier: verifier,
  });

  const resp = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Token exchange failed: ${err}`);
  }

  const data = (await resp.json()) as {
    access_token: string;
    refresh_token?: string;
    expires_in: number;
  };

  const userInfo = await fetchUserInfo(data.access_token);
  const tokens: StoredTokens = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Math.floor(Date.now() / 1000) + data.expires_in,
    user_id: userInfo.sub,
    username: userInfo.preferred_username ?? userInfo.email ?? userInfo.sub,
  };

  await storeTokens(tokens);
  await storeUser({
    sub: userInfo.sub,
    username: tokens.username,
    email: userInfo.email,
  });

  return tokens;
}

async function fetchUserInfo(accessToken: string): Promise<Record<string, string>> {
  const resp = await fetch(USERINFO_ENDPOINT, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!resp.ok) throw new Error("Failed to fetch userinfo");
  return resp.json() as Promise<Record<string, string>>;
}

export async function logout(): Promise<void> {
  await clearAll();
}
