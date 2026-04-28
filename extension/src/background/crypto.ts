import { base64urlEncode } from "../utils/base64url.js";
import type { ChallengeRequest } from "../types/challenge.js";

// SECURITY: extractable MUST remain false — private key can never be exported.
export async function generateKeypair(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey(
    { name: "Ed25519" } as EcKeyGenParams,
    false,
    ["sign", "verify"],
  );
}

export async function exportPublicKey(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey("raw", key);
  return base64urlEncode(new Uint8Array(raw));
}

// SECURITY: canonical serialization must stay byte-for-byte identical to
// cli/hitl_cli/challenge.py:challenge_bytes(). Sorted keys, no whitespace.
export function canonicalChallengeBytes(challenge: ChallengeRequest): Uint8Array {
  const payload = JSON.stringify({
    action: challenge.action,
    nonce: challenge.nonce,
    timestamp: challenge.timestamp,
    tool_name: challenge.tool_name,
    version: challenge.version,
  });
  return new TextEncoder().encode(payload);
}

export async function signChallenge(
  privateKey: CryptoKey,
  challenge: ChallengeRequest,
): Promise<string> {
  const payload = canonicalChallengeBytes(challenge);
  const sigBuffer = await crypto.subtle.sign("Ed25519", privateKey, payload);
  return base64urlEncode(new Uint8Array(sigBuffer));
}

export async function verifySignature(
  publicKey: CryptoKey,
  challenge: ChallengeRequest,
  signatureBase64url: string,
): Promise<boolean> {
  const { base64urlDecode } = await import("../utils/base64url.js");
  const payload = canonicalChallengeBytes(challenge);
  const sig = base64urlDecode(signatureBase64url);
  return crypto.subtle.verify("Ed25519", publicKey, sig, payload);
}

export async function importPublicKey(base64urlKey: string): Promise<CryptoKey> {
  const { base64urlDecode } = await import("../utils/base64url.js");
  const raw = base64urlDecode(base64urlKey);
  return crypto.subtle.importKey("raw", raw, { name: "Ed25519" } as EcKeyImportParams, true, ["verify"]);
}
