import { createPublicKey, verify as cryptoVerify } from "node:crypto";
import { HitlVerificationError } from "./errors.js";
import { challengeBytes } from "./challenge.js";
import type { ChallengeRequest, SignedResponse } from "./types.js";
import type { KeycloakClient } from "./keycloak.js";

function b64urlDecode(s: string): Buffer {
  const padded = s + "=".repeat((4 - (s.length % 4)) % 4);
  return Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

function parseJwtSub(token: string): string {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT: expected 3 parts");
  const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf-8")) as {
    sub?: string;
  };
  if (!payload.sub) throw new Error("JWT missing sub claim");
  return payload.sub;
}

async function checkNonce(nonce: string, ttl: number): Promise<void> {
  const redisUrl = process.env.NONCE_STORE_REDIS_URL ?? "redis://localhost:6379/0";
  // Dynamic import so redis is optional at module load time
  const { createClient } = await import("redis");
  const client = createClient({ url: redisUrl });
  await client.connect();
  try {
    const key = `hitl:nonce:${nonce}`;
    const wasSet = await client.set(key, "1", { NX: true, EX: ttl * 2 });
    if (!wasSet) {
      throw new HitlVerificationError(`Nonce already used: ${nonce}`);
    }
  } finally {
    await client.disconnect();
  }
}

export async function verifySignedResponse(
  challenge: ChallengeRequest,
  response: SignedResponse,
  keycloak: KeycloakClient,
): Promise<boolean> {
  const ttl = parseInt(process.env.CHALLENGE_TTL_SECONDS ?? "300", 10);
  const age = Math.abs(Date.now() / 1000 - challenge.timestamp);
  if (age > ttl) {
    throw new HitlVerificationError(`Challenge expired (age=${age.toFixed(0)}s, ttl=${ttl}s)`);
  }

  if (response.nonce !== challenge.nonce) {
    throw new HitlVerificationError("Response nonce does not match challenge nonce");
  }

  await checkNonce(challenge.nonce, ttl);

  let userId: string;
  try {
    userId = parseJwtSub(response.access_token);
  } catch (e) {
    throw new HitlVerificationError(`Cannot parse access_token sub: ${e}`);
  }

  if (userId !== response.user_id) {
    throw new HitlVerificationError("user_id in response does not match access_token sub");
  }

  const pubkeyB64url = await keycloak.getUserPubkey(userId);
  const pubkeyDer = b64urlDecode(pubkeyB64url);

  // Node.js requires DER-wrapped Ed25519 public key for createPublicKey
  // Wrap raw 32-byte key in SubjectPublicKeyInfo DER envelope
  const spkiPrefix = Buffer.from("302a300506032b6570032100", "hex");
  const spki = Buffer.concat([spkiPrefix, pubkeyDer]);
  const publicKey = createPublicKey({ key: spki, format: "der", type: "spki" });

  const payload = challengeBytes(challenge);
  const sigBytes = b64urlDecode(response.signature);

  return cryptoVerify(null, payload, publicKey, sigBytes);
}
