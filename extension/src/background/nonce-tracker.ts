// In-session nonce deduplication. Prevents replay within a single browser session.
// Production should also check a shared Redis store (handled server-side by the tool).

const usedNonces = new Set<string>();

export function trackNonce(nonce: string): boolean {
  if (usedNonces.has(nonce)) return false;
  usedNonces.add(nonce);
  return true;
}

export function hasNonce(nonce: string): boolean {
  return usedNonces.has(nonce);
}

export function clearNonces(): void {
  usedNonces.clear();
}
