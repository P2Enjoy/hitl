/**
 * Challenge generation and signing-host communication.
 *
 * challengeBytes() MUST remain byte-for-byte identical to
 * sdk/python/hitl/challenge.py:challenge_bytes().
 */

import { randomBytes } from "node:crypto";
import type { ChallengeRequest, SignedResponse, SignOrDenyResponse } from "./types.js";

export function generateChallenge(action: string, toolName: string): ChallengeRequest {
  return {
    nonce: randomBytes(32).toString("hex"), // 256-bit, 64 hex chars
    timestamp: Math.floor(Date.now() / 1000),
    action,
    tool_name: toolName,
    version: "1",
  };
}

/**
 * Canonical UTF-8 bytes for signing/verifying.
 *
 * MUST stay byte-for-byte identical to sdk/python/hitl/challenge.py:challenge_bytes().
 * Keys are sorted alphabetically, no whitespace.
 */
export function challengeBytes(challenge: ChallengeRequest): Buffer {
  const payload = JSON.stringify({
    action: challenge.action,
    nonce: challenge.nonce,
    timestamp: challenge.timestamp,
    tool_name: challenge.tool_name,
    version: challenge.version,
  });
  return Buffer.from(payload, "utf-8");
}

export async function requestSignature(
  challenge: ChallengeRequest,
  port = parseInt(process.env.EXTENSION_SIGNING_PORT ?? "7331", 10),
): Promise<SignOrDenyResponse> {
  const { default: axios } = await import("axios");
  const ttl = parseInt(process.env.CHALLENGE_TTL_SECONDS ?? "300", 10);

  const resp = await axios.post<SignOrDenyResponse>(
    `http://127.0.0.1:${port}/sign`,
    challenge,
    { timeout: (ttl + 10) * 1000 },
  );
  return resp.data;
}

export async function checkExtensionAvailability(
  port = parseInt(process.env.EXTENSION_SIGNING_PORT ?? "7331", 10),
): Promise<boolean> {
  try {
    const { default: axios } = await import("axios");
    const resp = await axios.get(`http://127.0.0.1:${port}/health`, { timeout: 2000 });
    return resp.status === 200;
  } catch {
    return false;
  }
}
