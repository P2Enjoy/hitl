// SECURITY: chrome.storage.session is in-memory only, cleared on browser close.
// Private key material must NEVER be stored in local/sync storage.

const KEYPAIR_KEY = "hitl_keypair_v1";
const TOKENS_KEY = "hitl_tokens_v1";
const USER_KEY = "hitl_user_v1";

export interface StoredTokens {
  access_token: string;
  refresh_token?: string;
  expires_at: number; // Unix epoch seconds
  user_id: string;    // Keycloak sub
  username: string;
}

export interface StoredUser {
  sub: string;
  username: string;
  email?: string;
}

export async function storeKeypair(pair: CryptoKeyPair): Promise<void> {
  await chrome.storage.session.set({ [KEYPAIR_KEY]: pair });
}

export async function loadKeypair(): Promise<CryptoKeyPair | null> {
  const result = await chrome.storage.session.get(KEYPAIR_KEY);
  return (result[KEYPAIR_KEY] as CryptoKeyPair) ?? null;
}

export async function clearKeypair(): Promise<void> {
  await chrome.storage.session.remove(KEYPAIR_KEY);
}

export async function storeTokens(tokens: StoredTokens): Promise<void> {
  await chrome.storage.session.set({ [TOKENS_KEY]: tokens });
}

export async function loadTokens(): Promise<StoredTokens | null> {
  const result = await chrome.storage.session.get(TOKENS_KEY);
  return (result[TOKENS_KEY] as StoredTokens) ?? null;
}

export async function clearTokens(): Promise<void> {
  await chrome.storage.session.remove(TOKENS_KEY);
}

export async function storeUser(user: StoredUser): Promise<void> {
  await chrome.storage.session.set({ [USER_KEY]: user });
}

export async function loadUser(): Promise<StoredUser | null> {
  const result = await chrome.storage.session.get(USER_KEY);
  return (result[USER_KEY] as StoredUser) ?? null;
}

export async function clearAll(): Promise<void> {
  await chrome.storage.session.clear();
}
