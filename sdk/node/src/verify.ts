import { createPublicKey, verify as cryptoVerify } from "node:crypto";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { HitlVerificationError } from "./errors.js";
import { challengeBytes } from "./challenge.js";
import type { ChallengeRequest, SignedResponse } from "./types.js";
import type { OAuthClient } from "./oauth.js";

// Cache JWKS fetchers per issuer to avoid re-creating on every call
const _jwksSets = new Map<string, ReturnType<typeof createRemoteJWKSet>>();

function b64urlDecode(s: string): Buffer {
  const padded = s + "=".repeat((4 - (s.length % 4)) % 4);
  return Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

/**
 * Verify a JWT's RS256/ES256 signature against the OAuth server's JWKS
 * and return the 'sub' claim.
 *
 * Raises HitlVerificationError if the signature is invalid, the issuer
 * doesn't match, or the token is expired.
 */
async function verifyJwtAndGetSub(token: string, issuer: string): Promise<string> {
  const jwksUri = new URL(`${issuer}/protocol/openid-connect/certs`);

  if (!_jwksSets.has(issuer)) {
    // createRemoteJWKSet caches keys internally with automatic rotation support
    _jwksSets.set(issuer, createRemoteJWKSet(jwksUri, { cacheMaxAge: 3_600_000 }));
  }
  const JWKS = _jwksSets.get(issuer)!;

  let payload;
  try {
    ({ payload } = await jwtVerify(token, JWKS, {
      issuer,
      clockTolerance: 30,
    }));
  } catch (e: unknown) {
    throw new HitlVerificationError(`JWT verification failed: ${e}`);
  }

  if (!payload.sub) {
    throw new HitlVerificationError("JWT missing sub claim");
  }
  return payload.sub;
}

async function checkNonce(nonce: string, ttl: number): Promise<void> {
  const redisUrl = process.env.NONCE_STORE_REDIS_URL ?? "redis://localhost:6379/0";
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
  oauthClient: OAuthClient,
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

  // Verify JWT signature cryptographically — prevents crafted/fake JWTs
  const issuer = `${oauthClient.oauthServerUrl}/realms/${oauthClient.realm}`;
  const userId = await verifyJwtAndGetSub(response.access_token, issuer);

  if (userId !== response.user_id) {
    throw new HitlVerificationError("user_id in response does not match access_token sub");
  }

  const pubkeyB64url = await oauthClient.getUserPubkey(userId);
  const pubkeyDer = b64urlDecode(pubkeyB64url);

  // Wrap raw 32-byte Ed25519 key in SubjectPublicKeyInfo DER envelope
  const spkiPrefix = Buffer.from("302a300506032b6570032100", "hex");
  const spki = Buffer.concat([spkiPrefix, pubkeyDer]);
  const publicKey = createPublicKey({ key: spki, format: "der", type: "spki" });

  const payload = challengeBytes(challenge);
  const sigBytes = b64urlDecode(response.signature);

  return cryptoVerify(null, payload, publicKey, sigBytes);
}
